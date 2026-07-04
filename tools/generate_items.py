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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

    # type 4 – Other Octet (IBMENU_SC[4]: Flyer, PetEgg, BlessBox, Elf, Hiero,
    #                        Ammo, Potion, TaskDice, PetFood, SoulStones, Order, StarChart)
    "023 - FLYSWORD_ESSENCE":      (4, 1),   # Flyer
    "024 - WINGMANWING_ESSENCE":   (4, 1),   # Flyer (elf wings)
    "100 - WAR_TANKCALLIN_ESSENCE":(4, 1),   # Flyer (tank mount)
    "095 - PET_ESSENCE":           (4, 2),   # Pet Egg
    "096 - PET_EGG_ESSENCE":       (4, 2),   # Pet Egg
    "120 - GOBLIN_ESSENCE":        (4, 2),   # Pet Egg
    "122 - GOBLIN_EQUIP_ESSENCE":  (4, 2),   # Pet Egg
    "032 - PROJECTILE_ESSENCE":    (4, 6),   # Ammo (arrows)
    "034 - QUIVER_ESSENCE":        (4, 6),   # Ammo (quivers)
    "075 - TASKDICE_ESSENCE":      (4, 8),   # Task Dice
    "097 - PET_FOOD_ESSENCE":      (4, 9),   # Pet Food
    "036 - STONE_ESSENCE":         (4, 10),  # Soul Stones (Jargoon, Garnet…)

    # type 5 – Utility (IBMENU_SC[5]: Tome, Boost, Util, Chat, Pages, Dye,
    #                   Firework, DragonQuest, PackReward, PetScroll, Funny, Fuel,
    #                   Wine/Blood, ElfGear, Runes, MarkOfMight)
    "022 - SKILLTOME_ESSENCE":        (5, 1),   # Tome
    "107 - SKILLMATTER_ESSENCE":      (5, 1),   # Tome
    "013 - MEDICINE_ESSENCE":         (5, 2),   # Boost (HP/MP potions, food)
    "115 - AUTOHP_ESSENCE":           (5, 2),   # Boost
    "116 - AUTOMP_ESSENCE":           (5, 2),   # Boost
    "117 - DOUBLE_EXP_ESSENCE":       (5, 2),   # Boost
    "123 - GOBLIN_EXPPILL_ESSENCE":   (5, 2),   # Boost
    "025 - TOWNSCROLL_ESSENCE":       (5, 3),   # Util
    "026 - UNIONSCROLL_ESSENCE":      (5, 3),   # Util
    "027 - REVIVESCROLL_ESSENCE":     (5, 3),   # Util
    "118 - TRANSMITSCROLL_ESSENCE":   (5, 3),   # Util
    "087 - FACETICKET_ESSENCE":       (5, 3),   # Util (makeover scrolls)
    "108 - REFINE_TICKET_ESSENCE":    (5, 3),   # Util
    "109 - DESTROYING_ESSENCE":       (5, 3),   # Util
    "113 - BIBLE_ESSENCE":            (5, 3),   # Util
    "124 - SELL_CERTIFICATE_ESSENCE": (5, 3),   # Util
    "125 - TARGET_ITEM_ESSENCE":      (5, 3),   # Util
    "126 - LOOK_INFO_ESSENCE":        (5, 3),   # Util
    "114 - SPEAKER_ESSENCE":          (5, 4),   # Chat
    "119 - DYE_TICKET_ESSENCE":       (5, 6),   # Dye
    "099 - FIREWORKS_ESSENCE":        (5, 7),   # Firework
    "098 - PET_FACETICKET_ESSENCE":   (5, 10),  # Pet Scroll
    "090 - FACEPILL_ESSENCE":         (5, 11),  # Funny (face change pills)
    "028 - ELEMENT_ESSENCE":          (5, 12),  # Fuel (Yiyuan Stone)
    "018 - DAMAGERUNE_ESSENCE":       (5, 14),  # Elf Gear
    "020 - ARMORRUNE_ESSENCE":        (5, 15),  # Runes

    # type 6 – Mats & Herbs (IBMENU_SC[6]: NormalMats, Jade, Herbs)
    # MATERIAL_ESSENCE sub-type determines output bucket (MAT_SUB sentinel)
    "016 - MATERIAL_ESSENCE":    (6, "MAT_SUB"),
    "029 - TASKMATTER_ESSENCE":  (6, 1),   # Normal Mats
    "030 - TOSSMATTER_ESSENCE":  (6, 1),   # Normal Mats

    # type 7 – Fashion  (IBMENU_SC[7]: Top[M], Top[F], Pants[M], Skirt[F]…)
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

