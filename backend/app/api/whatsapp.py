"""
WhatsApp Web API endpoints
"""
from pathlib import Path
from typing import List, Optional, AsyncGenerator
import logging
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.whatsapp_client import WhatsAppClient, WhatsAppConnectionStatus
from app.services.whatsapp import whatsapp_service


router = APIRouter()
whatsapp_client = WhatsAppClient(Path(settings.SESSIONS_DIR) / "whatsapp")
logger = logging.getLogger(__name__)


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


@router.post("/connect", response_model=SessionResponse)
async def create_whatsapp_session():
    """
    Create a new WhatsApp Web session and generate QR code.
    """
    try:
        logger.info("API /connect: create session")
        session_id = whatsapp_client.create_session()
        return SessionResponse(
            session_id=session_id,
            status=WhatsAppConnectionStatus.DISCONNECTED.value,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")


@router.get("/{session_id}/qr", response_model=QRCodeResponse)
async def get_qr_code(session_id: str):
    """
    Get QR code for WhatsApp Web connection.
    """
    try:
        logger.info("API /%s/qr: fetching QR", session_id)
        qr_code = whatsapp_client.generate_qr_code(session_id)
        if qr_code is None:
            raise HTTPException(status_code=404, detail="Session not found")

        return QRCodeResponse(qr_code=qr_code, session_id=session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")


@router.get("/{session_id}/status", response_model=ConnectionStatusResponse)
async def get_connection_status(session_id: str):
    """
    Check WhatsApp Web connection status.
    """
    try:
        logger.info("API /%s/status: check status", session_id)
        status = whatsapp_client.get_connection_status(session_id)
        return ConnectionStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.post("/{session_id}/simulate-connect")
async def simulate_connection(session_id: str):
    """
    Simulate successful connection (for testing).
    In production, this would be handled automatically by WhatsApp Web API.
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


@router.get("/{session_id}/chats", response_model=ChatsResponse)
async def get_whatsapp_chats(session_id: str):
    """
    Get list of WhatsApp chats.
    """
    try:
        status = whatsapp_client.get_connection_status(session_id)
        if not status["connected"]:
            raise HTTPException(
                status_code=400,
                detail="WhatsApp Web is not connected. Please connect first.",
            )

        chats = whatsapp_client.get_chats(session_id)
        return ChatsResponse(chats=chats)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting chats: {str(e)}")


@router.post("/{session_id}/disconnect")
async def disconnect_whatsapp(session_id: str):
    """
    Disconnect WhatsApp Web session.
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
"""
WhatsApp Web connection API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.whatsapp import whatsapp_service
from app.services.file_manager import FileManager
from app.core.config import settings

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)


class ConnectResponse(BaseModel):
    session_id: str
    qr_code: str
    status: str
    expires_at: str


class ChatInfo(BaseModel):
    id: str
    name: str
    type: str
    avatar: Optional[str] = None
    message_count: int
    is_group: bool


class ChatsResponse(BaseModel):
    chats: List[ChatInfo]


class ConnectRequest(BaseModel):
    session_id: Optional[str] = None  # Optional: reuse existing session


@router.post("/connect", response_model=ConnectResponse)
async def connect_whatsapp(request: Optional[ConnectRequest] = None):
    """
    Start WhatsApp Web connection process
    
    If session_id is provided, tries to reuse existing session.
    Otherwise, creates a new session.
    
    Returns QR code for scanning and session_id for status polling
    """
    try:
        session_id = None
        
        # If session_id provided, try to reuse
        if request and request.session_id:
            session_id = request.session_id
            reuse_result = await whatsapp_service.try_reuse_session(session_id)
            
            if reuse_result.get("reused"):
                # Session successfully reused
                status = await whatsapp_service.get_status(session_id)
                return ConnectResponse(
                    session_id=session_id,
                    qr_code="",  # No QR needed
                    status=status.get("status", "ready"),
                    expires_at=""  # Not applicable
                )
            # If reuse failed, continue to create new session or use existing session_id
        
        # Generate new session ID if not provided or reuse failed
        if not session_id:
            session_id = file_manager.generate_session_id()
        
        # Start connection (will create new session or continue with existing)
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


@router.get("/chats/{session_id}/stream")
async def stream_whatsapp_chats(session_id: str):
    """
    Stream WhatsApp chats as they are loaded (Server-Sent Events)
    
    Requires session to be in 'ready' status
    """
    async def event_generator():
        try:
            # Check if session is connected
            if not whatsapp_service.is_connected(session_id):
                yield f"data: {json.dumps({'error': 'WhatsApp Web is not connected'})}\n\n"
                return
            
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Loading chats...'})}\n\n"
            
            # Stream chats as they are parsed
            async for chat_batch in whatsapp_service.get_chats_streaming(session_id):
                if chat_batch:
                    yield f"data: {json.dumps({'type': 'chats', 'chats': chat_batch})}\n\n"
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'message': 'All chats loaded'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error streaming chats for session {session_id}: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/chats/{session_id}", response_model=ChatsResponse)
async def get_whatsapp_chats(session_id: str):
    """
    Get list of WhatsApp chats from connected session
    
    Requires session to be in 'ready' status
    """
    try:
        # Check if session is connected
        if not whatsapp_service.is_connected(session_id):
            raise HTTPException(
                status_code=400,
                detail="WhatsApp Web is not connected. Please connect first.",
            )
        
        chats = await whatsapp_service.get_chats(session_id)
        return ChatsResponse(chats=chats)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting chats: {str(e)}")


@router.get("/messages/{session_id}/{chat_id}/stream")
async def stream_whatsapp_messages(session_id: str, chat_id: str, limit: Optional[int] = None, chat_name: Optional[str] = None):
    """
    Stream WhatsApp messages as they are loaded (Server-Sent Events)
    
    Optional query parameters:
    - limit: maximum number of messages to load
    - chat_name: real name of the chat (for more reliable chat opening)
    """
    async def event_generator():
        try:
            # Check if session is connected
            if not whatsapp_service.is_connected(session_id):
                yield f"data: {json.dumps({'type': 'error', 'error': 'WhatsApp Web is not connected'})}\n\n"
                return
            
            # Stream messages as they are parsed
            async for event in whatsapp_service.get_chat_messages_streaming(session_id, chat_id, limit, chat_name):
                yield f"data: {json.dumps(event)}\n\n"
            
        except Exception as e:
            logger.error(f"Error streaming messages for session {session_id}, chat {chat_id}: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/messages/{session_id}/{chat_id}")
async def get_whatsapp_messages(session_id: str, chat_id: str):
    """
    Get messages from a specific WhatsApp chat
    """
    try:
        # Check if session is connected
        if not whatsapp_service.is_connected(session_id):
            raise HTTPException(
                status_code=400,
                detail="WhatsApp Web is not connected. Please connect first.",
            )
        
        messages = await whatsapp_service.get_chat_messages(session_id, chat_id)
        return {"messages": messages, "count": len(messages)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting messages: {str(e)}")


@router.get("/sessions")
async def list_sessions():
    """
    List all existing WhatsApp sessions
    
    Returns list of session IDs that have browser data saved
    """
    try:
        sessions = whatsapp_service.list_existing_sessions()
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")


@router.post("/sessions/{session_id}/reuse")
async def reuse_session(session_id: str):
    """
    Try to reuse an existing WhatsApp session
    
    Returns status indicating if session was successfully reused
    """
    try:
        result = await whatsapp_service.try_reuse_session(session_id)
        
        if result.get("reused"):
            # Get full status
            status = await whatsapp_service.get_status(session_id)
            return {
                "reused": True,
                "session_id": session_id,
                "status": status
            }
        else:
            return {
                "reused": False,
                "session_id": session_id,
                "reason": result.get("reason", "Unknown reason")
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reusing session: {str(e)}")


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


@router.post("/sessions/cleanup")
async def cleanup_old_sessions(max_age_days: int = 7, max_sessions: Optional[int] = 100):
    """
    Cleanup old WhatsApp sessions from disk
    
    Query parameters:
        max_age_days: Delete sessions older than this many days (default: 7)
        max_sessions: Keep only the N most recent sessions (default: 100, None = no limit)
    """
    try:
        result = whatsapp_service.cleanup_old_sessions(max_age_days=max_age_days, max_sessions=max_sessions)
        return {
            "deleted": result["deleted"],
            "kept": result["kept"],
            "total_before": result["total_before"],
            "message": f"Cleaned up {result['deleted']} old sessions, kept {result['kept']}"
        }
    except Exception as e:
        logger.error("Error cleaning up old sessions: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error cleaning up old sessions: {str(e)}")
