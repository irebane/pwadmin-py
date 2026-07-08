"""
Reads the GM_ACTIVITY_CONFIG table (in-game "events" — holiday activities, siege
activation, etc.) out of the server's elements.data.

The openlist/closelist fields are NOT decoded — every record observed so far has
openlist_N == closelist_N for every used slot, which rules out a plain schedule
window (open time != close time, normally). They're most likely references into
some other trigger/task system rather than raw weekday/hour/timestamp values.
Exposed here as-is (raw ints) until that's understood; no edit/patch capability
yet — see docs/zone-lifecycle-and-gm-protocol.md-style investigation notes.
"""
import sys
from pathlib import Path
from app.config import settings

_TOOLS_DIR = Path(__file__).parent.parent.parent / "tools"
_TABLE_NAME = "159 - GM_ACTIVITY_CONFIG"


def _elements_path() -> str:
    return f"{settings.server_path.rstrip('/')}/gamed/config/elements.data"


def parse_gm_activity_config(elements_path: str | None = None, cfg_name: str | None = None) -> list[dict]:
    """Return every GM_ACTIVITY_CONFIG record as
    {"id", "name", "openlist": [8 ints], "closelist": [8 ints], "disabled": bool}."""
    sys.path.insert(0, str(_TOOLS_DIR))
    from generate_items import _load_config, _read_field, _iter_tables, _resolve_cfg

    path = elements_path or _elements_path()
    if not Path(path).exists():
        return []

    cfg_path = _resolve_cfg(cfg_name, path)
    conv_idx, tables = _load_config(cfg_path)
    data = Path(path).read_bytes()

    records: list[dict] = []
    for idx, tbl, count, pos in _iter_tables(data, tables, conv_idx):
        if tbl['name'] != _TABLE_NAME:
            continue
        if count is None or tbl['rec_size'] == 0:
            break
        fields = tbl['fields']
        types = tbl['types']
        for _ in range(count):
            rec_start = pos
            record: dict = {}
            for fld, ftype in zip(fields, types):
                v, pos = _read_field(data, pos, ftype)
                record[fld] = v
            if pos != rec_start + tbl['rec_size']:
                pos = rec_start + tbl['rec_size']
            records.append({
                "id": record.get("ID", 0),
                "name": record.get("Name", "") or "",
                "openlist": [record.get(f"openlist_{n}", 0) or 0 for n in range(1, 9)],
                "closelist": [record.get(f"closelist_{n}", 0) or 0 for n in range(1, 9)],
                "disabled": bool(record.get("disabled", 0)),
            })
        break
    return records
