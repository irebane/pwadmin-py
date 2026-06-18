from app.services.server_config import parse_conf_key, update_conf_key


def test_parse_conf_key_basic():
    content = "exp_bonus = 100\npvp = 0\n"
    assert parse_conf_key(content, "exp_bonus") == "100"
    assert parse_conf_key(content, "pvp") == "0"


def test_parse_conf_key_missing():
    content = "pvp = 0\n"
    assert parse_conf_key(content, "missing") is None


def test_parse_conf_key_case_insensitive():
    content = "EXP_BONUS = 50\n"
    assert parse_conf_key(content, "exp_bonus") == "50"


def test_parse_conf_key_tab_separator():
    content = "exp_bonus\t=\t100\n"
    assert parse_conf_key(content, "exp_bonus") == "100"


def test_update_conf_key_existing():
    content = "exp_bonus = 100\npvp = 0\n"
    updated = update_conf_key(content, "exp_bonus", "200")
    assert "exp_bonus = 200" in updated
    assert "exp_bonus = 100" not in updated


def test_update_conf_key_preserves_other():
    content = "exp_bonus = 100\npvp = 1\n"
    updated = update_conf_key(content, "exp_bonus", "200")
    assert "pvp = 1" in updated


def test_update_conf_key_new_entry():
    content = "pvp = 0\n"
    updated = update_conf_key(content, "exp_bonus", "100")
    assert "exp_bonus = 100" in updated
    assert "pvp = 0" in updated


def test_update_conf_key_roundtrip():
    content = "exp_bonus = 0\nsp_bonus = 0\n"
    content = update_conf_key(content, "exp_bonus", "200")
    content = update_conf_key(content, "sp_bonus", "100")
    assert parse_conf_key(content, "exp_bonus") == "200"
    assert parse_conf_key(content, "sp_bonus") == "100"


def test_daemon_status_names():
    from app.services.server_status import SERVER_DAEMON_NAMES
    assert "gamedbd" in SERVER_DAEMON_NAMES
    assert "gamed" in SERVER_DAEMON_NAMES
    assert "glinkd" in SERVER_DAEMON_NAMES
    assert len(SERVER_DAEMON_NAMES) >= 5
