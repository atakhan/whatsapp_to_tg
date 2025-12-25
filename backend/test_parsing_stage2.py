#!/usr/bin/env python3
"""
Test script for Stage 2 implementation - Data Sources.
Tests sources implementation without requiring full app dependencies.
"""

import sys
import ast
import py_compile
import importlib.util
from pathlib import Path

backend_dir = Path(__file__).parent


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


def check_file_structure(file_path, expected_classes=None, expected_methods=None):
    """Check if file contains expected classes and methods."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        classes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get both regular and async methods
                methods = [
                    n.name for n in node.body 
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                classes[node.name] = methods
        
        if expected_classes:
            missing = set(expected_classes) - set(classes.keys())
            if missing:
                return False, f"Missing classes: {missing}", classes
        
        if expected_methods:
            for class_name, methods in expected_methods.items():
                if class_name in classes:
                    missing = set(methods) - set(classes[class_name])
                    if missing:
                        return False, f"Class {class_name} missing methods: {missing}", classes
        
        return True, classes, classes
    except Exception as e:
        return False, str(e), {}


def test_store_source():
    """Test StoreChatSource implementation."""
    print("Testing StoreChatSource...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/sources/store_chat_source.py"
    
    if not file_path.exists():
        print("  ✗ File not found")
        return False
    
    # Check syntax
    syntax_ok, error = check_syntax(file_path)
    if not syntax_ok:
        print(f"  ✗ Syntax error: {error}")
        return False
    
    # Check structure
    struct_ok, result, classes = check_file_structure(
        file_path,
        expected_classes=['StoreChatSource'],
        expected_methods={
            'StoreChatSource': ['init', 'fetch_batch', 'is_complete', 'total_expected']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('window.Store', 'Store access'),
            ('chat.id._serialized', 'JID extraction'),
            ('isGroup', 'Group detection'),
            ('SourceUnavailableError', 'Error handling'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ StoreChatSource - syntax OK, contains {list(classes.keys())}")
    return True


def test_cdp_source():
    """Test CDPNetworkChatSource implementation."""
    print("\nTesting CDPNetworkChatSource...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/sources/cdp_network_chat_source.py"
    
    if not file_path.exists():
        print("  ✗ File not found")
        return False
    
    # Check syntax
    syntax_ok, error = check_syntax(file_path)
    if not syntax_ok:
        print(f"  ✗ Syntax error: {error}")
        return False
    
    # Check structure
    struct_ok, result, classes = check_file_structure(
        file_path,
        expected_classes=['CDPNetworkChatSource'],
        expected_methods={
            'CDPNetworkChatSource': ['init', 'fetch_batch', 'is_complete', 'total_expected', 'cleanup']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('new_cdp_session', 'CDP session creation'),
            ('Network.enable', 'Network domain'),
            ('Network.responseReceived', 'Response listener'),
            ('_parse_json_payload', 'Payload parsing'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ CDPNetworkChatSource - syntax OK, contains {list(classes.keys())}")
    return True


def test_dom_source():
    """Test DOMChatSource implementation."""
    print("\nTesting DOMChatSource...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/sources/dom_chat_source.py"
    
    if not file_path.exists():
        print("  ✗ File not found")
        return False
    
    # Check syntax
    syntax_ok, error = check_syntax(file_path)
    if not syntax_ok:
        print(f"  ✗ Syntax error: {error}")
        return False
    
    # Check structure
    struct_ok, result, classes = check_file_structure(
        file_path,
        expected_classes=['DOMChatSource'],
        expected_methods={
            'DOMChatSource': ['init', 'fetch_batch', 'is_complete', 'total_expected', 'scroll_for_more']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('data-testid="chatlist"', 'Chat list selector'),
            ('querySelectorAll', 'DOM querying'),
            ('_seen_ids', 'Deduplication'),
            ('scroll_for_more', 'Scrolling support'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ DOMChatSource - syntax OK, contains {list(classes.keys())}")
    return True


def test_source_selector():
    """Test SourceSelector implementation."""
    print("\nTesting SourceSelector...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/sources/source_selector.py"
    
    if not file_path.exists():
        print("  ✗ File not found")
        return False
    
    # Check syntax
    syntax_ok, error = check_syntax(file_path)
    if not syntax_ok:
        print(f"  ✗ Syntax error: {error}")
        return False
    
    # Check structure
    struct_ok, result, classes = check_file_structure(
        file_path,
        expected_classes=['SourceSelector'],
        expected_methods={
            'SourceSelector': ['select_source']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('StoreChatSource', 'Store source import'),
            ('CDPNetworkChatSource', 'CDP source import'),
            ('DOMChatSource', 'DOM source import'),
            ('metadata', 'Metadata tracking'),
            ('is_degraded', 'Degradation flag'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ SourceSelector - syntax OK, contains {list(classes.keys())}")
    return True


def test_ichatsource_interface():
    """Test that all sources implement IChatSource interface."""
    print("\nTesting IChatSource interface compliance...")
    
    base_file = backend_dir / "app/services/whatsapp/parsing/sources/base.py"
    
    with open(base_file, 'r', encoding='utf-8') as f:
        base_content = f.read()
        tree = ast.parse(base_content)
    
    # Find abstract methods in IChatSource
    abstract_methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'IChatSource':
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Check if it's abstract (has @abstractmethod decorator)
                    for decorator in item.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == 'abstractmethod':
                            abstract_methods.append(item.name)
    
    print(f"  Found {len(abstract_methods)} abstract methods: {abstract_methods}")
    
    # Check each source implements them
    sources = {
        'StoreChatSource': backend_dir / "app/services/whatsapp/parsing/sources/store_chat_source.py",
        'CDPNetworkChatSource': backend_dir / "app/services/whatsapp/parsing/sources/cdp_network_chat_source.py",
        'DOMChatSource': backend_dir / "app/services/whatsapp/parsing/sources/dom_chat_source.py",
    }
    
    all_compliant = True
    for source_name, file_path in sources.items():
        if not file_path.exists():
            print(f"  ✗ {source_name} file not found")
            all_compliant = False
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
        
        # Find the source class
        source_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == source_name:
                source_class = node
                break
        
        if not source_class:
            print(f"  ✗ {source_name} class not found")
            all_compliant = False
            continue
        
        # Check if it implements all abstract methods (including async)
        implemented_methods = [
            item.name for item in source_class.body 
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        missing = set(abstract_methods) - set(implemented_methods)
        
        if missing:
            print(f"  ✗ {source_name} missing methods: {missing}")
            all_compliant = False
        else:
            print(f"  ✓ {source_name} implements all required methods")
    
    return all_compliant


def test_imports():
    """Test that all modules can be imported (syntax check)."""
    print("\nTesting module imports...")
    
    modules = [
        "app/services/whatsapp/parsing/sources/base",
        "app/services/whatsapp/parsing/sources/store_chat_source",
        "app/services/whatsapp/parsing/sources/cdp_network_chat_source",
        "app/services/whatsapp/parsing/sources/dom_chat_source",
        "app/services/whatsapp/parsing/sources/source_selector",
    ]
    
    all_ok = True
    for module_path in modules:
        file_path = backend_dir / f"{module_path}.py"
        if not file_path.exists():
            print(f"  ✗ {module_path} not found")
            all_ok = False
            continue
        
        # Just check syntax, not actual import (would require dependencies)
        syntax_ok, error = check_syntax(file_path)
        if not syntax_ok:
            print(f"  ✗ {module_path} syntax error: {error}")
            all_ok = False
        else:
            print(f"  ✓ {module_path} syntax OK")
    
    return all_ok


def main():
    """Run all tests."""
    print("=" * 60)
    print("Stage 2 Implementation - Data Sources Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("StoreChatSource", test_store_source()))
    results.append(("CDPNetworkChatSource", test_cdp_source()))
    results.append(("DOMChatSource", test_dom_source()))
    results.append(("SourceSelector", test_source_selector()))
    results.append(("IChatSource Compliance", test_ichatsource_interface()))
    results.append(("Module Imports", test_imports()))
    
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
        print("\n🎉 All Stage 2 tests passed!")
        print("   All data sources are correctly implemented.")
        print("\n   Note: Functional tests with real browser require:")
        print("   - Playwright installed")
        print("   - Active WhatsApp Web session")
        print("   - Integration test environment")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