# MATERIAL_ESSENCE sub-type IDs that map to Jade (sub 2) or Herbs (sub 3) in type 6.
# All other sub-types land in Normal Mats (sub 1), except 20044 (Pages → type 5 sub 5).
_JADE_MATERIAL_SUBS  = {762, 764, 765, 766, 767, 768, 769, 770}
_HERB_MATERIAL_SUBS  = {1819, 1822, 1829, 1833, 1836, 1843, 1847, 1849, 1853, 1856}
_PAGE_MATERIAL_SUB   = 20044

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
# Block CJK/Hangul/Kana but allow non-ASCII symbols like ☆ ★ ✦
_CJK = re.compile(r'[　-ヿ㐀-䶿一-鿿가-힯豈-﫿]')


def _read_name(raw: str) -> str:
    name = _NA_PREFIX.sub('', raw).strip()
    if _CJK.search(name):
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
                elif sub_spec == "MAT_SUB":
                    raw_sub = record.get("id_sub_type", 0) or 0
                    if raw_sub in _JADE_MATERIAL_SUBS:
                        pw_sub = 2   # Jade
                    elif raw_sub in _HERB_MATERIAL_SUBS:
                        pw_sub = 3   # Herbs
                    elif raw_sub == _PAGE_MATERIAL_SUB:
                        pw_type, pw_sub = 5, 5  # Pages → type 5
                    else:
                        pw_sub = 1   # Normal Mats
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

        seen_names: set[str] = set()
        for item_id, item_name in sorted(entries):  # sort by ID to keep the original (lowest ID)
            if item_id in seen_ids:
                continue
            if item_name in seen_names:
                continue  # same name already added from a lower ID
            seen_ids.add(item_id)
            seen_names.add(item_name)
            bucket.append(f"{item_name}#{item_id}#{grade}#0#1 0 0 0#-")

    total = sum(len(v) for subs in result.values() for v in subs.values())
    print(f"Built {total:,} unique items across {len(result)} types.", file=sys.stderr)
    return result


# ── Inherent item addons (base-template variable bonuses, e.g. "Strength +3~4") ─

# Weapon/Armor/Jewelry always give their 4 basic-stat bonuses (Strength, Agility,
# Intelligence, Constitution) through EQUIPMENT_ADDON names "A_F<tier>", "A_G<tier>",
# "A_H<tier>", "A_I<tier>" sharing the same tier suffix — verified against known
# item_data.ADDONS entries (tier 009) and against a live item's in-game tooltip
# (tier 004, "Energetic Robe: Wraithgate"): F/G/H/I -> stat 0/1/2/3 in that order.
_BASIC_STAT_LETTERS = {"F": 0, "G": 1, "H": 2, "I": 3}
_ADDON_NAME_RE = re.compile(r'^A_([A-Z]+)(\d+)$')

# Same "complete family sharing one tier" trick for the 5 elemental defenses
# (Metal/Wood/Water/Fire/Earth), whose EQUIPMENT_ADDON names are "C_E<tier>A"
# through "C_E<tier>E" — verified against the curated Metal/Wood/Water/Fire/Earth
# Def. addon ids (365/368/371/374/377, all tier "01").
_ELEMENTAL_DEF_LETTERS = {"A": 15, "B": 16, "C": 17, "D": 18, "E": 19}
_ELEMENTAL_NAME_RE = re.compile(r'^C_E(\d+)([A-E])$')

