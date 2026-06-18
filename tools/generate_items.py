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

_CONFIGS_DIR = Path(__file__).parent / "configs"

# filename → (data_version, pw_version_str)
_VERSION_RE = re.compile(r'PW_([\d.]+)_v(\d+)(?:_\d+)?\.cfg$')


def list_configs() -> list[dict]:
    """Return all available configs sorted by data version."""
    out = []
    for f in sorted(_CONFIGS_DIR.glob("PW_*.cfg")):
        m = _VERSION_RE.search(f.name)
        if m:
            out.append({
                "name": f.name,
                "pw_version": m.group(1),
                "data_version": int(m.group(2)),
            })
    return sorted(out, key=lambda x: x["data_version"])


def detect_config(elements_path: str) -> str | None:
    """
    Read the version int16 from elements.data header and return the matching
    config filename. Falls back to the closest lower version if no exact match.
    Returns None if configs directory is missing.
    """
    if not _CONFIGS_DIR.exists():
        return None
    try:
        with open(elements_path, "rb") as fh:
            raw = fh.read(2)
        ver = struct.unpack_from("<h", raw)[0]
    except Exception:
        return None

    configs = list_configs()
    if not configs:
        return None

    # Exact match: pick highest PW version among all configs with the same data version
    exact = [c for c in configs if c["data_version"] == ver]
    if exact:
        return sorted(exact, key=lambda x: [int(p) for p in x["pw_version"].split(".")])[-1]["name"]

    # Closest version ≤ detected
    below = [c for c in configs if c["data_version"] <= ver]
    if below:
        return below[-1]["name"]  # list is sorted ascending, so last = closest
    return configs[0]["name"]

# ibuild.js type letter → mcat → SItmC{mcat}S{sub} → pw_items.json type key
#   W=1(Weapon)  A=2(Armor)  J=3(Jewelry)  O=4(Other Octet)
#   U=5(Utility) M=6(Mats&Herbs)  F=7(Fashion)  C=8(Cards)
#
# pw_items.json sub numbers must match 1-based positions in IBMENU_SC[type].
# Sub-type IDs from elements.data are large arbitrary ints — remap them below.

