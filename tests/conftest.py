"""Pytest configuration for for_your_eyes_only tests."""

import os
import sys

# Force headless backend for matplotlib in tests.
os.environ.setdefault("MPLBACKEND", "Agg")

# Add src/ to sys.path so the package is importable from a clean env.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
