"""
WhatsApp Web connection API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.whatsapp_connect import whatsapp_service
from app.services.file_manager import FileManager
from app.core.config import settings

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)


class ConnectResponse(BaseModel):
    session_id: str
    qr_code: str
    status: str
    expires_at: str


@router.post("/connect", response_model=ConnectResponse)
async def connect_whatsapp():
    """
    Start WhatsApp Web connection process
    
    Returns QR code for scanning and session_id for status polling
    """
    try:
        # Generate session ID
        session_id = file_manager.generate_session_id()
        
        # Start connection
        result = await whatsapp_service.start_connection(session_id)
        
        return ConnectResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting WhatsApp connection: {str(e)}")


@router.get("/status/{session_id}")
async def get_connection_status(session_id: str):
    """
    Get WhatsApp Web connection status
    
    Returns current status and QR code if still waiting
    """
    try:
        status = await whatsapp_service.get_status(session_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """
    Cleanup WhatsApp session and close browser context
    """
    try:
        success = await whatsapp_service.cleanup_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "cleaned": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up session: {str(e)}")
