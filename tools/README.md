# generate_items.py

Regenerates `data/pw_items.json` (the item name database used by Item Builder and G-Shop) from one of two sources:

- **elements.data** — your game server's binary item database (most up-to-date)
- **pw_items.php** — a PHP item list file (alternative, useful if you don't have elements.data)

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

## How it works

### elements.data mode

`elements.data` is a binary database that contains all game objects — items, NPCs, mobs, skills, maps, and more. The tool scans it for item records by looking for valid item IDs (4000–40000) followed by a UTF-16LE item name 12 bytes later.

Items with star quality prefixes (☆/★/✦) that are not already in the existing `pw_items.json` are appended to type 8 / subtype 99 ("Other — new"). All existing items have their names refreshed from the binary.

### php mode

Parses `$ItemMod[type][sub][] = "name#id#grade#color#addon";` assignments and converts them directly to JSON.

---

## Admin panel (no SSH needed)

The **Server** page in the admin panel has an **Item Database** section where you can:

1. **Upload** your `elements.data` file from any computer
2. Click **Regenerate** to rebuild `pw_items.json` from it
3. **Switch** between saved backups if you want to roll back
4. **Delete** old backups to free space

---

## Output format

```json
{
  "1": {
    "1": ["☆☆☆Iron Sword#4567#1#2#0", "☆Blade of Dawn#4999#3#1#0"],
    "2": ["..."]
  },
  "8": {
    "99": ["☆☆New Item#19500#0#0#0"]
  }
}
```

Each string: `name#item_id#grade#color#addon_flags`

Type and subtype numbers match the Item Builder category tree.
