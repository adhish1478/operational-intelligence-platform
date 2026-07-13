from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt
from app.core.config import settings

# JWT Secret configurations
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Generate a secure bcrypt hash of a plaintext password.
    """
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a pre-calculated bcrypt hash.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def create_token(
    subject: str | Any, 
    expires_delta: timedelta, 
    token_type: str = "access"
) -> str:
    """
    Create a signed JSON Web Token (JWT) with custom claims.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "exp": now + expires_delta,
        "iat": now,
        "type": token_type
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JSON Web Token signature and expiration.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError if invalid.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])


def get_fernet_key() -> bytes:
    """
    Derive a 32-byte URL-safe base64 key from settings.SECRET_KEY.
    """
    import base64
    import hashlib
    key_hash = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    """
    Encrypt a dictionary of credentials (e.g. API keys, tokens) to a secure cipher string.
    """
    import json
    from cryptography.fernet import Fernet
    fernet_key = get_fernet_key()
    fernet = Fernet(fernet_key)
    serialized = json.dumps(credentials)
    return fernet.encrypt(serialized.encode()).decode()


def decrypt_credentials(encrypted_string: str) -> dict[str, Any]:
    """
    Decrypt a cipher string back to the credentials dictionary.
    """
    import json
    from cryptography.fernet import Fernet
    fernet_key = get_fernet_key()
    fernet = Fernet(fernet_key)
    decrypted_bytes = fernet.decrypt(encrypted_string.encode())
    return json.loads(decrypted_bytes.decode())

