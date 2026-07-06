# generate_items.py

Regenerates `data/pw_items.json` (the item name database used by Item Builder and G-Shop) from one of two sources:

- **elements.data** — your game server's binary item database (recommended, correct categories)
- **pw_items.php** — a PHP item list file (fallback), in the format used by
  [shadowvzs/pwAdmin](https://github.com/shadowvzs/pwAdmin)

Before overwriting, the current `pw_items.json` is always backed up to `data/backups/pw_items_YYYYMMDD_HHMMSS.json.bak`.

---

## Usage

Run from the `pwadmin-py` root directory.

### From elements.data (recommended)

```bash
# Auto-detect: reads SERVER_PATH from .env, appends /gamed/config/elements.data
python3 tools/generate_items.py --source elements

# Explicit path
python3 tools/generate_items.py --source elements --elements /home/gamed/config/elements.data
```

### From pw_items.php

```bash
python3 tools/generate_items.py --source php --php /path/to/pw_items.php
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--source` | `php` | `elements` or `php` |
| `--elements` | `$SERVER_PATH/gamed/config/elements.data` | Path to elements.data |
| `--php` | — | Path to pw_items.php |
| `--output` | `data/pw_items.json` | Output file |
| `--no-backup` | off | Skip backup step |

---

## Admin panel (no SSH needed)

The **Server** page in the admin panel has an **Item Database** section where you can:

1. **Upload** your `elements.data` file from any computer
2. Click **Regenerate** to rebuild `pw_items.json` from it
3. **Switch** between saved backups if you want to roll back
4. **Delete** old backups to free space

---

## How it works

### elements.data mode

`elements.data` is a v27 binary database containing all game objects. The tool uses `PW_1.4.2_v27.cfg` to walk all 129 tables sequentially, reading exact record sizes for each table. For every item essence table (WEAPON_ESSENCE, ARMOR_ESSENCE, DECORATION_ESSENCE, FASHION_ESSENCE, etc.) it extracts the item ID and name, then assigns the correct type/subtype based on which table the item came from:

| Table | Type | Sub-type |
|---|---|---|
| WEAPON_ESSENCE | 1 (Weapon) | by weapon sub-type |
| ARMOR_ESSENCE | 2 (Armor) | by armor sub-type |
| DECORATION_ESSENCE | 3 (Jewelry) | by decoration sub-type |
| FLYSWORD_ESSENCE | 4 (Flyer/Pet) | 1 (flying swords) |
| WINGMANWING_ESSENCE | 4 (Flyer/Pet) | 2 (wings) |
| PET_ESSENCE | 4 (Flyer/Pet) | 3 (pets) |
| PET_EGG_ESSENCE | 4 (Flyer/Pet) | 4 (pet eggs) |
| DAMAGERUNE_ESSENCE | 5 (Elf) | 1 |
| ARMORRUNE_ESSENCE | 5 (Elf) | 2 |
| FASHION_ESSENCE | 6 (Fashion) | by fashion sub-type |
| MEDICINE_ESSENCE | 7 (Misc) | 1 |
| MATERIAL_ESSENCE | 7 (Misc) | 2 |
| SKILLTOME_ESSENCE | 7 (Misc) | 3 |
| STONE_ESSENCE | 7 (Misc) | 6 |
| everything else | 7 (Misc) | varies |

Items not belonging to any of these tables are excluded. This ensures no "Wrong Item" errors from items that exist in other server versions but not in this one.

### php mode

Parses `$ItemMod[type][sub][] = "name#id#grade#color#addon";` assignments and converts them directly to JSON.

---

## Output format

```json
{
  "1": {
    "1": ["☆☆☆Iron Sword#4567#1#2#0", "☆Blade of Dawn#4999#3#1#0"],
    "2": ["..."]
  },
  "6": {
    "2": ["Fairy Dress#19200#0#0#0", "Summer Chipao#19210#0#0#0"]
  }
}
```

Each string: `name#item_id#grade#color#addon_flags`

Type and subtype numbers match the Item Builder category tree.