_TABLE_MAP = {
    # type 1 – Weapon  (IBMENU_SC[1]: Polehammer…Schythe)
    "004 - WEAPON_ESSENCE":      (1, "id_sub_type"),

    # type 2 – Armor   (IBMENU_SC[2]: HeavyPlate…Manteau)
    "007 - ARMOR_ESSENCE":       (2, "id_sub_type"),

    # type 3 – Jewelry (IBMENU_SC[3]: PhysNeck…MagicRing)
    "010 - DECORATION_ESSENCE":  (3, "id_sub_type"),

    # type 4 – Other Octet (IBMENU_SC[4]: Flyer, PetEgg, BlessBox, Elf, Hiero…)
    "023 - FLYSWORD_ESSENCE":    (4, 1),   # Flyer
    "024 - WINGMANWING_ESSENCE": (4, 1),   # Flyer (elf wings)
    "095 - PET_ESSENCE":         (4, 2),   # Pet Egg
    "096 - PET_EGG_ESSENCE":     (4, 2),   # Pet Egg
    "120 - GOBLIN_ESSENCE":      (4, 2),   # Pet Egg
    "122 - GOBLIN_EQUIP_ESSENCE":(4, 2),   # Pet Egg
    "100 - WAR_TANKCALLIN_ESSENCE":(4, 1), # Flyer (tank mount)

    # type 5 – Utility (IBMENU_SC[5]: Tome, Boost, Util, Chat, Pages, Dye…)
    "022 - SKILLTOME_ESSENCE":   (5, 1),   # Tome
    "107 - SKILLMATTER_ESSENCE": (5, 1),   # Tome
    "013 - MEDICINE_ESSENCE":    (5, 2),   # Boost (HP/MP/buff potions)
    "115 - AUTOHP_ESSENCE":      (5, 2),   # Boost
    "116 - AUTOMP_ESSENCE":      (5, 2),   # Boost
    "117 - DOUBLE_EXP_ESSENCE":  (5, 2),   # Boost
    "123 - GOBLIN_EXPPILL_ESSENCE":(5, 2), # Boost
    "090 - FACEPILL_ESSENCE":    (5, 2),   # Boost
    "025 - TOWNSCROLL_ESSENCE":  (5, 3),   # Util
    "026 - UNIONSCROLL_ESSENCE": (5, 3),   # Util
    "027 - REVIVESCROLL_ESSENCE":(5, 3),   # Util
    "028 - ELEMENT_ESSENCE":     (5, 3),   # Util
    "118 - TRANSMITSCROLL_ESSENCE":(5, 3), # Util
    "087 - FACETICKET_ESSENCE":  (5, 3),   # Util (makeover scrolls)
    "108 - REFINE_TICKET_ESSENCE":(5, 3),  # Util
    "109 - DESTROYING_ESSENCE":  (5, 3),   # Util
    "113 - BIBLE_ESSENCE":       (5, 3),   # Util
    "124 - SELL_CERTIFICATE_ESSENCE":(5, 3), # Util
    "125 - TARGET_ITEM_ESSENCE": (5, 3),   # Util
    "126 - LOOK_INFO_ESSENCE":   (5, 3),   # Util
    "114 - SPEAKER_ESSENCE":     (5, 4),   # Chat
    "099 - FIREWORKS_ESSENCE":   (5, 7),   # Firework
    "119 - DYE_TICKET_ESSENCE":  (5, 6),   # Dye
    "097 - PET_FOOD_ESSENCE":    (5, 10),  # Pet Scroll
    "098 - PET_FACETICKET_ESSENCE":(5, 3), # Util
    "018 - DAMAGERUNE_ESSENCE":  (5, 3),   # Util (elf runes)
    "020 - ARMORRUNE_ESSENCE":   (5, 3),   # Util (elf runes)

    # type 6 – Mats & Herbs (IBMENU_SC[6]: NormalMats, Jade, Herbs)
    "016 - MATERIAL_ESSENCE":    (6, 1),   # Normal Mats
    "029 - TASKMATTER_ESSENCE":  (6, 1),   # Normal Mats
    "030 - TOSSMATTER_ESSENCE":  (6, 1),   # Normal Mats
    "032 - PROJECTILE_ESSENCE":  (6, 1),   # Normal Mats
    "034 - QUIVER_ESSENCE":      (6, 1),   # Normal Mats
    "036 - STONE_ESSENCE":       (6, 2),   # Jade (craft stones)

    # type 7 – Fashion  (IBMENU_SC[7]: Top[M], Top[F], Pants[M], Skirt[F]…)
    # Sub is derived from (id_sub_type, gender) — sentinel triggers special handling
    "084 - FASHION_ESSENCE":     (7, "FASHION_GENDER"),
}

# Sub-type ID from elements.data → 1-based IBMENU_SC position
# Read from actual WEAPON/ARMOR/DECORATION/FASHION_SUB_TYPE tables in elements.data v27.
_WEAPON_SUB_REMAP: dict[int, int] = {
    10: 1,   # Polehammer
    98: 2,   # Poleaxe
    99: 3,   # Dual Axes
    118: 4,  # Dual Hammers
    56: 5,   # Pike (Spear)
    66: 6,   # Poleblade (Polearm)
    76: 7,   # 棍杖 (Staff)
    86: 8,   # Club (Mace)
    2: 9,    # Blade
    18: 10,  # Sword
    46: 11,  # Dual Blades
    35: 12,  # Dual Swords
    183: 13, # Fist
    184: 14, # Claw
    96: 15,  # Bow
    209: 16, # Crossbow
    210: 17, # Slingshot
    336: 18, # Magic Sword
    338: 19, # Wand
    339: 20, # Glaive (Magic Quoit)
    340: 21, # Pataka (Magic Staff)
    23755: 22, 25719: 22,  # Dagger
    23756: 23, 25720: 23,  # Artifact (Sphere)
}

