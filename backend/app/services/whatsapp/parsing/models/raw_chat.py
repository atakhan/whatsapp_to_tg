"""
Raw chat data structure from various sources.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RawChat:
    """
    Raw chat data extracted from a source (Store, CDP Network, or DOM).
    
    This is the unnormalized representation that will be converted to ChatDTO
    by the normalizer. The structure may vary depending on the source.
    """
    
    # Common fields that should be present in all sources
    source: str  # 'store', 'network', or 'dom'
    
    # Raw data dictionary - structure depends on source
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Optional extracted fields (may be None if not available in source)
    jid: Optional[str] = None  # WhatsApp JID (e.g., "1234567890@c.us")
    wid: Optional[str] = None  # Alternative ID format
    server_id: Optional[str] = None  # From network payloads
    user_id: Optional[str] = None  # From network payloads
    
    name: Optional[str] = None
    is_group: Optional[bool] = None
    unread_count: Optional[int] = None
    avatar_url: Optional[str] = None
    
    # Metadata
    extraction_timestamp: Optional[float] = None
    
    def get_id_candidates(self) -> List[str]:
        """
        Returns all possible ID values in priority order.
        
        Used by IdentityResolver to extract the canonical ID.
        """
        candidates = []
        if self.jid:
            candidates.append(self.jid)
        if self.wid:
            candidates.append(self.wid)
        if self.server_id:
            candidates.append(self.server_id)
        if self.user_id:
            candidates.append(self.user_id)
        return candidates


