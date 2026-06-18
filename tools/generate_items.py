#!/usr/bin/env python3
"""
Generate data/pw_items.json from elements.data or pw_items.php.

Usage:
    python tools/generate_items.py --source elements  [--elements /path/to/elements.data]
    python tools/generate_items.py --source php       [--php /path/to/pw_items.php]
    python tools/generate_items.py --source elements  # uses server path from .env

The output is written to data/pw_items.json. The previous file is backed up
to data/backups/pw_items_YYYYMMDD_HHMMSS.json.bak before overwriting.
"""

import argparse
import json
import os
import re
import shutil
import struct
import sys
from pathlib import Path

OUTPUT = Path("data/pw_items.json")
BACKUP_DIR = Path("data/backups")

# Item type/subtype mapping: (type_id, subtype_id) → (type_name, sub_name)
# Mirrors the item builder category structure.
# Weapons
WEAPON_TYPE = 1
ARMOR_TYPE   = 2
JEWEL_TYPE   = 3
# type_id → list of subtype names (index = subtype_id - 1)
TYPE_NAMES = {
    1: "Weapon", 2: "Armor", 3: "Jewelry",
    4: "Flyer/Pet", 5: "Elf", 6: "Fashion",
    7: "Misc", 8: "Other",
}


# ── PHP converter ─────────────────────────────────────────────────────────────

def from_php(php_path: str) -> dict:
    """Parse $ItemMod[type][sub][] = "name#id#..."; assignments."""
    text = Path(php_path).read_text(encoding="utf-8", errors="replace")
    # Match both $ItemMod[t][s][n] and $ItemMod[t][s][]
    pattern = re.compile(
        r'\$ItemMod\s*\[(\d+)\]\s*\[(\d+)\]\s*(?:\[\d*\])?\s*=\s*"([^"]+)"\s*;'
    )
    result: dict[str, dict[str, list]] = {}
    for m in pattern.finditer(text):
        t, s, val = m.group(1), m.group(2), m.group(3)
        result.setdefault(t, {}).setdefault(s, []).append(val)
    return result


# ── elements.data scanner ─────────────────────────────────────────────────────

# Known (item_id → (type, subtype)) from the existing php structure.
# We read this from pw_items.json if available, to anchor the scan.
def _build_anchor_map(existing_json: dict) -> dict[int, tuple[int, int]]:
    # Exclude type 8 / subtype 99 — that's the auto-generated bucket, always rebuilt.
    anchor: dict[int, tuple[int, int]] = {}
    for t_str, subs in existing_json.items():
        for s_str, entries in subs.items():
            if t_str == "8" and s_str == "99":
                continue
            vals = entries.values() if isinstance(entries, dict) else entries
            for entry in vals:
                parts = entry.split("#")
                if len(parts) >= 2:
                    try:
                        anchor[int(parts[1])] = (int(t_str), int(s_str))
                    except ValueError:
                        pass
    return anchor


def _read_utf16le_str(data: bytes, offset: int, max_chars: int = 64) -> str:
    """Read null-terminated UTF-16LE string from offset."""
    end = offset
    limit = min(offset + max_chars * 2, len(data) - 1)
    while end + 1 < limit:
        if data[end] == 0 and data[end + 1] == 0:
            break
        end += 2
    try:
        return data[offset:end].decode("utf-16-le", errors="replace")
    except Exception:
        return ""


_STAR = set("☆★✦")
_VALID_NAME = re.compile(
    r'^[☆★✦]*[A-Z一-鿿][A-Za-z0-9\s一-鿿·\'\-\+\.\!\(\)\[\]☆★✦°·:,&%]{1,50}$'
)
_NA_PREFIX = re.compile(r'^N/A\s*')
_CJK = re.compile(r'[一-鿿]')

