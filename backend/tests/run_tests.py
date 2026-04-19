import sys
import unittest
from pathlib import Path


# Runs every backend test in this folder with verbose output
def main():
    tests_dir = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(tests_dir), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
