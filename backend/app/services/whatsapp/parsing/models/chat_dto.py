"""
Normalized chat data transfer object.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional


@dataclass
class ChatDTO:
    """
    Normalized chat data transfer object.
    
    This is the final, unified representation of a chat that is used
    throughout the system after normalization.
    """
    
    # Required fields
    id: str  # Canonical chat ID (from IdentityResolver)
    type: Literal["personal", "group", "broadcast"]
    source: Literal["store", "network", "dom"]
    integrity: Literal["verified", "fallback", "ambiguous"]
    
    # Optional fields
    name: Optional[str] = None
    avatar: Optional[str] = None
    unread_count: int = 0
    
    # Metadata for diagnostics
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format (for API responses)."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'avatar': self.avatar,
            'message_count': self.unread_count,
            'is_group': self.type == 'group',
            'source': self.source,
            'integrity': self.integrity,
        }
    
    def __eq__(self, other: object) -> bool:
        """Equality based on ID only."""
        if not isinstance(other, ChatDTO):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID only."""
        return hash(self.id)


