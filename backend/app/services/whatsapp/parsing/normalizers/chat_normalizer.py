"""
Chat normalizer - converts RawChat to ChatDTO.
"""

from typing import List, Optional, TYPE_CHECKING
import logging

from ..models.raw_chat import RawChat
from ..models.chat_dto import ChatDTO

if TYPE_CHECKING:
    from ..identity.identity_resolver import IdentityResolver

logger = logging.getLogger(__name__)


class ChatNormalizer:
    """
    Normalizes raw chat data into unified ChatDTO format.
    
    Handles:
    - Type determination (personal/group/broadcast)
    - Integrity status assignment
    - Field mapping from various sources
    """
    
    def normalize(self, raw_chat: RawChat, chat_id: Optional[str] = None) -> ChatDTO:
        """
        Normalize a single RawChat to ChatDTO.
        
        Args:
            raw_chat: Raw chat data from source
            chat_id: Optional pre-extracted chat ID (from IdentityResolver)
            
        Returns:
            Normalized ChatDTO
            
        Note:
            If chat_id is not provided, it should be set later by IdentityResolver.
            For now, we'll use a placeholder if ID extraction is needed.
        """
        # Determine chat type
        chat_type = self._determine_type(raw_chat)
        
        # Determine integrity status
        integrity = self._determine_integrity(raw_chat)
        
        # Use provided ID or placeholder (will be set by IdentityResolver)
        final_id = chat_id or ""  # Empty string as placeholder
        
        # Normalize name (clean up whitespace, handle None)
        normalized_name = None
        if raw_chat.name:
            normalized_name = raw_chat.name.strip()
            if not normalized_name:
                normalized_name = None
        
        # Normalize avatar URL
        normalized_avatar = None
        if raw_chat.avatar_url:
            normalized_avatar = raw_chat.avatar_url.strip()
            if not normalized_avatar:
                normalized_avatar = None
        
        # Create DTO
        dto = ChatDTO(
            id=final_id,
            type=chat_type,
            source=raw_chat.source,
            integrity=integrity,
            name=normalized_name,
            avatar=normalized_avatar,
            unread_count=raw_chat.unread_count or 0,
            raw_data=raw_chat.raw_data.copy() if raw_chat.raw_data else {}
        )
        
        return dto
    
    def normalize_with_id(
        self, 
        raw_chat: RawChat, 
        identity_resolver: "IdentityResolver"
    ) -> Optional[ChatDTO]:
        """
        Normalize RawChat to ChatDTO with ID resolution.
        
        Args:
            raw_chat: Raw chat data from source
            identity_resolver: IdentityResolver instance to extract ID
            
        Returns:
            Normalized ChatDTO or None if ID cannot be extracted
        """
        # Extract ID first
        chat_id = identity_resolver.extract_id(raw_chat)
        if not chat_id:
            logger.warning(
                "Cannot normalize chat without ID: name=%s, source=%s",
                raw_chat.name,
                raw_chat.source
            )
            return None
        
        # Normalize with extracted ID
        return self.normalize(raw_chat, chat_id=chat_id)
    
    def normalize_batch(
        self, 
        raw_chats: List[RawChat], 
        identity_resolver: Optional["IdentityResolver"] = None
    ) -> List[ChatDTO]:
        """
        Normalize a batch of raw chats.
        
        Args:
            raw_chats: List of raw chats to normalize
            identity_resolver: Optional IdentityResolver for ID extraction
            
        Returns:
            List of normalized ChatDTOs (chats without IDs are skipped if resolver provided)
        """
        if identity_resolver:
            # Use resolver to extract IDs and skip chats without IDs
            normalized = []
            for raw_chat in raw_chats:
                dto = self.normalize_with_id(raw_chat, identity_resolver)
                if dto:
                    normalized.append(dto)
            return normalized
        else:
            # Normalize without ID extraction (IDs will be set later)
            return [self.normalize(raw_chat) for raw_chat in raw_chats]
    
    def _determine_type(self, raw_chat: RawChat) -> str:
        """
        Determine chat type from raw data.
        
        Priority:
        1. Explicit is_group flag
        2. JID format (@g.us = group, @c.us = personal, @broadcast = broadcast)
        3. wid format (if contains @g.us)
        4. Default to personal
        """
        # Check explicit is_group flag
        if raw_chat.is_group is True:
            return "group"
        elif raw_chat.is_group is False:
            return "personal"
        
        # Check JID format
        jid = raw_chat.jid or ""
        if jid:
            if jid.endswith("@g.us"):
                return "group"
            elif jid.endswith("@c.us"):
                return "personal"
            elif jid.endswith("@broadcast"):
                return "broadcast"
        
        # Check wid format
        wid = raw_chat.wid or ""
        if wid:
            if "@g.us" in wid:
                return "group"
            elif "@c.us" in wid:
                return "personal"
            elif "@broadcast" in wid:
                return "broadcast"
        
        # Default to personal
        return "personal"
    
    def _determine_integrity(self, raw_chat: RawChat) -> str:
        """
        Determine data integrity status.
        
        - verified: Has reliable ID (jid/wid) from Store or Network, complete data
        - fallback: Missing reliable ID or using DOM source
        - ambiguous: Conflicting or unclear data (e.g., different sources give different data)
        """
        # Check if we have a reliable ID
        has_reliable_id = bool(raw_chat.jid or raw_chat.wid)
        has_network_id = bool(raw_chat.server_id or raw_chat.user_id)
        
        # Source-based integrity determination
        if raw_chat.source == "store":
            if has_reliable_id:
                # Store with reliable ID = verified
                return "verified"
            else:
                # Store without ID = fallback (shouldn't happen normally)
                logger.warning("Store source chat without reliable ID: %s", raw_chat.name)
                return "fallback"
        
        elif raw_chat.source == "network":
            if has_reliable_id or has_network_id:
                # Network with ID = verified
                return "verified"
            else:
                # Network without ID = fallback
                return "fallback"
        
        elif raw_chat.source == "dom":
            # DOM source always fallback (by requirement)
            return "fallback"
        
        else:
            # Unknown source = ambiguous
            logger.warning("Unknown source for chat: %s", raw_chat.source)
            return "ambiguous"

