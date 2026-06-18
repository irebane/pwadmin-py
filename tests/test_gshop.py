import struct
from app.services.gshop import parse_gshop_records, build_gshop_binary, HEADER_SIZE, RECORD_SIZE, FIELDS_PER_RECORD


def _make_test_data(records: list[dict]) -> bytes:
    count = len(records)
    header = b"\x00\x00\x00\x00" + struct.pack("<I", count)
    body = bytearray()
    for r in records:
        block = bytearray(RECORD_SIZE)
        vals = [
            r.get("shop_id", 0), r.get("main_cat", 0), r.get("sub_cat", 0),
            r.get("item_id", 0), r.get("qty", 1), r.get("price", 0),
            0, r.get("duration", 0), 0, r.get("class_mask", 0),
        ]
        for j, v in enumerate(vals):
            struct.pack_into("<I", block, j * 4, v)
        body += block
    return header + bytes(body)


def test_parse_empty():
    raw = b"\x00\x00\x00\x00" + struct.pack("<I", 0)
    records = parse_gshop_records(raw)
    assert records == []


def test_parse_one_record():
    r = {"shop_id": 1, "main_cat": 2, "sub_cat": 3, "item_id": 4242, "qty": 5, "price": 100, "duration": 0, "class_mask": 0}
    raw = _make_test_data([r])
    records = parse_gshop_records(raw)
    assert len(records) == 1
    assert records[0]["item_id"] == 4242
    assert records[0]["price"] == 100
    assert records[0]["qty"] == 5
    assert records[0]["idx"] == 0


def test_parse_multiple_records():
    items = [
        {"shop_id": 1, "item_id": 1001, "qty": 1, "price": 100},
        {"shop_id": 2, "item_id": 1002, "qty": 5, "price": 500},
        {"shop_id": 3, "item_id": 1003, "qty": 10, "price": 1000},
    ]
    raw = _make_test_data(items)
    records = parse_gshop_records(raw)
    assert len(records) == 3
    assert records[2]["item_id"] == 1003


def test_roundtrip():
    records = [
        {"shop_id": 1, "main_cat": 1, "sub_cat": 1, "item_id": 1001, "qty": 1, "price": 500, "duration": 0, "class_mask": 0},
        {"shop_id": 2, "main_cat": 1, "sub_cat": 2, "item_id": 1002, "qty": 2, "price": 1000, "duration": 86400, "class_mask": 255},
    ]
    raw = _make_test_data(records)
    parsed = parse_gshop_records(raw)
    rebuilt = build_gshop_binary(raw[:HEADER_SIZE], parsed)
    re_parsed = parse_gshop_records(rebuilt)
    assert len(re_parsed) == 2
    assert re_parsed[0]["item_id"] == 1001
    assert re_parsed[1]["duration"] == 86400
    assert re_parsed[1]["class_mask"] == 255


def test_record_constants():
    assert RECORD_SIZE == 148
    assert FIELDS_PER_RECORD == 37
    assert FIELDS_PER_RECORD * 4 == RECORD_SIZE


def test_build_updates_count():
    raw = _make_test_data([{"item_id": 1}, {"item_id": 2}])
    parsed = parse_gshop_records(raw)
    parsed_1 = parsed[:1]
    rebuilt = build_gshop_binary(raw[:HEADER_SIZE], parsed_1)
    count = struct.unpack_from("<I", rebuilt, 4)[0]
    assert count == 1


def test_items_service_no_file():
    from app.services.items import search_items
    result = search_items("test", limit=10)
    assert isinstance(result, list)
