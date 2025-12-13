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


@router.post("/contacts")
async def get_contacts(request: GetContactsRequest):
    """
    Get list of Telegram contacts/chats
    """
    try:
        session_path = file_manager.get_telegram_session_path(request.user_id)
        
        if not session_path.exists():
            raise HTTPException(status_code=404, detail="Telegram session not found")
        
        client_wrapper = TelegramClientWrapper(request.user_id, session_path)
        connected = await client_wrapper.connect()
        
        if not connected:
            raise HTTPException(status_code=401, detail="Could not connect to Telegram")
        
        dialogs = await client_wrapper.get_dialogs()
        await client_wrapper.disconnect()
        
        return {
            "contacts": dialogs,
            "count": len(dialogs)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting contacts: {str(e)}")
