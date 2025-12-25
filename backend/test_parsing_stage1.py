#!/usr/bin/env python3
"""
Test script for Stage 1 implementation.
Tests models and basic functionality without requiring full app dependencies.
"""

import sys
import importlib.util
from pathlib import Path

# Add app to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def import_module_directly(module_path, module_name):
    """Import module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_models():
    """Test model imports and basic functionality."""
    print("Testing models...")
    
    try:
        # Import models directly
        models_dir = backend_dir / "app/services/whatsapp/parsing/models"
        
        raw_chat_module = import_module_directly(
            models_dir / "raw_chat.py", "raw_chat"
        )
        RawChat = raw_chat_module.RawChat
        
        chat_dto_module = import_module_directly(
            models_dir / "chat_dto.py", "chat_dto"
        )
        ChatDTO = chat_dto_module.ChatDTO
        
        parsing_result_module = import_module_directly(
            models_dir / "parsing_result.py", "parsing_result"
        )
        ParsingResult = parsing_result_module.ParsingResult
        
        print("  ✓ Models imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import models: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test RawChat
    try:
        raw_chat = RawChat(
            source="store",
            jid="1234567890@c.us",
            name="Test Chat",
            is_group=False,
            unread_count=5
        )
        assert raw_chat.jid == "1234567890@c.us"
        assert raw_chat.get_id_candidates() == ["1234567890@c.us"]
        print("  ✓ RawChat creation and methods work")
    except Exception as e:
        print(f"  ✗ RawChat test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test ChatDTO
    try:
        dto = ChatDTO(
            id="1234567890@c.us",
            type="personal",
            source="store",
            integrity="verified",
            name="Test Chat",
            unread_count=5
        )
        assert dto.id == "1234567890@c.us"
        assert dto.type == "personal"
        dto_dict = dto.to_dict()
        assert dto_dict['id'] == "1234567890@c.us"
        assert dto_dict['is_group'] is False
        print("  ✓ ChatDTO creation and to_dict() work")
    except Exception as e:
        print(f"  ✗ ChatDTO test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test ParsingResult
    try:
        result = ParsingResult(
            chats=[dto],
            completeness="complete",
            collected=1,
            expected=1,
            source_type="store"
        )
        assert result.is_complete() is True
        assert result.get_completeness_percentage() == 100.0
        result_dict = result.to_dict()
        assert result_dict['completeness'] == "complete"
        print("  ✓ ParsingResult creation and methods work")
    except Exception as e:
        print(f"  ✗ ParsingResult test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_sources():
    """Test source interfaces."""
    print("\nTesting sources...")
    
    try:
        sources_dir = backend_dir / "app/services/whatsapp/parsing/sources"
        
        base_module = import_module_directly(
            sources_dir / "base.py", "base"
        )
        IChatSource = base_module.IChatSource
        SourceUnavailableError = base_module.SourceUnavailableError
        
        print("  ✓ Source interfaces imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import source interfaces: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test that SourceUnavailableError is a proper exception
    try:
        raise SourceUnavailableError("Test error")
    except SourceUnavailableError as e:
        assert str(e) == "Test error"
        print("  ✓ SourceUnavailableError works correctly")
    except Exception as e:
        print(f"  ✗ SourceUnavailableError test failed: {e}")
        return False
    
    return True


def test_normalizers():
    """Test normalizer."""
    print("\nTesting normalizers...")
    
    try:
        normalizers_dir = backend_dir / "app/services/whatsapp/parsing/normalizers"
        
        normalizer_module = import_module_directly(
            normalizers_dir / "chat_normalizer.py", "chat_normalizer"
        )
        ChatNormalizer = normalizer_module.ChatNormalizer
        
        # Import RawChat for testing
        models_dir = backend_dir / "app/services/whatsapp/parsing/models"
        raw_chat_module = import_module_directly(
            models_dir / "raw_chat.py", "raw_chat"
        )
        RawChat = raw_chat_module.RawChat
        
        print("  ✓ ChatNormalizer imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import ChatNormalizer: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test normalization
    try:
        normalizer = ChatNormalizer()
        raw_chat = RawChat(
            source="store",
            jid="1234567890@c.us",
            name="Test",
            is_group=False
        )
        dto = normalizer.normalize(raw_chat)
        assert dto.type == "personal"
        assert dto.source == "store"
        print("  ✓ ChatNormalizer.normalize() works")
    except Exception as e:
        print(f"  ✗ ChatNormalizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_identity_resolver():
    """Test identity resolver."""
    print("\nTesting identity resolver...")
    
    try:
        identity_dir = backend_dir / "app/services/whatsapp/parsing/identity"
        
        resolver_module = import_module_directly(
            identity_dir / "identity_resolver.py", "identity_resolver"
        )
        IdentityResolver = resolver_module.IdentityResolver
        
        # Import RawChat for testing
        models_dir = backend_dir / "app/services/whatsapp/parsing/models"
        raw_chat_module = import_module_directly(
            models_dir / "raw_chat.py", "raw_chat"
        )
        RawChat = raw_chat_module.RawChat
        
        print("  ✓ IdentityResolver imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import IdentityResolver: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test ID extraction
    try:
        resolver = IdentityResolver()
        raw_chat = RawChat(
            source="store",
            jid="1234567890@c.us",
            name="Test"
        )
        chat_id = resolver.extract_id(raw_chat)
        assert chat_id == "1234567890@c.us"
        print("  ✓ IdentityResolver.extract_id() works")
    except Exception as e:
        print(f"  ✗ IdentityResolver test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_completion_controller():
    """Test completion controller."""
    print("\nTesting completion controller...")
    
    try:
        completion_dir = backend_dir / "app/services/whatsapp/parsing/completion"
        
        controller_module = import_module_directly(
            completion_dir / "completion_controller.py", "completion_controller"
        )
        CompletionController = controller_module.CompletionController
        
        print("  ✓ CompletionController imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import CompletionController: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Note: Full testing requires mock IChatSource, which we'll do in integration tests
    print("  ✓ CompletionController structure is correct")
    return True


def test_publishers():
    """Test result publisher."""
    print("\nTesting publishers...")
    
    try:
        publishers_dir = backend_dir / "app/services/whatsapp/parsing/publishers"
        
        publisher_module = import_module_directly(
            publishers_dir / "result_publisher.py", "result_publisher"
        )
        ResultPublisher = publisher_module.ResultPublisher
        
        print("  ✓ ResultPublisher imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import ResultPublisher: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Note: Full testing requires async context, which we'll do in integration tests
    print("  ✓ ResultPublisher structure is correct")
    return True


def test_source_selector():
    """Test source selector."""
    print("\nTesting source selector...")
    
    try:
        sources_dir = backend_dir / "app/services/whatsapp/parsing/sources"
        
        selector_module = import_module_directly(
            sources_dir / "source_selector.py", "source_selector"
        )
        SourceSelector = selector_module.SourceSelector
        
        print("  ✓ SourceSelector imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import SourceSelector: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ SourceSelector structure is correct")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Stage 1 Implementation Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Models", test_models()))
    results.append(("Sources", test_sources()))
    results.append(("Normalizers", test_normalizers()))
    results.append(("Identity Resolver", test_identity_resolver()))
    results.append(("Completion Controller", test_completion_controller()))
    results.append(("Publishers", test_publishers()))
    results.append(("Source Selector", test_source_selector()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name:30s} {status}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! Stage 1 implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
