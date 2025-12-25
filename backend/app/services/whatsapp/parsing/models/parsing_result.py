"""
Parsing result with completeness information.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from .chat_dto import ChatDTO


@dataclass
class ParsingResult:
    """
    Result of chat parsing with completeness and metadata.
    
    This object is returned by the orchestrator and contains:
    - The list of parsed chats
    - Completeness status (complete/partial)
    - Expected vs collected counts
    - Missing IDs (if partial)
    - Source information
    - Anomalies detected
    """
    
    # Chat data
    chats: List[ChatDTO] = field(default_factory=list)
    
    # Completeness information
    completeness: Literal["complete", "partial"] = "partial"
    collected: int = 0
    expected: Optional[int] = None
    missing_ids: List[str] = field(default_factory=list)
    
    # Source information
    source_type: str = "unknown"  # 'store', 'network', 'dom'
    source_degraded: bool = False  # True if fallback was used
    
    # Anomalies detected during parsing
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate collected count from chats list."""
        if self.collected == 0 and self.chats:
            self.collected = len(self.chats)
    
    def is_complete(self) -> bool:
        """Check if parsing is complete."""
        if self.completeness == "complete":
            return True
        
        if self.expected is not None:
            return self.collected >= self.expected
        
        return False
    
    def get_completeness_percentage(self) -> Optional[float]:
        """Get completeness as percentage (0-100)."""
        if self.expected is None or self.expected == 0:
            return None
        return (self.collected / self.expected) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format (for API responses)."""
        return {
            'chats': [chat.to_dict() for chat in self.chats],
            'completeness': self.completeness,
            'collected': self.collected,
            'expected': self.expected,
            'missing_ids': self.missing_ids,
            'source_type': self.source_type,
            'source_degraded': self.source_degraded,
            'anomalies': self.anomalies,
            'metadata': self.metadata,
            'completeness_percentage': self.get_completeness_percentage(),
        }