# Single-stat EQUIPMENT_ADDON name prefixes that map to exactly one stat id across
# every curated (non-Rune, H-type) ADDONS entry that uses them — derived from
# tools/generate_items.py analysis correlating item_data.ADDONS against the live
# EQUIPMENT_ADDON table's Name field. Prefixes that map to more than one stat id
# (e.g. "A_G" covers both Agility and Hit Point at different tiers) are excluded
# here and only resolved via exact curated-id match. This lets other power tiers
# of the *same* addon family resolve, not just the handful of tiers the curated
# list happens to include.
_SAFE_PREFIXES = {
    "AD_L": 35, "A_A": 10, "A_AGI": 13, "A_B": 9, "A_DEF": 10, "A_F": 0, "A_I": 3,
    "A_J": 27, "A_MD": 6, "A_MDU": 7, "A_N": 11, "A_P": 23,
    "B_S": 20, "B_T": 21, "B_U": 28, "C_B": 29, "C_C": 14, "C_SD": 8,
    "D_L": 36, "D_rate": 37, "Ed_rate": 44, "Fd_rate": 45, "Gd_rate": 43,
    "Mdd_rate": 38, "Wad_rate": 46, "Wd_rate": 42,
}
_SAFE_PREFIX_RE = re.compile(
    r'^(' + '|'.join(re.escape(p) for p in sorted(_SAFE_PREFIXES, key=len, reverse=True)) + r')(\d+)$'
)

_GEAR_ESSENCE_TABLES = ("004 - WEAPON_ESSENCE", "007 - ARMOR_ESSENCE", "010 - DECORATION_ESSENCE")

# Stats whose octet amount isn't a 1:1 copy of the elements.data param — the client
# displays them as (raw_param / UNIT_SCALE[stat_id]), e.g. Interval stores the
# actual game value (0.05) while the octet wants an integer "count of 0.05 units"
# (StatName's "-." prefix in baseitemdata.js — GetAddonString does val*0.05).
# Only include stats confirmed to need this; anything else is assumed 1:1.
_UNIT_SCALE = {28: 0.05}  # stat_id -> elements.data-value-per-octet-unit


def _curated_addon_map() -> dict[int, tuple[int, str]]:
    """addon_id -> (stat_id, type_char) from the hand-curated ADDONS list, H-type
    only — F-type entries can have per-addon-id scaling quirks (e.g. Max Durability
    divides by 100) that aren't safe to assume generically. Runes are excluded --
    they're a distinct system (duration-bound, separate UI) we don't want to
    surface as if they were a plain inherent stat bonus."""
    from app.services.item_data import ADDONS
    out = {}
    for a in ADDONS:
        parts = a.split("#")
        aid, statid, typ, name = int(parts[0]), int(parts[1]), parts[2], parts[4]
        if typ == "H" and "Rune" not in name:
            out[aid] = (statid, typ)
    return out


