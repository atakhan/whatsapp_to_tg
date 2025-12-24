"""
WhatsApp Web service modules
"""
from app.services.whatsapp.whatsapp_service import WhatsAppConnectService

# Global service instance for backward compatibility
whatsapp_service = WhatsAppConnectService()

__all__ = ['WhatsAppConnectService', 'whatsapp_service']