# NPC job titles and zone labels that appear in element tables but are not items
_NPC_WORDS = re.compile(
    r'\b(Blacksmith|Apothecary|Tailor|Jeweler|Herbalist|Craftsman|Warehouse|'
    r'Merchant|Vendor|Banker|Bounty|Trainer|Healer|Auctioneer|'
    r'Dealer|Trader|Supplier|Refiner|Teleporter|Sculptor|'
    r'Guard|Warden|Sentry|Ambassador|Envoy|Emissary|'
    r'Elder|Master|Chief|Captain|General|Commander|'
    r'Traveling|RootNode|Checkpoint|Courier)\b',
    re.IGNORECASE,
)
# Stat descriptions, abbreviated or full, and bare UI strings
_STAT_NAME = re.compile(
    r'\b(Damage|Defense|Accuracy|Evasion|HP|MP|Mana|Mdef|Pdef|'
    r'Dmg|Atk|Def|Acc|Eva|Crit|Phys|Mag|Max)\b.{0,6}[+\-]\d+'
    r'|'
    r'\bPage\s+\d+'  # "Page 1", "Page 2" — UI pagination strings
)


def _is_cjk(name: str) -> bool:
    return bool(_CJK.search(name))


def _is_valid_item_name(name: str) -> bool:
    if not name or len(name) < 3 or len(name) > 55:
        return False
    clean = name.lstrip("☆★✦ ")
    if not clean or not (clean[0].isupper() or '一' <= clean[0] <= '鿿'):
        return False
    if clean.replace(" ", "").isdigit():
        return False
    # Reject quest dialog (sentence fragments)
    if re.search(r'\b(you|the|and|for|have|that|this|with|from|your|are|was|will)\b', name, re.IGNORECASE):
        return False
    # Reject NPC job titles and zone/UI labels
    if _NPC_WORDS.search(name):
        return False
    # Reject stat description strings
    if _STAT_NAME.search(name):
        return False
    return bool(_VALID_NAME.match(name))