def extract_item_addons(elements_path: str, cfg_name: str | None = None) -> dict[int, list[dict]]:
    """
    Parse EQUIPMENT_ADDON + gear essence tables and resolve each item's inherent
    (variable-range) bonus addons, e.g. an armor's built-in "Strength +3~4".
    Returns {item_id: [{"addon_id","stat_id","type","name","min","max"}, ...]}.
    Items whose addons can't be confidently resolved are omitted.
    """
    cfg_path = _resolve_cfg(cfg_name, elements_path)
    conv_idx, tables = _load_config(cfg_path)
    data = Path(elements_path).read_bytes()
    pos = 4  # version (int16) + signature (int16)

    addon_master: dict[int, dict] = {}
    gear_items: dict[int, list[int]] = {}

    for idx, tbl in enumerate(tables):
        name = tbl['name']
        if idx == 0:
            pos += tbl['offset']
        elif tbl['offset'] == 'AUTO' and idx == 20:
            pos += 4
            buf_len = struct.unpack_from('<I', data, pos)[0]; pos += 4
            pos += buf_len + 4
        elif tbl['offset'] == 'AUTO' and idx == 100:
            pos += 4
            buf_len = struct.unpack_from('<I', data, pos)[0]; pos += 4
            pos += buf_len
        elif isinstance(tbl['offset'], int) and tbl['offset'] > 0:
            pos += tbl['offset']

        if idx == conv_idx:
            pat_pos = data.find(b'facedata\\', pos)
            list_length = max(pat_pos - pos - 72, 0) if pat_pos != -1 else 0
            pos += list_length
            continue

        if pos + 4 > len(data):
            break
        count = struct.unpack_from('<i', data, pos)[0]; pos += 4
        if count < 0 or count > 200_000:
            break
        rec_size = tbl['rec_size']
        if rec_size == 0:
            continue

        want = name == "001 - EQUIPMENT_ADDON" or name in _GEAR_ESSENCE_TABLES
        if not want:
            pos += count * rec_size
            continue

        fields = tbl['fields']; types = tbl['types']
        for _ in range(count):
            rec_start = pos
            record = {}
            for fld, ftype in zip(fields, types):
                v, pos = _read_field(data, pos, ftype)
                record[fld] = v
            if pos != rec_start + rec_size:
                pos = rec_start + rec_size

            if name == "001 - EQUIPMENT_ADDON":
                addon_master[record.get('ID')] = record
            elif name in _GEAR_ESSENCE_TABLES:
                item_id = record.get('ID', 0)
                if not item_id:
                    continue
                # addons_N_id_addon is a *random-roll pool*, not a guaranteed set --
                # e.g. a regular sword (fixed_props=0) had probability_addon_num0
                # (chance of *zero* addons) over 96%, with the rest of the pool
                # only sometimes rolled. Only fixed_props==2 items (quest/reward
                # gear like "Energetic Robe: Wraithgate", verified against its
                # real in-game tooltip) reliably apply every listed slot — treat
                # everything else as "can't safely say this is guaranteed."
                if record.get('fixed_props', 0) != 2:
                    continue
                slots = [record.get(f'addons_{n}_id_addon', 0) or 0 for n in range(1, 33)]
                slots = [s for s in slots if s]
                if slots:
                    gear_items[item_id] = slots

    def resolve_item(addon_ids: list[int]) -> list[dict]:
        # Only resolve the "complete quadruple" basic-stat-bonus pattern (see comment
        # above): F/G/H/I sharing one tier suffix, all present on the same item.
        # These are plain integer stat points with no unit conversion, so the
        # elements.data param is exactly the octet amount an admin would type in.
        parsed: dict[int, tuple[str, str]] = {}
        for aid in addon_ids:
            rec = addon_master.get(aid)
            if not rec:
                continue
            m = _ADDON_NAME_RE.match(rec.get('Name', '') or '')
            if m:
                parsed[aid] = (m.group(1), m.group(2))

        by_tier: dict[str, dict[str, int]] = {}
        for aid, (letter, tier) in parsed.items():
            if letter in _BASIC_STAT_LETTERS:
                by_tier.setdefault(tier, {})[letter] = aid
        quad_resolved: dict[int, int] = {}
        for letters in by_tier.values():
            if set(letters) == set(_BASIC_STAT_LETTERS):
                for letter, aid in letters.items():
                    quad_resolved[aid] = _BASIC_STAT_LETTERS[letter]

        # Same trick for the elemental-defense quintuple (Metal/Wood/Water/Fire/Earth).
        elem_parsed: dict[int, tuple[str, str]] = {}
        for aid in addon_ids:
            rec = addon_master.get(aid)
            if not rec:
                continue
            m = _ELEMENTAL_NAME_RE.match(rec.get('Name', '') or '')
            if m:
                elem_parsed[aid] = (m.group(1), m.group(2))  # (tier, letter)
        elem_by_tier: dict[str, dict[str, int]] = {}
        for aid, (tier, letter) in elem_parsed.items():
            elem_by_tier.setdefault(tier, {})[letter] = aid
        elem_resolved: dict[int, int] = {}
        for letters in elem_by_tier.values():
            if set(letters) == set(_ELEMENTAL_DEF_LETTERS):
                for letter, aid in letters.items():
                    elem_resolved[aid] = _ELEMENTAL_DEF_LETTERS[letter]

        curated = _curated_addon_map()

        out = []
        seen_aids: set[int] = set()
        for aid in addon_ids:
            if aid in seen_aids:
                continue  # same addon_id can appear in multiple slots of one item's pool
            seen_aids.add(aid)
            rec = addon_master.get(aid)
            if not rec:
                continue
            if aid in quad_resolved:
                stat_id = quad_resolved[aid]
            elif aid in elem_resolved:
                stat_id = elem_resolved[aid]
            elif aid in curated:
                stat_id = curated[aid][0]
            else:
                m = _SAFE_PREFIX_RE.match(rec.get('Name', '') or '')
                stat_id = _SAFE_PREFIXES[m.group(1)] if m else None
            if stat_id is None:
                continue

            p1 = rec.get('param1', 0)
            # num_params==1 means only param1 is meaningful (a fixed value, not a
            # range) — param2 is unused zero-fill in that case, not a real bound.
            p2 = rec.get('param2', 0) if rec.get('num_params', 2) >= 2 else p1
            scale = _UNIT_SCALE.get(stat_id)
            if scale:
                # These stats store the actual float game value as int32 bits,
                # not a plain int (e.g. Interval's 0.05 is a float32 bit pattern).
                p1 = struct.unpack('<f', struct.pack('<i', p1))[0]
                p2 = struct.unpack('<f', struct.pack('<i', p2))[0]
                lo, hi = round(min(p1, p2) / scale), round(max(p1, p2) / scale)
            else:
                lo, hi = min(p1, p2), max(p1, p2)
            # Sanity guard: a few addon ids resolved via _SAFE_PREFIXES turned out to
            # store a float32 bit pattern despite their curated H-type sibling being a
            # plain int (e.g. an "A_P<tier>" Reduce P.Harm variant genuinely encodes a
            # percentage as float, unlike the curated int-based one) -- those decode
            # to nonsense values in the billions. Rather than guess which ones need
            # float reinterpretation, drop anything implausible for a real game stat.
            if abs(lo) > 100_000 or abs(hi) > 100_000:
                continue
            out.append({"addon_id": aid, "stat_id": stat_id, "type": "H", "min": lo, "max": hi})
        return out

    result: dict[int, list[dict]] = {}
    for item_id, addon_ids in gear_items.items():
        resolved = resolve_item(addon_ids)
        if resolved:
            result[item_id] = resolved
    return result


