"""
Parse API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from app.services.whatsapp_parser import WhatsAppParser
from app.services.file_manager import FileManager
from app.core.config import settings
import json

router = APIRouter()
file_manager = FileManager(settings.TMP_DIR, settings.SESSIONS_DIR)


class ParseRequest(BaseModel):
    session_id: str


@router.post("/parse")
async def parse_whatsapp_export(request: ParseRequest):
    """
    Parse WhatsApp export and return messages
    """
    try:
        session_path = file_manager.get_session_path(request.session_id)
        extract_path = session_path / "extracted"
        
        if not extract_path.exists():
            raise HTTPException(status_code=404, detail="Extracted files not found")
        
        # Parse export
        parser = WhatsAppParser(extract_path)
        messages = parser.parse()
        
        # Save parsed messages
        messages_file = session_path / "messages.json"
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        return {
            "session_id": request.session_id,
            "messages_count": len(messages),
            "messages": messages[:10]  # Return first 10 as preview
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing export: {str(e)}")
