"""
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


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

