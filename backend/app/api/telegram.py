"""
Telegram API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.telegram_client import TelegramClientWrapper
from app.services.file_manager import FileManager
from app.core.config import settings

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)


class GetContactsRequest(BaseModel):
    user_id: int


class CheckSessionRequest(BaseModel):
    user_id: int


@router.post("/check-session")
async def check_session(request: CheckSessionRequest):
    """
    Check if Telegram session exists and is valid for given user_id
    """
    client_wrapper = None
    try:
        session_path = file_manager.get_telegram_session_path(request.user_id)
        
        if not session_path.exists():
            return {
                "session_exists": False,
                "valid": False
            }
        
        client_wrapper = TelegramClientWrapper(request.user_id, session_path)
        connected = await client_wrapper.connect(retries=2, retry_delay=1.0)
        
        if connected:
            user_info = await client_wrapper.get_me()
            await client_wrapper.disconnect()
            
            return {
                "session_exists": True,
                "valid": True,
                "user_info": {
                    "id": user_info.id,
                    "first_name": user_info.first_name,
                    "last_name": user_info.last_name,
                    "username": user_info.username,
                    "phone": user_info.phone
                }
            }
        else:
            return {
                "session_exists": True,
                "valid": False
            }
    
    except Exception as e:
        return {
            "session_exists": True,
            "valid": False,
            "error": str(e)
        }
    finally:
        if client_wrapper:
            try:
                await client_wrapper.disconnect()
            except Exception:
                pass


@router.post("/contacts")
async def get_contacts(request: GetContactsRequest):
    """
    Get list of Telegram contacts/chats
    """
    client_wrapper = None
    try:
        session_path = file_manager.get_telegram_session_path(request.user_id)
        
        if not session_path.exists():
            raise HTTPException(status_code=404, detail="Telegram session not found")
        
        client_wrapper = TelegramClientWrapper(request.user_id, session_path)
        connected = await client_wrapper.connect(retries=3, retry_delay=2.0)
        
        if not connected:
            raise HTTPException(status_code=401, detail="Could not connect to Telegram")
        
        dialogs = await client_wrapper.get_dialogs()
        
        return {
            "contacts": dialogs,
            "count": len(dialogs)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting contacts: {str(e)}")
    finally:
        # Always disconnect, even on error
        if client_wrapper:
            try:
                await client_wrapper.disconnect()
            except Exception:
                pass
