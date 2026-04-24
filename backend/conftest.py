# conftest.py — ensures backend/ root is on sys.path for all tests.
# This allows `from lib.utils import ...` and `from main import app` to work.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
