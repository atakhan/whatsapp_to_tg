"""
Security utilities for Telegram authentication
"""
import hashlib
import hmac
from typing import Dict, Optional


def verify_telegram_auth(auth_data: Dict[str, str], bot_token: str) -> bool:
    """
    Verify Telegram Login Widget authentication data
    
    Args:
        auth_data: Dictionary with id, first_name, username, photo_url, auth_date, hash
        bot_token: Telegram bot token (optional, can be empty for user auth)
    
    Returns:
        True if authentication is valid
    """
    if not auth_data.get("hash"):
        return False
    
    # Create data check string
    check_string_parts = []
    for key in sorted(auth_data.keys()):
        if key != "hash":
            check_string_parts.append(f"{key}={auth_data[key]}")
    
    check_string = "\n".join(check_string_parts)
    
    # Calculate secret key
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return calculated_hash == auth_data["hash"]


def extract_user_id(auth_data: Dict[str, str]) -> Optional[int]:
    """Extract Telegram user ID from auth data"""
    try:
        return int(auth_data.get("id", 0))
    except (ValueError, TypeError):
        return None
