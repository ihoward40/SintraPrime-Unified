"""
Universe Integration Tests Module

Comprehensive test suite for SintraPrime UniVerse integrations.
"""

import unittest

# Test discovery and loading
test_loader = unittest.TestLoader()

__all__ = ["test_discord_integration"]

if __name__ == "__main__":
    # Run all tests
    test_suite = test_loader.discover(".", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)
