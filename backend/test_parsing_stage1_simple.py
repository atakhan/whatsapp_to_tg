#!/usr/bin/env python3
"""
Simple test script for Stage 1 implementation.
Tests syntax and basic structure without requiring dependencies.
"""

import ast
import py_compile
import sys
from pathlib import Path


def check_syntax(file_path):
    """Check if Python file has valid syntax."""
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)


def check_ast(file_path):
    """Check if file can be parsed as AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True, None
    except SyntaxError as e:
        return False, str(e)


def check_file_structure(file_path, expected_classes=None):
    """Check if file contains expected classes."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        if expected_classes:
            missing = set(expected_classes) - set(classes)
            if missing:
                return False, f"Missing classes: {missing}"
        
        return True, classes
    except Exception as e:
        return False, str(e)


def test_models_syntax():
    """Test model files syntax."""
    print("Testing models syntax...")
    
    backend_dir = Path(__file__).parent
    models_dir = backend_dir / "app/services/whatsapp/parsing/models"
    
    files = {
        "raw_chat.py": ["RawChat"],
        "chat_dto.py": ["ChatDTO"],
        "parsing_result.py": ["ParsingResult"],
    }
    
    all_passed = True
    for filename, expected_classes in files.items():
        file_path = models_dir / filename
        if not file_path.exists():
            print(f"  ✗ {filename} not found")
            all_passed = False
            continue
        
        # Check syntax
        syntax_ok, error = check_syntax(file_path)
        if not syntax_ok:
            print(f"  ✗ {filename} syntax error: {error}")
            all_passed = False
            continue
        
        # Check AST
        ast_ok, error = check_ast(file_path)
        if not ast_ok:
            print(f"  ✗ {filename} AST error: {error}")
            all_passed = False
            continue
        
        # Check structure
        struct_ok, result = check_file_structure(file_path, expected_classes)
        if not struct_ok:
            print(f"  ✗ {filename} structure error: {result}")
            all_passed = False
            continue
        
        print(f"  ✓ {filename} - syntax OK, contains {result}")
    
    return all_passed


def test_sources_syntax():
    """Test source files syntax."""
    print("\nTesting sources syntax...")
    
    backend_dir = Path(__file__).parent
    sources_dir = backend_dir / "app/services/whatsapp/parsing/sources"
    
    files = {
        "base.py": ["IChatSource", "SourceUnavailableError"],
        "store_chat_source.py": ["StoreChatSource"],
        "cdp_network_chat_source.py": ["CDPNetworkChatSource"],
        "dom_chat_source.py": ["DOMChatSource"],
        "source_selector.py": ["SourceSelector"],
    }
    
    all_passed = True
    for filename, expected_classes in files.items():
        file_path = sources_dir / filename
        if not file_path.exists():
            print(f"  ✗ {filename} not found")
            all_passed = False
            continue
        
        # Check syntax
        syntax_ok, error = check_syntax(file_path)
        if not syntax_ok:
            print(f"  ✗ {filename} syntax error: {error}")
            all_passed = False
            continue
        
        # Check AST
        ast_ok, error = check_ast(file_path)
        if not ast_ok:
            print(f"  ✗ {filename} AST error: {error}")
            all_passed = False
            continue
        
        # Check structure
        struct_ok, result = check_file_structure(file_path, expected_classes)
        if not struct_ok:
            print(f"  ✗ {filename} structure error: {result}")
            all_passed = False
            continue
        
        print(f"  ✓ {filename} - syntax OK, contains {result}")
    
    return all_passed


def test_other_components_syntax():
    """Test other component files syntax."""
    print("\nTesting other components syntax...")
    
    backend_dir = Path(__file__).parent
    parsing_dir = backend_dir / "app/services/whatsapp/parsing"
    
    files = {
        "normalizers/chat_normalizer.py": ["ChatNormalizer"],
        "identity/identity_resolver.py": ["IdentityResolver"],
        "completion/completion_controller.py": ["CompletionController"],
        "publishers/result_publisher.py": ["ResultPublisher"],
    }
    
    all_passed = True
    for rel_path, expected_classes in files.items():
        file_path = parsing_dir / rel_path
        if not file_path.exists():
            print(f"  ✗ {rel_path} not found")
            all_passed = False
            continue
        
        # Check syntax
        syntax_ok, error = check_syntax(file_path)
        if not syntax_ok:
            print(f"  ✗ {rel_path} syntax error: {error}")
            all_passed = False
            continue
        
        # Check AST
        ast_ok, error = check_ast(file_path)
        if not ast_ok:
            print(f"  ✗ {rel_path} AST error: {error}")
            all_passed = False
            continue
        
        # Check structure
        struct_ok, result = check_file_structure(file_path, expected_classes)
        if not struct_ok:
            print(f"  ✗ {rel_path} structure error: {result}")
            all_passed = False
            continue
        
        print(f"  ✓ {rel_path} - syntax OK, contains {result}")
    
    return all_passed


def test_directory_structure():
    """Test that all required directories exist."""
    print("\nTesting directory structure...")
    
    backend_dir = Path(__file__).parent
    parsing_dir = backend_dir / "app/services/whatsapp/parsing"
    
    required_dirs = [
        "models",
        "sources",
        "normalizers",
        "identity",
        "completion",
        "publishers",
    ]
    
    all_passed = True
    for dirname in required_dirs:
        dir_path = parsing_dir / dirname
        if not dir_path.exists():
            print(f"  ✗ {dirname}/ directory not found")
            all_passed = False
        elif not dir_path.is_dir():
            print(f"  ✗ {dirname} is not a directory")
            all_passed = False
        else:
            # Check for __init__.py
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                print(f"  ⚠ {dirname}/__init__.py not found (optional)")
            else:
                print(f"  ✓ {dirname}/ directory exists with __init__.py")
    
    return all_passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("Stage 1 Implementation - Syntax & Structure Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Directory Structure", test_directory_structure()))
    results.append(("Models Syntax", test_models_syntax()))
    results.append(("Sources Syntax", test_sources_syntax()))
    results.append(("Other Components Syntax", test_other_components_syntax()))
    
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
        print("\n🎉 All syntax and structure tests passed!")
        print("   Stage 1 implementation structure is correct.")
        print("\n   Note: Full functional tests require:")
        print("   - Python dependencies (pydantic_settings, playwright)")
        print("   - Proper package imports (not direct file imports)")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


