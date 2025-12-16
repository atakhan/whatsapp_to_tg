"""
<<<<<<< HEAD
WhatsApp Web API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from app.services.whatsapp_client import WhatsAppClient, WhatsAppConnectionStatus
from app.core.config import settings
from pathlib import Path
import asyncio

router = APIRouter()
whatsapp_client = WhatsAppClient(Path(settings.SESSIONS_DIR) / "whatsapp")


class SessionResponse(BaseModel):
    session_id: str
    status: str


class QRCodeResponse(BaseModel):
    qr_code: str
    session_id: str


class ConnectionStatusResponse(BaseModel):
    status: str
    connected: bool
    qr_code: Optional[str] = None


class ChatInfo(BaseModel):
    id: str
    name: str
    type: str
    avatar: Optional[str] = None
    message_count: int
    is_group: bool


class ChatsResponse(BaseModel):
    chats: List[ChatInfo]


@router.post("/whatsapp/connect", response_model=SessionResponse)
async def create_whatsapp_session():
    """
    Create a new WhatsApp Web session and generate QR code
    """
    try:
        session_id = whatsapp_client.create_session()
        return SessionResponse(
            session_id=session_id,
            status=WhatsAppConnectionStatus.DISCONNECTED.value
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")


@router.get("/whatsapp/{session_id}/qr", response_model=QRCodeResponse)
async def get_qr_code(session_id: str):
    """
    Get QR code for WhatsApp Web connection
    """
    try:
        qr_code = whatsapp_client.generate_qr_code(session_id)
        if qr_code is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return QRCodeResponse(
            qr_code=qr_code,
            session_id=session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")


@router.get("/whatsapp/{session_id}/status", response_model=ConnectionStatusResponse)
async def get_connection_status(session_id: str):
    """
    Check WhatsApp Web connection status
    """
    try:
        status = whatsapp_client.get_connection_status(session_id)
        return ConnectionStatusResponse(**status)
=======
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
>>>>>>> 238e4525065f659f2c1cbbf992fe83989d87a964
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


<<<<<<< HEAD
@router.post("/whatsapp/{session_id}/simulate-connect")
async def simulate_connection(session_id: str):
    """
    Simulate successful connection (for testing)
    In production, this would be handled automatically by WhatsApp Web API
    """
    try:
        success = whatsapp_client.simulate_connection(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "connected", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating connection: {str(e)}")


@router.get("/whatsapp/{session_id}/chats", response_model=ChatsResponse)
async def get_whatsapp_chats(session_id: str):
    """
    Get list of WhatsApp chats
    """
    try:
        status = whatsapp_client.get_connection_status(session_id)
        if not status["connected"]:
            raise HTTPException(
                status_code=400,
                detail="WhatsApp Web is not connected. Please connect first."
            )
        
        chats = whatsapp_client.get_chats(session_id)
        return ChatsResponse(chats=chats)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting chats: {str(e)}")


@router.post("/whatsapp/{session_id}/disconnect")
async def disconnect_whatsapp(session_id: str):
    """
    Disconnect WhatsApp Web session
    """
    try:
        success = whatsapp_client.disconnect(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "disconnected", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")

=======
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
>>>>>>> 238e4525065f659f2c1cbbf992fe83989d87a964
