"""
Migration API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
import json
from app.services.migration_manager import MigrationManager
from app.services.telegram_client import TelegramClientWrapper
from app.services.file_manager import FileManager
from app.core.config import settings

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)

# Store active migrations
active_migrations: dict[str, MigrationManager] = {}


class StartMigrationRequest(BaseModel):
    session_id: str
    user_id: int
    target_chat_id: int


async def run_migration(session_id: str, user_id: int, target_chat_id: int):
    """Background task to run migration"""
    try:
        session_path = file_manager.get_session_path(session_id)
        
        # Load messages
        messages_file = session_path / "messages.json"
        if not messages_file.exists():
            raise ValueError("Messages file not found")
        
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # Initialize migration manager
        manager = MigrationManager(session_id, session_path)
        manager.load_messages(messages)
        manager.set_target_chat(target_chat_id)
        
        # Initialize Telegram client
        telegram_session_path = file_manager.get_telegram_session_path(user_id)
        client_wrapper = TelegramClientWrapper(user_id, telegram_session_path)
        connected = await client_wrapper.connect()
        
        if not connected:
            raise ValueError("Could not connect to Telegram")
        
        manager.set_client(client_wrapper)
        
        # Store manager
        active_migrations[session_id] = manager
        
        # Run migration
        await manager.start_migration()
        
        # Cleanup
        await client_wrapper.disconnect()
        
    except Exception as e:
        print(f"Migration error: {e}")
        if session_id in active_migrations:
            active_migrations[session_id].status["errors"].append(str(e))
            active_migrations[session_id]._save_status()


@router.post("/start")
async def start_migration(request: StartMigrationRequest, background_tasks: BackgroundTasks):
    """
    Start migration process
    """
    try:
        session_path = file_manager.get_session_path(request.session_id)
        
        # Check if messages are parsed
        messages_file = session_path / "messages.json"
        if not messages_file.exists():
            raise HTTPException(status_code=400, detail="Messages not parsed yet")
        
        # Check if Telegram session exists
        telegram_session_path = file_manager.get_telegram_session_path(request.user_id)
        if not telegram_session_path.exists():
            raise HTTPException(status_code=404, detail="Telegram session not found")
        
        # Start migration in background
        background_tasks.add_task(
            run_migration,
            request.session_id,
            request.user_id,
            request.target_chat_id
        )
        
        return {
            "session_id": request.session_id,
            "status": "started",
            "message": "Migration started"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting migration: {str(e)}")


@router.get("/status/{session_id}")
async def get_migration_status(session_id: str):
    """
    Get migration status
    """
    try:
        session_path = file_manager.get_session_path(session_id)
        status_file = session_path / "migration_status.json"
        
        if session_id in active_migrations:
            # Get live status
            status = active_migrations[session_id].get_status()
        elif status_file.exists():
            # Load from file
            with open(status_file, 'r') as f:
                status = json.load(f)
        else:
            raise HTTPException(status_code=404, detail="Migration not found")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.post("/stop/{session_id}")
async def stop_migration(session_id: str):
    """
    Stop migration process
    """
    try:
        if session_id in active_migrations:
            active_migrations[session_id].stop_migration()
            return {"status": "stopped", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Migration not found")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping migration: {str(e)}")


@router.post("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """
    Cleanup session files after migration
    """
    try:
        success = file_manager.cleanup_session(session_id)
        
        if session_id in active_migrations:
            del active_migrations[session_id]
        
        return {
            "session_id": session_id,
            "cleaned": success
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up: {str(e)}")
