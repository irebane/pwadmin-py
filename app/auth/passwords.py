import hashlib
import base64
import re
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def hash_password_compat(username: str, password: str, pass_type: int) -> str:
    """Reproduce the PHP hash stored in the DB for login verification."""
    if pass_type == 1:
        return "0x" + _md5(username + password)
    elif pass_type == 2:
        raw = hashlib.md5((username.lower() + password).encode()).digest()
        return base64.b64encode(raw).decode()
    elif pass_type == 3:
        return "0x" + _md5(username + password)
    raise ValueError(f"Unknown pass_type {pass_type}")


def verify_password_compat(username: str, password: str, stored_hash: str, pass_type: int) -> bool:
    """Verify login against the PHP-compatible hash stored in MySQL."""
    computed = hash_password_compat(username, password, pass_type)
    if pass_type == 3:
        return computed.lower() == ("0x" + stored_hash.lower()).lower() or \
               computed[2:].lower() == stored_hash.lower()
    return computed == stored_hash


def hash_password_bcrypt(password: str) -> str:
    """For new accounts created via the Python app."""
    return pwd_context.hash(password)


def verify_password_bcrypt(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def validate_date(date_str: str) -> bool:
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))
