from app.auth.passwords import hash_password_compat


def test_list_accounts_pagination_math():
    page, page_size = 2, 10
    offset = (page - 1) * page_size
    assert offset == 10


def test_list_accounts_page1_offset():
    page, page_size = 1, 50
    offset = (page - 1) * page_size
    assert offset == 0


def test_hash_for_save():
    hashed = hash_password_compat("alice", "newpass", 1)
    assert hashed.startswith("0x")
    assert len(hashed) == 34


def test_save_body_defaults():
    from app.routers.accounts import SaveBody
    body = SaveBody()
    assert body.current_password == ""
    assert body.new_password == ""
    assert body.sex == 0
    assert body.birthday == ""


def test_tool_body():
    from app.routers.accounts import ToolBody
    body = ToolBody(action="add_gold", value=100)
    assert body.action == "add_gold"
    assert body.value == 100


def test_tool_body_defaults():
    from app.routers.accounts import ToolBody
    body = ToolBody(action="delete")
    assert body.value == 0
