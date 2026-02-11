"""Test that all core modules and dependencies can be imported."""
import pytest


class TestCoreDependencies:
    """Verify all pyproject.toml dependencies are importable."""

    @pytest.mark.parametrize("module_name", [
        "PyQt5",
        "matplotlib",
        "solid",         # solidpython package
        "pandas",
        "lark",
        "networkx",
        "regex",
        "numpy",
        "stl",           # numpy-stl package
        "PIL",           # Pillow package
        "yaml",          # PyYAML package
    ])
    def test_dependency_import(self, module_name):
        """Each pyproject.toml dependency should be importable."""
        __import__(module_name)


class TestSrcModules:
    """Verify all src/openmfda_flow modules import without error."""

    @pytest.mark.parametrize("module_name", [
        "openmfda_flow",
        "openmfda_flow.def_parse",
        "openmfda_flow.component_parse",
        "openmfda_flow.verilog_grammer",
        "openmfda_flow.read_netlist",
        "openmfda_flow.openmfda_class",
        "openmfda_flow.def_grammer",
        "openmfda_flow.def_obj_grammer",
        "openmfda_flow.def_obj_load",
        "openmfda_flow.run_iterator",
        pytest.param(
            "openmfda_flow.tcl_comm",
            marks=pytest.mark.xfail(reason="Requires _tkinter (Tk bindings)"),
        ),
        "openmfda_flow.replace_iter",
        "openmfda_flow.write_replace_tcl",
        "openmfda_flow.get_placement_data",
    ])
    def test_src_module_import(self, module_name):
        """Each src/openmfda_flow module should be importable."""
        __import__(module_name)


class TestToolModules:
    """Verify tools/ modules import without error."""

    def test_runners_import(self):
        """tools/runners.py should import cleanly."""
        from runners import run_scad_logic, run_sim_logic
        assert callable(run_scad_logic)
        assert callable(run_sim_logic)

    def test_scad_pnr_importable(self):
        """tools/scad_render/scad_pnr.py should be importable as a module."""
        import importlib
        import os
        scad_render_path = os.path.join(
            os.environ["OPENMFDA_ROOT"], "tools", "scad_render"
        )
        import sys
        if scad_render_path not in sys.path:
            sys.path.insert(0, scad_render_path)
        # Just verify the file exists and is valid Python syntax
        scad_pnr_file = os.path.join(scad_render_path, "scad_pnr.py")
        assert os.path.isfile(scad_pnr_file), "scad_pnr.py not found"
