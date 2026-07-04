import json
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_items() -> dict:
    path = Path("data/pw_items.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_item_addons() -> dict:
    path = Path("data/pw_item_addons.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_inherent_addons(item_id: int) -> list[dict]:
    """Return an item's built-in variable-range bonus addons, e.g. an armor's
    inherent 'Strength +3~4' — see tools/generate_items.py:extract_item_addons."""
    return _load_item_addons().get(str(item_id), [])


@lru_cache(maxsize=1)
def _load_item_stats() -> dict:
    path = Path("data/pw_item_stats.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_item_stats(item_id: int) -> dict:
    """Return an item's base stats (Level Req, HP/MP, defenses, stat reqs,
    durability) — see tools/generate_items.py:extract_item_stats."""
    return _load_item_stats().get(str(item_id), {})


@lru_cache(maxsize=None)
def _build_id_map() -> dict[int, str]:
    """Build item_id → name map from the nested structure."""
    items = _load_items()
    id_map = {}
    for type_group in items.values():
        for subtype_list in type_group.values():
            entries = subtype_list.values() if isinstance(subtype_list, dict) else subtype_list
            for entry in entries:
                parts = entry.split("#")
                if len(parts) < 2:
                    continue
                try:
                    iid = int(parts[1])
                except ValueError:
                    continue
                if iid > 0 and iid not in id_map:
                    name = parts[0].strip().lstrip("☆★✦ ")
                    id_map[iid] = name or parts[0]
    return id_map


def get_item_name(item_id: int) -> str | None:
    return _build_id_map().get(item_id)


def search_items(query: str, limit: int = 100) -> list[dict]:
    q = query.lower()
    return [
        {"id": k, "name": v}
        for k, v in _build_id_map().items()
        if q in v.lower()
    ][:limit]
