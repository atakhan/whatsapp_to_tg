"""
Unit tests for parsing models.
"""

import pytest
from app.services.whatsapp.parsing.models.chat_dto import ChatDTO
from app.services.whatsapp.parsing.models.parsing_result import ParsingResult
from app.services.whatsapp.parsing.models.raw_chat import RawChat


class TestRawChat:
    """Tests for RawChat model."""
    
    def test_create_raw_chat(self):
        """Test creating a RawChat with minimal data."""
        raw_chat = RawChat(source="store")
        assert raw_chat.source == "store"
        assert raw_chat.jid is None
        assert raw_chat.name is None
    
    def test_create_raw_chat_with_data(self):
        """Test creating a RawChat with full data."""
        raw_chat = RawChat(
            source="store",
            jid="1234567890@c.us",
            name="Test Chat",
            is_group=False,
            unread_count=5,
            avatar_url="https://example.com/avatar.jpg"
        )
        assert raw_chat.jid == "1234567890@c.us"
        assert raw_chat.name == "Test Chat"
        assert raw_chat.is_group is False
        assert raw_chat.unread_count == 5
    
    def test_get_id_candidates(self):
        """Test getting ID candidates in priority order."""
        raw_chat = RawChat(
            source="store",
            jid="123@c.us",
            wid="456",
            server_id="789",
            user_id="012"
        )
        candidates = raw_chat.get_id_candidates()
        assert candidates == ["123@c.us", "456", "789", "012"]
    
    def test_get_id_candidates_empty(self):
        """Test getting ID candidates when none exist."""
        raw_chat = RawChat(source="dom")
        candidates = raw_chat.get_id_candidates()
        assert candidates == []


class TestChatDTO:
    """Tests for ChatDTO model."""
    
    def test_create_chat_dto(self):
        """Test creating a ChatDTO."""
        dto = ChatDTO(
            id="1234567890@c.us",
            type="personal",
            source="store",
            integrity="verified"
        )
        assert dto.id == "1234567890@c.us"
        assert dto.type == "personal"
        assert dto.source == "store"
        assert dto.integrity == "verified"
    
    def test_create_chat_dto_with_optional_fields(self):
        """Test creating a ChatDTO with optional fields."""
        dto = ChatDTO(
            id="1234567890@c.us",
            type="group",
            source="store",
            integrity="verified",
            name="Test Group",
            avatar="https://example.com/avatar.jpg",
            unread_count=10
        )
        assert dto.name == "Test Group"
        assert dto.avatar == "https://example.com/avatar.jpg"
        assert dto.unread_count == 10
    
    def test_to_dict(self):
        """Test converting ChatDTO to dictionary."""
        dto = ChatDTO(
            id="1234567890@c.us",
            type="group",
            source="store",
            integrity="verified",
            name="Test Group",
            unread_count=5
        )
        result = dto.to_dict()
        assert result['id'] == "1234567890@c.us"
        assert result['name'] == "Test Group"
        assert result['type'] == "group"
        assert result['is_group'] is True
        assert result['message_count'] == 5
        assert result['source'] == "store"
        assert result['integrity'] == "verified"
    
    def test_equality(self):
        """Test ChatDTO equality based on ID."""
        dto1 = ChatDTO(
            id="123@c.us",
            type="personal",
            source="store",
            integrity="verified"
        )
        dto2 = ChatDTO(
            id="123@c.us",
            type="group",  # Different type
            source="dom",  # Different source
            integrity="fallback"  # Different integrity
        )
        assert dto1 == dto2  # Same ID means equal
    
    def test_hash(self):
        """Test ChatDTO hashing based on ID."""
        dto1 = ChatDTO(
            id="123@c.us",
            type="personal",
            source="store",
            integrity="verified"
        )
        dto2 = ChatDTO(
            id="123@c.us",
            type="group",
            source="dom",
            integrity="fallback"
        )
        assert hash(dto1) == hash(dto2)  # Same ID means same hash


class TestParsingResult:
    """Tests for ParsingResult model."""
    
    def test_create_parsing_result(self):
        """Test creating a ParsingResult."""
        result = ParsingResult()
        assert result.chats == []
        assert result.completeness == "partial"
        assert result.collected == 0
        assert result.expected is None
    
    def test_create_parsing_result_with_chats(self):
        """Test creating a ParsingResult with chats."""
        chats = [
            ChatDTO(id="1@c.us", type="personal", source="store", integrity="verified"),
            ChatDTO(id="2@c.us", type="personal", source="store", integrity="verified"),
        ]
        result = ParsingResult(chats=chats)
        assert len(result.chats) == 2
        assert result.collected == 2  # Auto-calculated in __post_init__
    
    def test_is_complete(self):
        """Test checking if parsing is complete."""
        result = ParsingResult(completeness="complete")
        assert result.is_complete() is True
        
        result = ParsingResult(completeness="partial")
        assert result.is_complete() is False
    
    def test_is_complete_with_expected(self):
        """Test completeness check with expected count."""
        chats = [
            ChatDTO(id="1@c.us", type="personal", source="store", integrity="verified"),
            ChatDTO(id="2@c.us", type="personal", source="store", integrity="verified"),
        ]
        result = ParsingResult(
            chats=chats,
            completeness="partial",
            expected=2,
            collected=2
        )
        # Should be complete if collected >= expected
        assert result.is_complete() is True
    
    def test_get_completeness_percentage(self):
        """Test calculating completeness percentage."""
        chats = [
            ChatDTO(id="1@c.us", type="personal", source="store", integrity="verified"),
        ]
        result = ParsingResult(
            chats=chats,
            expected=2,
            collected=1
        )
        percentage = result.get_completeness_percentage()
        assert percentage == 50.0
    
    def test_get_completeness_percentage_none(self):
        """Test completeness percentage when expected is None."""
        result = ParsingResult(expected=None)
        percentage = result.get_completeness_percentage()
        assert percentage is None
    
    def test_to_dict(self):
        """Test converting ParsingResult to dictionary."""
        chats = [
            ChatDTO(id="1@c.us", type="personal", source="store", integrity="verified"),
        ]
        result = ParsingResult(
            chats=chats,
            completeness="partial",
            expected=2,
            collected=1,
            source_type="store",
            source_degraded=False,
            missing_ids=["2@c.us"]
        )
        result_dict = result.to_dict()
        assert result_dict['completeness'] == "partial"
        assert result_dict['collected'] == 1
        assert result_dict['expected'] == 2
        assert result_dict['missing_ids'] == ["2@c.us"]
        assert result_dict['source_type'] == "store"
        assert result_dict['source_degraded'] is False
        assert len(result_dict['chats']) == 1
        assert result_dict['completeness_percentage'] == 50.0


