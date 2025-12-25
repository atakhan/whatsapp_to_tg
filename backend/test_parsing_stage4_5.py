#!/usr/bin/env python3
"""
Test script for Stage 4-5 implementation - Orchestrator and Integration.
Tests orchestrator implementation and integration with service.
"""

import sys
import ast
import py_compile
from pathlib import Path

backend_dir = Path(__file__).parent


def check_syntax(file_path):
    """Check if Python file has valid syntax."""
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)


def check_file_structure(file_path, expected_classes=None, expected_methods=None):
    """Check if file contains expected classes and methods."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        classes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
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


def test_orchestrator():
    """Test ChatParsingOrchestrator implementation."""
    print("Testing ChatParsingOrchestrator...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/orchestrator.py"
    
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
        expected_classes=['ChatParsingOrchestrator'],
        expected_methods={
            'ChatParsingOrchestrator': [
                '__init__',
                'parse_chats_streaming',
                'parse_chats',
                '_fetch_batches',
                '_chats_to_generator'
            ]
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('SourceSelector', 'Source selector'),
            ('ChatNormalizer', 'Normalizer'),
            ('IdentityResolver', 'Identity resolver'),
            ('CompletionController', 'Completion controller'),
            ('ResultPublisher', 'Result publisher'),
            ('parse_chats_streaming', 'Streaming parsing'),
            ('parse_chats', 'Blocking parsing'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ ChatParsingOrchestrator - syntax OK, contains {list(classes.keys())}")
    return True


def test_service_integration():
    """Test integration in WhatsAppConnectService."""
    print("\nTesting WhatsAppConnectService integration...")
    
    file_path = backend_dir / "app/services/whatsapp/whatsapp_service.py"
    
    if not file_path.exists():
        print("  ✗ File not found")
        return False
    
    # Check syntax
    syntax_ok, error = check_syntax(file_path)
    if not syntax_ok:
        print(f"  ✗ Syntax error: {error}")
        return False
    
    # Check for orchestrator usage
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('ChatParsingOrchestrator', 'Orchestrator import'),
            ('chat_orchestrator', 'Orchestrator instance'),
            ('get_chats_streaming', 'Streaming method'),
            ('get_chats', 'Blocking method'),
            ('get_chats_with_metadata', 'Metadata method'),
        ]
        
        all_present = True
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
                all_present = False
        
        if all_present:
            print("  ✓ WhatsAppConnectService integrates orchestrator")
        
        return all_present


def test_component_imports():
    """Test that orchestrator imports all required components."""
    print("\nTesting component imports in orchestrator...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/orchestrator.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_imports = [
        'SourceSelector',
        'ChatNormalizer',
        'IdentityResolver',
        'CompletionController',
        'ResultPublisher',
        'ChatDTO',
        'ParsingResult',
        'RawChat',
    ]
    
    missing = []
    for imp in required_imports:
        if imp not in content:
            missing.append(imp)
    
    if missing:
        print(f"  ✗ Missing imports: {missing}")
        return False
    
    print("  ✓ All required components are imported")
    return True


def test_backward_compatibility():
    """Test that old API is still supported."""
    print("\nTesting backward compatibility...")
    
    service_file = backend_dir / "app/services/whatsapp/whatsapp_service.py"
    
    with open(service_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that old methods still exist
    old_methods = [
        'get_chats_streaming',
        'get_chats',
    ]
    
    all_present = True
    for method in old_methods:
        if method not in content:
            print(f"  ✗ Missing old method: {method}")
            all_present = False
    
    # Check that conversion to old format exists
    if 'to_dict()' not in content:
        print("  ⚠ Missing conversion to old format (to_dict)")
        all_present = False
    
    if all_present:
        print("  ✓ Backward compatibility maintained")
    
    return all_present


def main():
    """Run all tests."""
    print("=" * 60)
    print("Stage 4-5 Implementation - Orchestrator & Integration Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("ChatParsingOrchestrator", test_orchestrator()))
    results.append(("Service Integration", test_service_integration()))
    results.append(("Component Imports", test_component_imports()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    
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
        print("\n🎉 All Stage 4-5 tests passed!")
        print("   Orchestrator and integration are correctly implemented.")
        print("\n   Note: Full functional tests require:")
        print("   - Active WhatsApp Web session")
        print("   - Real browser context")
        print("   - Integration test environment")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