_ARMOR_SUB_REMAP: dict[int, int] = {
    127: 1,  # Heavy Plate
    140: 2,  # Light Armor
    153: 3,  # Arcane Robe
    163: 4,  # Heavy Leggings
    188: 5,  # Light Leggings
    202: 6,  # Arcane Leggings
    217: 7,  # Heavy Footwear
    218: 8,  # Light Footwear
    219: 9,  # Arcane Footwear
    347: 10, # Heavy Wristguards
    2875: 11, # Light Wristguards
    356: 12, # Arcane Wristguards
    318: 13, # Helmet
    317: 14, # Arcane Headgear (Magic Headgear)
    370: 15, # Robe/Manteau/Cloak
}

_DECORATION_SUB_REMAP: dict[int, int] = {
    172: 1,  # Elemental Necklace → Physical Necklace
    241: 2,  # Ethereal Necklace  → Dodge Necklace
    243: 3,  # Protection Necklace → Magical Necklace
    235: 4,  # Elemental Belt → Physical Waist
    244: 5,  # Ethereal Belt  → Dodge Waist
    245: 6,  # Protection Belt → Magical Waist
    248: 7,  # Might Ring → Physical Ring
    250: 8,  # Magic Ring → Magical Ring
}

# Fashion: keyed by (id_sub_type, gender) → 1-based IBMENU_SC[7] position
# gender=0=Male, gender=1=Female (from actual elements.data dump)
_FASHION_SUB_REMAP: dict[tuple[int, int], int] = {
    (3937, 0): 1,   # Body, Male   → Top [Male]
    (3937, 1): 2,   # Body, Female → Top [Female]
    (4270, 0): 3,   # Legwears, Male   → Pants [Male]
    (4270, 1): 4,   # Legwears, Female → Skirt [Female]
    (4188, 0): 5,   # Handwears, Male   → Glove [Male]
    (4188, 1): 6,   # Handwears, Female → Sleeves [Female]
    (3954, 0): 7,   # Footwears, Male   → Boots [Male]
    (3954, 1): 8,   # Footwears, Female → Shoes [Female]
    (26173, 0): 9,  # Headdress, Male   → Hair Style [Male]
    (26173, 1): 10, # Headdress, Female → Hair Style [Female]
}

_SUB_REMAPS: dict[int, dict[int, int]] = {
    1: _WEAPON_SUB_REMAP,
    2: _ARMOR_SUB_REMAP,
    3: _DECORATION_SUB_REMAP,
}

# Item types that use grade field (cats 1/2/3 in getPItemData do selectedIndex = grade-1)
_GEAR_TYPES = {1, 2, 3}

# ── PHP converter ──────────────────────────────────────────────────────────────

def from_php(php_path: str) -> dict:
    """Parse $ItemMod[type][sub][] = "name#id#..."; assignments."""
    text = Path(php_path).read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(
        r'\$ItemMod\s*\[(\d+)\]\s*\[(\d+)\]\s*(?:\[\d*\])?\s*=\s*"([^"]+)"\s*;'
    )
    result: dict[str, dict[str, list]] = {}
    for m in pattern.finditer(text):
        t, s, val = m.group(1), m.group(2), m.group(3)
        result.setdefault(t, {}).setdefault(s, []).append(val)
    return result


# ── Config parser ──────────────────────────────────────────────────────────────

def _resolve_cfg(cfg_name: str | None, elements_path: str | None) -> Path:
    """Return the Path to the config to use."""
    if cfg_name:
        p = _CONFIGS_DIR / cfg_name
        if not p.exists():
            print(f"ERROR: config '{cfg_name}' not found in {_CONFIGS_DIR}", file=sys.stderr)
            sys.exit(1)
        return p
    if elements_path:
        detected = detect_config(elements_path)
        if detected:
            return _CONFIGS_DIR / detected
    # Last resort: old bundled file next to the script
    fallback = Path(__file__).parent / "PW_1.4.2_v27.cfg"
    if fallback.exists():
        return fallback
    print(f"ERROR: no config file found. Put configs in {_CONFIGS_DIR}", file=sys.stderr)
    sys.exit(1)