def from_elements(elements_path: str, existing: dict | None = None) -> dict:
    """
    Scan elements.data for item records.

    Strategy:
      - The file contains tables. Within each table, records have:
          uint32 item_id at a fixed offset,
          UTF-16LE null-terminated name string 12 bytes after the item_id.
      - We scan all 4-byte-aligned offsets for uint32 values in the valid
        item_id range (100–40000), then check for a valid UTF-16LE name
        12 bytes later.
      - We use the existing pw_items.json to resolve type/subtype placement.
        Items not in the existing map go into a catch-all "other" bucket.
    """
    data = Path(elements_path).read_bytes()
    anchor = _build_anchor_map(existing or {})

    # Collect all (item_id → name) pairs found in the binary.
    # Elements.data has multiple table types with different record layouts:
    #   weapons/armor/jewelry: item_id at record+0, name at item_id+12
    #   fashion/wings/misc:    item_id at record+0, name at item_id+4
    #   some tables:           item_id at record+2, name at item_id+4  (2-byte aligned)
    # We scan every 2 bytes and try names at both +4 and +12.
    #
    # The same numeric ID can appear in multiple tables (e.g. item table AND
    # recipe table), so we apply a priority:
    #   1. English names beat Chinese names (game client shows English)
    #   2. Within the same language, longer name wins (more specific table)
    found: dict[int, tuple[str, bool]] = {}  # id → (name, is_english)
    n = len(data) - 20

    print(f"Scanning {len(data):,} bytes …", file=sys.stderr)

    for i in range(0, n, 2):
        item_id = struct.unpack_from("<I", data, i)[0]
        if not (4000 <= item_id <= 40000):
            continue
        # Try name at +4 (fashion/misc) and +12 (weapons/armor); keep best
        best, best_is_eng = "", True
        for name_off in (i + 4, i + 12):
            if name_off + 4 > len(data):
                continue
            name = _read_utf16le_str(data, name_off, max_chars=48)
            name = _NA_PREFIX.sub("", name).strip()
            if not _is_valid_item_name(name):
                continue
            is_eng = not _is_cjk(name)
            # Pick this name if: it's English and current best is Chinese,
            # or same language and longer
            if (is_eng and not best_is_eng) or \
               (is_eng == best_is_eng and len(name) > len(best)):
                best, best_is_eng = name, is_eng
        if not best:
            continue
        # Compare against previously stored name for this ID
        prev = found.get(item_id)
        if prev is None:
            found[item_id] = (best, best_is_eng)
        else:
            prev_name, prev_is_eng = prev
            if (best_is_eng and not prev_is_eng) or \
               (best_is_eng == prev_is_eng and len(best) > len(prev_name)):
                found[item_id] = (best, best_is_eng)

    print(f"Found {len(found):,} raw item_id/name pairs.", file=sys.stderr)

    # Build result: start from existing structure, update/add names.
    # Type "8"/subtype "99" is our auto-generated bucket — always rebuild it
    # from scratch so stale or Chinese-named entries from prior runs are removed.
    result: dict[str, dict[str, list]] = {}
    if existing:
        for t_str, subs in existing.items():
            result[t_str] = {}
            for s_str, entries in subs.items():
                if t_str == "8" and s_str == "99":
                    continue  # rebuilt below
                vals = list(entries.values() if isinstance(entries, dict) else entries)
                result[t_str][s_str] = []
                for entry in vals:
                    parts = entry.split("#")
                    try:
                        iid = int(parts[1])
                    except (ValueError, IndexError):
                        result[t_str][s_str].append(entry)
                        continue
                    if iid not in found:
                        continue  # item ID not in this server's elements.data — drop it
                    name, is_eng = found[iid]
                    if is_eng:  # only overwrite with English names
                        parts[0] = name
                        entry = "#".join(parts)
                    result[t_str][s_str].append(entry)

    # Add newly found items not in existing (into type "8", subtype "99")
    existing_ids = set(anchor.keys())
    # Deduplicate by name — same NPC/mob in multiple zones shares one name
    seen_names: set[str] = set()
    new_items = []
    for iid, (name, is_eng) in sorted(found.items()):
        if iid in existing_ids or not is_eng:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        new_items.append((iid, name))
    if new_items:
        result.setdefault("8", {}).setdefault("99", [])
        for iid, name in new_items:
            result["8"]["99"].append(f"{name}#{iid}#0#0#0")
        print(f"Added {len(new_items):,} new items to type 8/subtype 99.", file=sys.stderr)

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pw_items.json")
    parser.add_argument("--source", choices=["elements", "php"], default="php",
                        help="Data source: 'elements' for elements.data, 'php' for pw_items.php")
    parser.add_argument("--elements", default=None,
                        help="Path to elements.data (default: read from .env SERVER_PATH)")
    parser.add_argument("--php", default=None,
                        help="Path to pw_items.php")
    parser.add_argument("--output", default=str(OUTPUT),
                        help=f"Output JSON path (default: {OUTPUT})")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip backup of existing pw_items.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing JSON for structure anchoring
    existing: dict | None = None
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            print(f"Loaded existing {out_path} ({len(str(existing)):,} chars)", file=sys.stderr)
        except Exception as e:
            print(f"Warning: could not read existing JSON: {e}", file=sys.stderr)

    # Backup
    if not args.no_backup and out_path.exists():
        from datetime import datetime
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = BACKUP_DIR / f"pw_items_{ts}.json.bak"
        shutil.copy2(out_path, bak)
        print(f"Backup saved to {bak}", file=sys.stderr)

    # Generate
    if args.source == "php":
        php_path = args.php
        if not php_path:
            # Try default location relative to this script
            default = Path(__file__).parent.parent.parent / "pwadmin/php/pw_items.php"
            if default.exists():
                php_path = str(default)
            else:
                print("Error: --php path required", file=sys.stderr)
                sys.exit(1)
        print(f"Parsing PHP: {php_path}", file=sys.stderr)
        result = from_php(php_path)

    else:  # elements
        el_path = args.elements
        if not el_path:
            # Try to read from .env
            env_file = Path(__file__).parent.parent / ".env"
            server_path = "/home"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("SERVER_PATH="):
                        server_path = line.split("=", 1)[1].strip().strip("'\"")
            el_path = f"{server_path.rstrip('/')}/gamed/config/elements.data"
        if not Path(el_path).exists():
            print(f"Error: elements.data not found at {el_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Scanning elements.data: {el_path}", file=sys.stderr)
        result = from_elements(el_path, existing)

    # Write output
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=None), encoding="utf-8")
    total = sum(len(v) for subs in result.values() for v in subs.values())
    print(f"Written {total:,} items to {out_path}", file=sys.stderr)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
