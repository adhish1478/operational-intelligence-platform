import time
import jwt
from app.core.security import decode_token

# Dictionary mapping raw token strings to their expiration timestamp (epoch seconds)
_blocklisted_tokens: dict[str, float] = {}

def blocklist_token(token: str) -> None:
    """
    Decodes the token to find its expiration timestamp, and adds it to the blocklist.
    """
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp is not None:
            _blocklisted_tokens[token] = float(exp)
        else:
            # Default fallback to current time + 15 minutes if no exp claim is present
            _blocklisted_tokens[token] = time.time() + 900
    except Exception:
        # Fallback to current time + 15 minutes if decoding fails
        _blocklisted_tokens[token] = time.time() + 900


def is_token_blocklisted(token: str) -> bool:
    """
    Checks if a token is in the blocklist. Prunes expired tokens in the process
    to prevent memory leak build-ups.
    """
    now = time.time()
    
    # Prune expired tokens
    expired_keys = [t for t, exp in _blocklisted_tokens.items() if exp < now]
    for key in expired_keys:
        _blocklisted_tokens.pop(key, None)
        
    return token in _blocklisted_tokens