def _load_config(cfg_path: Path) -> tuple[int, list[dict]]:
    """
    Parse PW_1.4.2_v27.cfg. Returns (conversation_list_index, tables[]).
    Each table dict has: name, offset (int or 'AUTO'), fields[], types[], rec_size.
    """
    lines = cfg_path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip(): i += 1
    _table_count = int(lines[i]); i += 1
    conv_idx = int(lines[i]); i += 1

    tables = []
    while i < len(lines):
        while i < len(lines) and not lines[i].strip(): i += 1
        if i >= len(lines): break
        name = lines[i].strip(); i += 1
        raw_off = lines[i].strip(); i += 1
        offset = int(raw_off) if raw_off.isdigit() else raw_off  # int or 'AUTO'
        fields = lines[i].strip().split(';'); i += 1
        types  = lines[i].strip().split(';'); i += 1
        if i < len(lines) and not lines[i].strip(): i += 1

        rec_size = 0
        for t in types:
            if t in ('int32', 'float'): rec_size += 4
            elif t == 'int16': rec_size += 2
            elif t in ('int64', 'double'): rec_size += 8
            elif t.startswith('wstring:'): rec_size += int(t[8:])
            elif t.startswith('string:'): rec_size += int(t[7:])
            elif t.startswith('byte:') and t[5:].isdigit(): rec_size += int(t[5:])
            # byte:AUTO → 0 (special case, handled separately)
        tables.append({'name': name, 'offset': offset, 'fields': fields,
                       'types': types, 'rec_size': rec_size})
    return conv_idx, tables


# ── Binary reader ──────────────────────────────────────────────────────────────

def _read_field(data: bytes, pos: int, ftype: str) -> tuple[object, int]:
    """Read one field at pos, return (value, new_pos)."""
    if ftype == 'int32':
        return struct.unpack_from('<i', data, pos)[0], pos + 4
    if ftype == 'float':
        return struct.unpack_from('<f', data, pos)[0], pos + 4
    if ftype == 'int16':
        return struct.unpack_from('<h', data, pos)[0], pos + 2
    if ftype == 'int64':
        return struct.unpack_from('<q', data, pos)[0], pos + 8
    if ftype == 'double':
        return struct.unpack_from('<d', data, pos)[0], pos + 8
    if ftype.startswith('wstring:'):
        n = int(ftype[8:])
        raw = data[pos:pos + n]
        end = 0
        while end + 1 < len(raw) and (raw[end] or raw[end + 1]):
            end += 2
        return raw[:end].decode('utf-16-le', errors='replace'), pos + n
    if ftype.startswith('string:'):
        n = int(ftype[7:])
        raw = data[pos:pos + n]
        end = raw.find(b'\x00')
        return raw[:end if end != -1 else n].decode('gbk', errors='replace'), pos + n
    if ftype.startswith('byte:') and ftype[5:].isdigit():
        n = int(ftype[5:])
        return data[pos:pos + n], pos + n
    return None, pos


_NA_PREFIX = re.compile(r'^N/A\s*')
# Matches any character outside printable ASCII (excludes CJK, Cyrillic, etc.)
_NON_ASCII = re.compile(r'[^\x20-\x7E]')


def _read_name(raw: str) -> str:
    name = _NA_PREFIX.sub('', raw).strip()
    # Skip non-English / debug items (names containing CJK or other non-ASCII)
    if _NON_ASCII.search(name):
        return ''
    return name


# ── elements.data parser ───────────────────────────────────────────────────────

