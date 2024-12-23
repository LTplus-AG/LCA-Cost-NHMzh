import unittest
import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test modules - use relative imports
from tests.test_minio_manager import TestMinioManager
from tests.test_minio_integration import TestMinioIntegration

def run_unittest_suite():
    """Run unittest-based tests"""
    # Create test suite with all unittest-based tests
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    # Add all unittest test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMinioManager))
    suite.addTests(loader.loadTestsFromTestCase(TestMinioIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_pytest_suite():
    """Run pytest-based tests"""
    # Run pytest on the tests directory
    pytest_result = pytest.main([
        str(Path(__file__).parent),  # Run tests in the tests directory
        '-v',  # Verbose output
        '--tb=short',  # Shorter traceback format
        '-p', 'no:warnings'  # Disable warning capture
    ])
    
    return pytest_result == 0  # pytest.ExitCode.OK == 0

def run_tests():
    """Run all tests and return appropriate exit code"""
    # Run both test suites
    unittest_success = run_unittest_suite()
    pytest_success = run_pytest_suite()
    
    # Return 0 if all tests passed, 1 if any failed
    return 0 if (unittest_success and pytest_success) else 1

if __name__ == '__main__':
    sys.exit(run_tests()) 