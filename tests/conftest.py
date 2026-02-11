"""Shared pytest fixtures for the OpenMFDA test suite."""
import os
import sys
import pytest


@pytest.fixture(autouse=True)
def openmfda_env():
    """Set OPENMFDA_ROOT and add paths for every test."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ["OPENMFDA_ROOT"] = root
    os.environ["PYTHON_CMD"] = sys.executable

    # Ensure src/ and tools/ are importable
    src_path = os.path.join(root, "src")
    tools_path = os.path.join(root, "tools")
    for p in (src_path, tools_path):
        if p not in sys.path:
            sys.path.insert(0, p)

    yield

    # No teardown needed — env vars persist per-process anyway
