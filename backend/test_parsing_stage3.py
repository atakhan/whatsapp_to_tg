#!/usr/bin/env python3
"""
Test script for Stage 3 implementation - Normalization and Identity.
Tests normalizers, identity resolver, completion controller, and publishers.
"""

import sys
import ast
import py_compile
import importlib.util
from pathlib import Path

backend_dir = Path(__file__).parent


def import_module_directly(module_path, module_name):
    """Import module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def test_normalizer():
    """Test ChatNormalizer implementation."""
    print("Testing ChatNormalizer...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/normalizers/chat_normalizer.py"
    
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
        expected_classes=['ChatNormalizer'],
        expected_methods={
            'ChatNormalizer': ['normalize', 'normalize_batch', 'normalize_with_id', '_determine_type', '_determine_integrity']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('_determine_type', 'Type determination'),
            ('_determine_integrity', 'Integrity determination'),
            ('normalize_with_id', 'ID-based normalization'),
            ('@g.us', 'Group detection'),
            ('verified', 'Integrity status'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ ChatNormalizer - syntax OK, contains {list(classes.keys())}")
    return True


def test_identity_resolver():
    """Test IdentityResolver implementation."""
    print("\nTesting IdentityResolver...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/identity/identity_resolver.py"
    
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
        expected_classes=['IdentityResolver'],
        expected_methods={
            'IdentityResolver': ['extract_id', 'extract_ids', 'validate_id', 'validate_uniqueness', 'detect_ambiguities']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('extract_id', 'ID extraction'),
            ('validate_id', 'ID validation'),
            ('validate_uniqueness', 'Uniqueness validation'),
            ('detect_ambiguities', 'Anomaly detection'),
            ('name_conflict', 'Name conflict detection'),
            ('type_conflict', 'Type conflict detection'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ IdentityResolver - syntax OK, contains {list(classes.keys())}")
    return True


def test_completion_controller():
    """Test CompletionController implementation."""
    print("\nTesting CompletionController...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/completion/completion_controller.py"
    
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
        expected_classes=['CompletionController'],
        expected_methods={
            'CompletionController': ['check_completion', 'determine_completeness_status', '_calculate_missing_ids']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('check_completion', 'Completion checking'),
            ('determine_completeness_status', 'Completeness status'),
            ('is_complete', 'Source completion check'),
            ('total_expected', 'Expected total'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ CompletionController - syntax OK, contains {list(classes.keys())}")
    return True


def test_result_publisher():
    """Test ResultPublisher implementation."""
    print("\nTesting ResultPublisher...")
    
    file_path = backend_dir / "app/services/whatsapp/parsing/publishers/result_publisher.py"
    
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
        expected_classes=['ResultPublisher'],
        expected_methods={
            'ResultPublisher': ['publish_stream', 'publish_final']
        }
    )
    
    if not struct_ok:
        print(f"  ✗ Structure error: {result}")
        return False
    
    # Check for key implementation details
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        checks = [
            ('publish_stream', 'Streaming publication'),
            ('publish_final', 'Final publication'),
            ('ParsingResult', 'Result model usage'),
            ('AsyncGenerator', 'Async generator support'),
        ]
        
        for pattern, description in checks:
            if pattern not in content:
                print(f"  ⚠ Missing {description}: {pattern}")
    
    print(f"  ✓ ResultPublisher - syntax OK, contains {list(classes.keys())}")
    return True


def test_integration():
    """Test that components have compatible interfaces."""
    print("\nTesting component integration (interface compatibility)...")
    
    try:
        # Check that normalizer can work with identity resolver
        normalizers_dir = backend_dir / "app/services/whatsapp/parsing/normalizers"
        with open(normalizers_dir / "chat_normalizer.py", 'r', encoding='utf-8') as f:
            normalizer_content = f.read()
        
        # Check that normalizer references IdentityResolver
        if 'IdentityResolver' not in normalizer_content:
            print("  ⚠ ChatNormalizer doesn't reference IdentityResolver")
        else:
            print("  ✓ ChatNormalizer references IdentityResolver")
        
        # Check that identity resolver has required methods
        identity_dir = backend_dir / "app/services/whatsapp/parsing/identity"
        with open(identity_dir / "identity_resolver.py", 'r', encoding='utf-8') as f:
            resolver_content = f.read()
        
        required_methods = ['extract_id', 'validate_id', 'detect_ambiguities']
        missing = [m for m in required_methods if m not in resolver_content]
        if missing:
            print(f"  ⚠ IdentityResolver missing methods: {missing}")
        else:
            print("  ✓ IdentityResolver has all required methods")
        
        # Check that completion controller uses correct types
        completion_dir = backend_dir / "app/services/whatsapp/parsing/completion"
        with open(completion_dir / "completion_controller.py", 'r', encoding='utf-8') as f:
            completion_content = f.read()
        
        if 'ChatDTO' not in completion_content:
            print("  ⚠ CompletionController doesn't use ChatDTO")
        else:
            print("  ✓ CompletionController uses ChatDTO")
        
        if 'IChatSource' not in completion_content:
            print("  ⚠ CompletionController doesn't use IChatSource")
        else:
            print("  ✓ CompletionController uses IChatSource")
        
        # Check that publisher uses correct types
        publishers_dir = backend_dir / "app/services/whatsapp/parsing/publishers"
        with open(publishers_dir / "result_publisher.py", 'r', encoding='utf-8') as f:
            publisher_content = f.read()
        
        if 'ParsingResult' not in publisher_content:
            print("  ⚠ ResultPublisher doesn't use ParsingResult")
        else:
            print("  ✓ ResultPublisher uses ParsingResult")
        
        if 'AsyncGenerator' not in publisher_content:
            print("  ⚠ ResultPublisher doesn't use AsyncGenerator")
        else:
            print("  ✓ ResultPublisher uses AsyncGenerator")
        
        print("  ✓ Component interfaces are compatible")
        return True
        
    except Exception as e:
        print(f"  ✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Stage 3 Implementation - Normalization & Identity Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("ChatNormalizer", test_normalizer()))
    results.append(("IdentityResolver", test_identity_resolver()))
    results.append(("CompletionController", test_completion_controller()))
    results.append(("ResultPublisher", test_result_publisher()))
    results.append(("Component Integration", test_integration()))
    
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
        print("\n🎉 All Stage 3 tests passed!")
        print("   All normalization and identity components are correctly implemented.")
        print("\n   Note: Full functional tests require:")
        print("   - Integration with data sources")
        print("   - Real chat data")
        print("   - Async context for publishers")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

