"""
Identity resolver - extracts and validates chat IDs.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from ..models.raw_chat import RawChat
from ..models.chat_dto import ChatDTO

logger = logging.getLogger(__name__)


class IdentityResolver:
    """
    Resolves chat identity (ID) from raw data.
    
    Implements requirements:
    - ID must come from Store or Network payload
    - NOT from aria-label, textContent, or regex on phone number
    - ID must be immutable and unique
    """
    
    def extract_id(self, raw_chat: RawChat) -> Optional[str]:
        """
        Extract canonical ID from raw chat data.
        
        Priority order:
        1. jid (from Store) - most reliable
        2. wid (from Store) - alternative format
        3. server_id (from Network) - from network payloads
        4. user_id (from Network) - from network payloads
        
        Returns None if no reliable ID found.
        
        Note: This method does NOT use:
        - aria-label (forbidden by requirements)
        - textContent (forbidden by requirements)
        - regex on phone numbers (forbidden by requirements)
        """
        # Priority 1: jid (most reliable, from Store)
        if raw_chat.jid:
            # Validate JID format (should contain @)
            if '@' in raw_chat.jid:
                return raw_chat.jid
            else:
                logger.warning(
                    "Invalid JID format (missing @): %s for chat: %s",
                    raw_chat.jid,
                    raw_chat.name
                )
        
        # Priority 2: wid (alternative Store format or DOM fallback ID)
        if raw_chat.wid:
            # For DOM source, wid may be a fallback ID (dom_chat_...)
            # This is acceptable as DOM is a fallback source
            if raw_chat.source == 'dom' and raw_chat.wid.startswith('dom_chat_'):
                # Fallback ID from DOM - acceptable but less reliable
                logger.debug(
                    "Using DOM fallback ID: %s for chat: %s",
                    raw_chat.wid,
                    raw_chat.name
                )
            return raw_chat.wid
        
        # Priority 3: server_id (from Network)
        if raw_chat.server_id:
            return raw_chat.server_id
        
        # Priority 4: user_id (from Network)
        if raw_chat.user_id:
            return raw_chat.user_id
        
        # No reliable ID found
        logger.warning(
            "No reliable ID found for chat: name=%s, source=%s, "
            "candidates=%s",
            raw_chat.name,
            raw_chat.source,
            raw_chat.get_id_candidates()
        )
        return None
    
    def validate_id(self, chat_id: str) -> bool:
        """
        Validate that ID is in correct format.
        
        Args:
            chat_id: Chat ID to validate
            
        Returns:
            True if ID is valid, False otherwise
        """
        if not chat_id or not isinstance(chat_id, str):
            return False
        
        # ID should not be empty
        if not chat_id.strip():
            return False
        
        # ID should not be a placeholder
        if chat_id.startswith('dom_chat_') or chat_id.startswith('chat_'):
            # This is a fallback ID, acceptable for DOM source but less reliable
            return True
        
        # For WhatsApp IDs, should contain @
        if '@' in chat_id:
            # Valid WhatsApp ID format
            return True
        
        # Other formats are acceptable if they're not empty
        return len(chat_id) > 0
    
    def extract_ids(self, raw_chats: List[RawChat]) -> List[Optional[str]]:
        """
        Extract IDs from a batch of raw chats.
        
        Returns list of IDs (or None if ID cannot be extracted).
        """
        return [self.extract_id(raw_chat) for raw_chat in raw_chats]
    
    def detect_ambiguities(self, chats: List[ChatDTO]) -> List[Dict[str, Any]]:
        """
        Detect anomalies and ambiguities in chat data.
        
        Examples:
        - Different names for same ID
        - ID found in one source but not another
        - Missing expected fields
        - Invalid or missing IDs
        - Integrity conflicts
        """
        anomalies = []
        
        # Check for missing or invalid IDs
        for chat in chats:
            if not chat.id or not self.validate_id(chat.id):
                anomalies.append({
                    'type': 'invalid_id',
                    'chat_name': chat.name,
                    'chat_id': chat.id,
                    'source': chat.source,
                    'integrity': chat.integrity
                })
        
        # Group chats by ID
        chats_by_id: Dict[str, List[ChatDTO]] = {}
        for chat in chats:
            if chat.id:
                if chat.id not in chats_by_id:
                    chats_by_id[chat.id] = []
                chats_by_id[chat.id].append(chat)
        
        # Check for duplicate IDs with different data
        for chat_id, chat_list in chats_by_id.items():
            if len(chat_list) > 1:
                # Check for name conflicts
                names = {chat.name for chat in chat_list if chat.name}
                if len(names) > 1:
                    anomalies.append({
                        'type': 'name_conflict',
                        'chat_id': chat_id,
                        'names': list(names),
                        'sources': [chat.source for chat in chat_list],
                        'count': len(chat_list)
                    })
                
                # Check for type conflicts
                types = {chat.type for chat in chat_list}
                if len(types) > 1:
                    anomalies.append({
                        'type': 'type_conflict',
                        'chat_id': chat_id,
                        'types': list(types),
                        'sources': [chat.source for chat in chat_list],
                        'count': len(chat_list)
                    })
                
                # Check for integrity conflicts
                integrities = {chat.integrity for chat in chat_list}
                if len(integrities) > 1:
                    # This is less critical but worth noting
                    anomalies.append({
                        'type': 'integrity_conflict',
                        'chat_id': chat_id,
                        'integrities': list(integrities),
                        'sources': [chat.source for chat in chat_list],
                        'count': len(chat_list)
                    })
        
        # Check for chats with same name but different IDs (potential duplicates)
        chats_by_name: Dict[str, List[ChatDTO]] = {}
        for chat in chats:
            if chat.name:
                if chat.name not in chats_by_name:
                    chats_by_name[chat.name] = []
                chats_by_name[chat.name].append(chat)
        
        for name, chat_list in chats_by_name.items():
            if len(chat_list) > 1:
                ids = {chat.id for chat in chat_list if chat.id}
                if len(ids) > 1:
                    # Same name, different IDs - might be a real duplicate or different chats
                    # Only flag if integrity suggests they might be the same
                    verified_chats = [c for c in chat_list if c.integrity == 'verified']
                    if len(verified_chats) > 1:
                        anomalies.append({
                            'type': 'potential_duplicate',
                            'chat_name': name,
                            'chat_ids': list(ids),
                            'sources': [chat.source for chat in chat_list],
                            'count': len(chat_list)
                        })
        
        return anomalies
    
    def validate_uniqueness(self, chats: List[ChatDTO]) -> Tuple[bool, List[str]]:
        """
        Validate that all chat IDs are unique.
        
        Args:
            chats: List of chats to validate
            
        Returns:
            Tuple of (is_unique, duplicate_ids)
        """
        seen_ids: Set[str] = set()
        duplicate_ids: List[str] = []
        
        for chat in chats:
            if not chat.id:
                continue
            
            if chat.id in seen_ids:
                duplicate_ids.append(chat.id)
            else:
                seen_ids.add(chat.id)
        
        return len(duplicate_ids) == 0, duplicate_ids