def from_elements(elements_path: str, _existing: dict | None = None,
                  cfg_name: str | None = None) -> dict:
    """
    Parse elements.data using the version-matched config schema.
    Correctly categorises every item by which essence table it comes from.
    Returns the pw_items.json structure.
    """
    cfg_path = _resolve_cfg(cfg_name, elements_path)
    print(f"Using config: {cfg_path.name}", file=sys.stderr)

    conv_idx, tables = _load_config(cfg_path)
    data = Path(elements_path).read_bytes()
    print(f"Loaded {len(data):,} bytes, {len(tables)} tables defined.", file=sys.stderr)

    pos = 0
    version  = struct.unpack_from('<h', data, pos)[0]; pos += 2
    _sig     = struct.unpack_from('<h', data, pos)[0]; pos += 2
    print(f"elements.data version={version}", file=sys.stderr)

    # Collected items: {(pw_type, pw_subtype): [(id, name), ...]}
    items_by_cat: dict[tuple[int,int], list[tuple[int,str]]] = {}
    # Sub-type name lookup tables read from the file
    weapon_sub: dict[int, str] = {}    # id → name
    armor_sub: dict[int, str] = {}
    deco_sub: dict[int, str] = {}
    fashion_sub: dict[int, str] = {}

    for idx, tbl in enumerate(tables):
        name = tbl['name']

        # ── Handle offset section ──────────────────────────────────────────
        if idx == 0:
            # EQUIPMENT_ADDON: fixed 4-byte offset blob before count
            pos += tbl['offset']  # offset == 4
        elif tbl['offset'] == 'AUTO' and idx == 20:
            # SKILLTOME_SUB_TYPE: 4-byte tag + 4-byte len + len bytes + 4 bytes
            _tag = data[pos:pos+4]; pos += 4
            buf_len = struct.unpack_from('<I', data, pos)[0]; pos += 4
            pos += buf_len
            pos += 4
        elif tbl['offset'] == 'AUTO' and idx == 100:
            # NPC_WAR_TOWERBUILD_SERVICE: 4-byte tag + 4-byte len + len bytes
            _tag = data[pos:pos+4]; pos += 4
            buf_len = struct.unpack_from('<I', data, pos)[0]; pos += 4
            pos += buf_len
        elif isinstance(tbl['offset'], int) and tbl['offset'] > 0:
            pos += tbl['offset']

        # ── Conversation list (TALK_PROC at conv_idx) — auto-size blob ────
        if idx == conv_idx:
            pattern = b'facedata\\'
            pat_pos = data.find(pattern, pos)
            if pat_pos == -1:
                print(f"WARNING: TALK_PROC pattern not found, aborting at table {idx}", file=sys.stderr)
                break
            list_length = pat_pos - pos - 72
            if list_length < 0:
                list_length = 0
            pos += list_length
            continue  # no record_count follows for this table

        # ── Read records ───────────────────────────────────────────────────
        if pos + 4 > len(data):
            break
        count = struct.unpack_from('<i', data, pos)[0]; pos += 4

        if count < 0 or count > 200_000:
            print(f"  [{idx:3d}] {name}: implausible count={count}, stopping", file=sys.stderr)
            break

        rec_size = tbl['rec_size']
        if rec_size == 0:
            # Unknown-size table with no records — skip
            continue

        # Decide whether we care about this table
        is_sub_type   = name.endswith('SUB_TYPE') or name.endswith('MAJOR_TYPE')
        table_mapping = _TABLE_MAP.get(name)
        want = is_sub_type or (table_mapping is not None)

        if not want:
            # Fast skip: jump over all records without parsing
            pos += count * rec_size
            continue

        fields = tbl['fields']
        types  = tbl['types']

        for _ in range(count):
            rec_start = pos
            record: dict = {}
            for fld, ftype in zip(fields, types):
                v, pos = _read_field(data, pos, ftype)
                record[fld] = v
            # Verify we consumed exactly rec_size bytes
            if pos != rec_start + rec_size:
                pos = rec_start + rec_size  # self-correct

            # ── Store sub-type name tables ─────────────────────────────────
            if name == '003 - WEAPON_SUB_TYPE':
                weapon_sub[record.get('ID', 0)] = record.get('Name', '')
            elif name == '006 - ARMOR_SUB_TYPE':
                armor_sub[record.get('ID', 0)] = record.get('Name', '')
            elif name == '009 - DECORATION_SUB_TYPE':
                deco_sub[record.get('ID', 0)] = record.get('Name', '')
            elif name == '083 - FASHION_SUB_TYPE':
                fashion_sub[record.get('ID', 0)] = record.get('Name', '')

            # ── Store item essence records ─────────────────────────────────
            if table_mapping:
                pw_type, sub_spec = table_mapping
                item_id = record.get('ID', 0)
                raw_name = record.get('Name', '') or ''
                item_name = _read_name(raw_name)

                if not item_id or not item_name:
                    continue

                # Determine sub-type position (1-based IBMENU_SC position)
                if sub_spec == "FASHION_GENDER":
                    raw_sub = record.get("id_sub_type", 0) or 0
                    raw_gender = record.get("gender", 0) or 0
                    pw_sub = _FASHION_SUB_REMAP.get((raw_sub, raw_gender), 0)
                    if pw_sub == 0:
                        continue  # unknown fashion sub — skip
                elif isinstance(sub_spec, str):
                    raw_sub = record.get(sub_spec, 0) or 0
                    remap = _SUB_REMAPS.get(pw_type)
                    pw_sub = remap.get(raw_sub, 1) if remap else (raw_sub or 1)
                else:
                    pw_sub = sub_spec

                key = (pw_type, pw_sub)
                items_by_cat.setdefault(key, []).append((item_id, item_name))

    print(f"Parsed {sum(len(v) for v in items_by_cat.values()):,} raw item records "
          f"across {len(items_by_cat)} categories.", file=sys.stderr)

    # ── Build output ───────────────────────────────────────────────────────────
    result: dict[str, dict[str, list]] = {}
    seen_ids: set[int] = set()

    for (pw_type, pw_sub), entries in sorted(items_by_cat.items()):
        t_str = str(pw_type)
        s_str = str(pw_sub)
        bucket = result.setdefault(t_str, {}).setdefault(s_str, [])
        # Grade: gear types (1/2/3) need grade≥1 so getPItemData's selectedIndex = grade-1 ≥ 0
        grade = "1" if pw_type in _GEAR_TYPES else "0"

        for item_id, item_name in entries:
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            # Format: name#id#grade#color#addon#extra
            # addon "1 0 0 0" = amount/stack=1, proc=0, octetType=0, octetData=0
            # extra "-" = non-numeric so isNumber() returns false for Tome (sct=1)
            #   desc branch, preventing TomeStat[NaN] crash in getPItemData
            bucket.append(f"{item_name}#{item_id}#{grade}#0#1 0 0 0#-")

    total = sum(len(v) for subs in result.values() for v in subs.values())
    print(f"Built {total:,} unique items across {len(result)} types.", file=sys.stderr)
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pw_items.json")
    parser.add_argument("--source", choices=["elements", "php"], default="php",
                        help="Data source: 'elements' for elements.data, 'php' for pw_items.php")
    parser.add_argument("--elements", default=None,
                        help="Path to elements.data (default: read from .env SERVER_PATH)")
    parser.add_argument("--php", default=None,
                        help="Path to pw_items.php")
    parser.add_argument("--config", default=None,
                        help="Config filename to use, e.g. PW_1.4.2_v27.cfg (default: auto-detect from elements.data version)")
    parser.add_argument("--output", default=str(OUTPUT),
                        help=f"Output JSON path (default: {OUTPUT})")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip backup of existing pw_items.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict | None = None
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: could not read existing JSON: {e}", file=sys.stderr)

    if not args.no_backup and out_path.exists():
        from datetime import datetime
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = BACKUP_DIR / f"pw_items_{ts}.json.bak"
        shutil.copy2(out_path, bak)
        print(f"Backup saved to {bak}", file=sys.stderr)

    if args.source == "php":
        php_path = args.php
        if not php_path:
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
        print(f"Parsing elements.data: {el_path}", file=sys.stderr)
        result = from_elements(el_path, existing, cfg_name=args.config)

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=None), encoding="utf-8")
    total = sum(len(v) for subs in result.values() for v in subs.values())
    print(f"Written {total:,} items to {out_path}", file=sys.stderr)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
