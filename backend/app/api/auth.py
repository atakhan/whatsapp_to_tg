"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
import logging
from app.core.security import verify_telegram_auth, extract_user_id
from app.services.telegram_client import TelegramClientWrapper
from app.services.file_manager import FileManager
from app.core.config import settings
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)
logger = logging.getLogger(__name__)


class TelegramAuthRequest(BaseModel):
    auth_data: Dict[str, str]


@router.post("/telegram-login")
async def telegram_login(request: TelegramAuthRequest):
    """
    Verify Telegram Login Widget authentication and initialize session
    """
    try:
        auth_data = request.auth_data
        
        # Verify authentication (for user auth, bot_token can be empty)
        # In production, you might want to use a bot token for additional security
        if not verify_telegram_auth(auth_data, settings.TELEGRAM_BOT_TOKEN or ""):
            raise HTTPException(status_code=401, detail="Invalid Telegram authentication")
        
        # Extract user ID
        user_id = extract_user_id(auth_data)
        if not user_id:
            raise HTTPException(status_code=400, detail="Could not extract user ID")
        
        # Initialize Telegram client
        session_path = file_manager.get_telegram_session_path(user_id)
        
        # Check if session exists
        if not session_path.exists():
            # Need to create session - this requires phone number authentication
            # For now, return user_id and let frontend handle phone auth
            return {
                "user_id": user_id,
                "session_exists": False,
                "requires_phone_auth": True
            }
        
        # Try to connect with existing session
        client_wrapper = TelegramClientWrapper(user_id, session_path)
        connected = await client_wrapper.connect()
        
        if connected:
            user_info = await client_wrapper.get_me()
            await client_wrapper.disconnect()
            
            return {
                "user_id": user_id,
                "session_exists": True,
                "user_info": user_info
            }
        else:
            return {
                "user_id": user_id,
                "session_exists": False,
                "requires_phone_auth": True
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error authenticating: {str(e)}")


@router.post("/telegram-phone-auth")
async def telegram_phone_auth(request: Dict):
    """
    Handle phone number authentication for Telegram
    This endpoint initiates phone auth flow
    Uses session_id instead of user_id (user_id will be obtained after auth)
    """
    try:
        session_id = request.get("session_id")
        phone = request.get("phone")
        
        if not session_id or not phone:
            raise HTTPException(status_code=400, detail="session_id and phone required")
        
        # Use session_id for session file path
        session_path = file_manager.sessions_dir / f"tg_{session_id}.session"
        
        # Create client
        client = TelegramClient(
            str(session_path),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
        
        await client.connect()
        
        # Send code
        sent_code = await client.send_code_request(phone)
        
        return {
            "phone_code_hash": sent_code.phone_code_hash,
            "session_id": session_id,
            "phone": phone
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating phone auth: {str(e)}")


@router.post("/telegram-verify-code")
async def telegram_verify_code(request: Dict):
    """
    Verify phone code and complete authentication
    """
    try:
        session_id = request.get("session_id")
        phone = request.get("phone")
        code = request.get("code")
        phone_code_hash = request.get("phone_code_hash")
        password = request.get("password")  # For 2FA
        
        if not all([session_id, phone, code, phone_code_hash]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        session_path = file_manager.sessions_dir / f"tg_{session_id}.session"
        
        client = TelegramClient(
            str(session_path),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
        
        await client.connect()
        
        try:
            # Sign in
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            # 2FA password required
            if not password:
                await client.disconnect()
                raise HTTPException(
                    status_code=400,
                    detail="2FA password required. Please provide password."
                )
            # Sign in with password
            await client.sign_in(password=password)
        
        user_info = await client.get_me()
        user_id = user_info.id
        
        # Rename session file to use user_id for consistency
        new_session_path = file_manager.get_telegram_session_path(user_id)
        if str(session_path) != str(new_session_path) and session_path.exists():
            try:
                # Close client before renaming
                await client.disconnect()
                # Rename session file
                import shutil
                shutil.move(str(session_path), str(new_session_path))
            except Exception as e:
                # If rename fails, it's okay - session is still valid
                logger.warning(
                    "Failed to rename Telegram session file",
                    extra={
                        "error_code": "TELEGRAM_SESSION_RENAME_FAIL",
                        "extra_data": {
                            "old_path": str(session_path),
                            "new_path": str(new_session_path),
                            "error": str(e)
                        },
                    },
                )
                await client.disconnect()
        else:
            await client.disconnect()
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "authenticated": True,
            "user_info": {
                "id": user_info.id,
                "first_name": user_info.first_name,
                "last_name": user_info.last_name,
                "username": user_info.username,
                "phone": user_info.phone
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying code: {str(e)}")
