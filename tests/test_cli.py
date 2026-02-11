"""Test the main.py CLI argument parsing."""
import subprocess
import sys
import os
import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable
MAIN_PY = os.path.join(ROOT, "main.py")


class TestCLIParsing:
    """Verify main.py argument parsing works correctly."""

    def test_help_flag(self):
        """--help should print usage and exit 0."""
        result = subprocess.run(
            [PYTHON, MAIN_PY, "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "OpenMFDA Flow Runner" in result.stdout

    def test_scad_flag_recognized(self):
        """--scad should be recognized (not cause argparse error)."""
        result = subprocess.run(
            [PYTHON, MAIN_PY, "--scad", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "--scad" in result.stdout

    def test_sim_flag_recognized(self):
        """--sim should be recognized."""
        result = subprocess.run(
            [PYTHON, MAIN_PY, "--sim", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "--sim" in result.stdout

    def test_design_and_platform_args(self):
        """--design and --platform should appear in help."""
        result = subprocess.run(
            [PYTHON, MAIN_PY, "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert "--design" in result.stdout
        assert "--platform" in result.stdout

    def test_unknown_args_dont_crash(self):
        """Unknown arguments should not cause a crash (parse_known_args)."""
        result = subprocess.run(
            [PYTHON, MAIN_PY, "--scad", "--nonexistent_flag", "value", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        # Should still show help since --help takes priority
        assert result.returncode == 0


class TestProjectStructure:
    """Verify expected project files and directories exist."""

    @pytest.mark.parametrize("path", [
        "main.py",
        "requirements.txt",
        "pyproject.toml",
        "Dockerfile",
        "flow/Makefile",
        "tools/runners.py",
        "tools/gui/app.py",
        "tools/scad_render/scad_pnr.py",
        "src/openmfda_flow/__init__.py",
    ])
    def test_key_file_exists(self, path):
        """Key project files should exist."""
        full_path = os.path.join(ROOT, path)
        assert os.path.isfile(full_path), f"Missing: {path}"

    @pytest.mark.parametrize("path", [
        "flow/platforms/h.r.3.3",
        "flow/platforms/p.m.8.k",
        "flow/platforms/standard",
        "flow/designs",
        "tools/simulation",
        "tools/scad_render",
        "src/openmfda_flow",
    ])
    def test_key_directory_exists(self, path):
        """Key project directories should exist."""
        full_path = os.path.join(ROOT, path)
        assert os.path.isdir(full_path), f"Missing directory: {path}"
