"""
Upload API endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.file_manager import FileManager
from app.core.config import settings
import shutil
from pathlib import Path

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)


@router.post("/upload")
async def upload_whatsapp_export(file: UploadFile = File(...)):
    """
    Upload WhatsApp export ZIP file
    
    Returns session_id for tracking the upload
    """
    # Check file size
    file_size = 0
    temp_path = None
    
    try:
        # Generate session ID
        session_id = file_manager.generate_session_id()
        session_dir = file_manager.create_session_dir(session_id)
        temp_path = session_dir / file.filename
        
        # Save file with size checking
        with open(temp_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)  # 8KB chunks
                if not chunk:
                    break
                file_size += len(chunk)
                
                if file_size > settings.MAX_ZIP_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {settings.MAX_ZIP_SIZE / (1024**3):.1f}GB"
                    )
                
                buffer.write(chunk)
        
        # Extract ZIP
        extract_path = file_manager.extract_zip(temp_path, session_id)
        
        # Remove ZIP file after extraction
        temp_path.unlink()
        
        return {
            "session_id": session_id,
            "extracted_path": str(extract_path),
            "file_size": file_size
        }
    
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup on error
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