# ── Item base stats (Level Req, HP/MP, defenses, stat reqs, durability) ─────────

# Field name -> normalized key, per essence table. "_high"/"_low" suffixed fields
# use the "high" (best-case) value, matching how a GM tool should default a
# freshly-built item; only Durability keeps both bounds (existing UI already has
# two boxes for it).
_ARMOR_STAT_FIELDS = {
    "require_level": "level_req", "character_combo_id": "class_req",
    "hp_enhance_high": "hp", "mp_enhance_high": "mp",
    "defence_high": "pdef",
    "magic_defences_1_high": "metal_def", "magic_defences_2_high": "wood_def",
    "magic_defences_3_high": "water_def", "magic_defences_4_high": "fire_def",
    "magic_defences_5_high": "earth_def",
    "require_strength": "str_req", "require_agility": "agi_req",
    "require_energy": "int_req", "require_tili": "con_req",
    "durability_min": "dur_min", "durability_max": "dur_max",
}
_WEAPON_STAT_FIELDS = {
    "require_level": "level_req", "character_combo_id": "class_req",
    "damage_low": "pdmg_min", "damage_high_max": "pdmg_max",
    "magic_damage_low": "mdmg_min", "magic_damage_high_max": "mdmg_max",
    "require_strength": "str_req", "require_agility": "agi_req",
    "require_energy": "int_req", "require_tili": "con_req",
    "durability_min": "dur_min", "durability_max": "dur_max",
}
_DECO_STAT_FIELDS = {
    "require_level": "level_req", "character_combo_id": "class_req",
    "damage_high": "pattack", "magic_damage_high": "mattack",
    "defence_high": "pdef",
    "magic_defences_1_high": "metal_def", "magic_defences_2_high": "wood_def",
    "magic_defences_3_high": "water_def", "magic_defences_4_high": "fire_def",
    "magic_defences_5_high": "earth_def",
    "require_strength": "str_req", "require_agility": "agi_req",
    "require_energy": "int_req", "require_tili": "con_req",
    "durability_min": "dur_min", "durability_max": "dur_max",
}
_STAT_FIELD_MAP = {
    "004 - WEAPON_ESSENCE": _WEAPON_STAT_FIELDS,
    "007 - ARMOR_ESSENCE": _ARMOR_STAT_FIELDS,
    "010 - DECORATION_ESSENCE": _DECO_STAT_FIELDS,
}


