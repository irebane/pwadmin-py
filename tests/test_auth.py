import hashlib
import base64
from unittest.mock import MagicMock


def test_hash_password_type1():
    from app.auth.passwords import hash_password_compat
    result = hash_password_compat("alice", "secret", 1)
    expected = "0x" + hashlib.md5("alicesecret".encode()).hexdigest()
    assert result == expected
    assert result.startswith("0x")
    assert len(result) == 34


def test_hash_password_type2():
    from app.auth.passwords import hash_password_compat
    result = hash_password_compat("Alice", "secret", 2)
    raw = hashlib.md5(("alice" + "secret").encode()).digest()
    expected = base64.b64encode(raw).decode()
    assert result == expected


def test_verify_password_compat_type1():
    from app.auth.passwords import hash_password_compat, verify_password_compat
    hashed = hash_password_compat("alice", "secret", 1)
    assert verify_password_compat("alice", "secret", hashed, 1)
    assert not verify_password_compat("alice", "wrong", hashed, 1)


def test_verify_password_compat_type2():
    from app.auth.passwords import hash_password_compat, verify_password_compat
    hashed = hash_password_compat("alice", "secret", 2)
    assert verify_password_compat("alice", "secret", hashed, 2)
    assert not verify_password_compat("alice", "wrong", hashed, 2)


def test_session_roundtrip():
    from app.auth.sessions import create_session, read_session
    response = MagicMock()
    captured_token = {}

    def capture_cookie(name, value, **kwargs):
        captured_token["value"] = value

    response.set_cookie.side_effect = capture_cookie
    data = {"id": 1, "name": "alice", "is_admin": True, "email": "a@b.com", "pw": "x"}
    create_session(response, data)

    request = MagicMock()
    request.cookies.get.return_value = captured_token.get("value")
    result = read_session(request)
    assert result is not None
    assert result["id"] == 1
    assert result["name"] == "alice"
    assert result["is_admin"] is True


def test_session_invalid_token():
    from app.auth.sessions import read_session
    request = MagicMock()
    request.cookies.get.return_value = "not-a-valid-token"
    assert read_session(request) is None


def test_session_missing_cookie():
    from app.auth.sessions import read_session
    request = MagicMock()
    request.cookies.get.return_value = None
    assert read_session(request) is None


def test_validate_date():
    from app.auth.passwords import validate_date
    assert validate_date("2024-01-15")
    assert not validate_date("01-15-2024")
    assert not validate_date("not-a-date")