def extract_item_stats(elements_path: str, cfg_name: str | None = None) -> dict[int, dict]:
    """
    Parse the gear essence tables for each item's base stats (Level Req, HP/MP,
    defenses, stat requirements, durability) -- the fields the item builder's
    Weapon/Armor/Jewelry panels show but have never auto-populated from the
    selected item. Returns {item_id: {normalized_field: value, ...}}.
    """
    cfg_path = _resolve_cfg(cfg_name, elements_path)
    conv_idx, tables = _load_config(cfg_path)
    data = Path(elements_path).read_bytes()
    pos = 4  # version (int16) + signature (int16)

    result: dict[int, dict] = {}

    for idx, tbl in enumerate(tables):
        name = tbl['name']
        if idx == 0:
            pos += tbl['offset']
        elif tbl['offset'] == 'AUTO' and idx == 20:
            pos += 4
            buf_len = struct.unpack_from('<I', data, pos)[0]; pos += 4
            pos += buf_len + 4
        elif tbl['offset'] == 'AUTO' and idx == 100:
            pos += 4
            buf_len = struct.unpack_from('<I', data, pos)[0]; pos += 4
            pos += buf_len
        elif isinstance(tbl['offset'], int) and tbl['offset'] > 0:
            pos += tbl['offset']

        if idx == conv_idx:
            pat_pos = data.find(b'facedata\\', pos)
            list_length = max(pat_pos - pos - 72, 0) if pat_pos != -1 else 0
            pos += list_length
            continue

        if pos + 4 > len(data):
            break
        count = struct.unpack_from('<i', data, pos)[0]; pos += 4
        if count < 0 or count > 200_000:
            break
        rec_size = tbl['rec_size']
        if rec_size == 0:
            continue

        field_map = _STAT_FIELD_MAP.get(name)
        if not field_map:
            pos += count * rec_size
            continue

        fields = tbl['fields']; types = tbl['types']
        for _ in range(count):
            rec_start = pos
            record = {}
            for fld, ftype in zip(fields, types):
                v, pos = _read_field(data, pos, ftype)
                record[fld] = v
            if pos != rec_start + rec_size:
                pos = rec_start + rec_size

            item_id = record.get('ID', 0)
            if not item_id:
                continue
            stats = {out_key: record.get(src_key, 0) or 0 for src_key, out_key in field_map.items()}
            if any(stats.values()):
                result[item_id] = stats

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

        print("Extracting inherent item addons (base-template variable bonuses)...", file=sys.stderr)
        addons_path = out_path.parent / "pw_item_addons.json"
        item_addons = extract_item_addons(el_path, cfg_name=args.config)
        addons_path.write_text(json.dumps(item_addons, ensure_ascii=False, indent=None), encoding="utf-8")
        print(f"Written inherent addons for {len(item_addons):,} items to {addons_path}", file=sys.stderr)

        print("Extracting item base stats (Level Req, HP/MP, defenses, stat reqs, durability)...", file=sys.stderr)
        stats_path = out_path.parent / "pw_item_stats.json"
        item_stats = extract_item_stats(el_path, cfg_name=args.config)
        stats_path.write_text(json.dumps(item_stats, ensure_ascii=False, indent=None), encoding="utf-8")
        print(f"Written base stats for {len(item_stats):,} items to {stats_path}", file=sys.stderr)

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=None), encoding="utf-8")
    total = sum(len(v) for subs in result.values() for v in subs.values())
    print(f"Written {total:,} items to {out_path}", file=sys.stderr)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
