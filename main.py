import sys
import os
import argparse
import subprocess

# Set OPENMFDA_ROOT if not set
if "OPENMFDA_ROOT" not in os.environ:
    os.environ["OPENMFDA_ROOT"] = os.path.dirname(os.path.abspath(__file__))

# Ensure make subprocesses use the same python interpreter
os.environ["PYTHON_CMD"] = sys.executable

# Enable Docker for full flow execution
os.environ["OPENMFDA_USE_DOCKER"] = "1"

# Add tools to path
sys.path.append(os.path.join(os.environ["OPENMFDA_ROOT"], 'tools', 'gui'))
sys.path.append(os.path.join(os.environ["OPENMFDA_ROOT"], 'tools', 'simulation'))

def run_gui():
    try:
        from app import OpenMFDAGUI
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("Error: Could not import GUI application. Make sure dependencies are installed.")
        print("Try running: python3 -m pip install -r requirements.txt")
        print("And: python3 -m pip install PyQt5 matplotlib")
        sys.exit(1)
        
    app = QApplication(sys.argv)
    window = OpenMFDAGUI()
    window.show()
    sys.exit(app.exec_())

import shutil

def check_use_docker(tool_name):
    """
    Checks if a tool is available locally. If not, returns True (use Docker).
    """
    if shutil.which(tool_name):
        return False
    print(f"[{tool_name}] not found locally. Switching to Docker execution...")
    return True

def run_scad(args):
    try:
        from tools.runners import run_scad_logic
    except ImportError:
        # Fallback if PYTHONPATH isn't set perfectly
        sys.path.append(os.path.join(os.environ["OPENMFDA_ROOT"], 'tools'))
        from runners import run_scad_logic

    # Extract extra args
    known_scad_args = [
        "routing_file", "component_file", "tlef_file", "px", "layer", 
        "bottom_layer", "lpv", "xbulk", "ybulk", "zbulk", "pitch", "res",
        "lef_file", "xchip", "ychip", "stl"
    ]
    extras = {}
    if args.profile:
        extras['profile'] = args.profile
    for k in known_scad_args:
        val = getattr(args, k, None)
        if val is not None:
            extras[k] = val

    use_docker = check_use_docker('openscad')

    try:
        run_scad_logic(
            design=args.design,
            platform=args.platform,
            def_file=args.def_file,
            results_dir=args.results_dir,
            extra_args=extras,
            use_docker=use_docker
        )
    except Exception as e:
        print(f"SCAD Generation Error: {e}")
        sys.exit(1)

def run_sim(args):
    try:
        from tools.runners import run_sim_logic
    except ImportError:
         sys.path.append(os.path.join(os.environ["OPENMFDA_ROOT"], 'tools'))
         from runners import run_sim_logic

    use_docker = check_use_docker('Xyce')

    try:
        run_sim_logic(
            design=args.design,
            sim_config=args.sim_config,
            verilog_file=args.verilog_file,
            library_file=args.library_file,
            work_dir=args.work_dir,
            plot=args.plot,
            use_docker=use_docker
        )
    except Exception as e:
        print(f"Simulation Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="OpenMFDA Flow Runner")
    
    # Mode selection
    parser.add_argument('--gui', action='store_true', help="Run the GUI (default)")
    parser.add_argument('--scad', action='store_true', help="Run OpenSCAD model generation")
    parser.add_argument('--stl', action='store_true', help="Generate STL from SCAD model")
    parser.add_argument('--sim', '--simulate', dest='sim', action='store_true', help="Run Xyce simulation")
    
    # Shared Args
    parser.add_argument('--design', type=str, help="Design name")
    parser.add_argument('--platform', type=str, help="Platform name (for SCAD)")
    parser.add_argument('--profile', type=str, help="3D Printer Profile (e.g. bambu_x1c, neptune4_plus)")
    
    # Sim Args
    parser.add_argument('--verilog_file', type=str, help="Verilog file for simulation")
    parser.add_argument('--sim_config', type=str, help="Simulation configuration file")
    parser.add_argument('--library_file', type=str, help="Library file for simulation")
    parser.add_argument('--work_dir', type=str, help="Working directory")
    parser.add_argument('--plot', action='store_true', help="Plot simulation results")

    # SCAD Args
    parser.add_argument('--def_file', type=str, help="DEF file path")
    parser.add_argument('--lef_file', type=str, nargs='+', help="LEF file path(s)")
    parser.add_argument('--routing_file', type=str, help="Routing SCAD definitions")
    parser.add_argument('--component_file', type=str, help="Component SCAD definitions")
    parser.add_argument('--tlef_file', type=str, help="TLEF file path")
    parser.add_argument('--results_dir', type=str, help="Results directory")
    parser.add_argument('--px', type=float, help="Pixel size")
    parser.add_argument('--layer', type=float, help="Layer size")
    parser.add_argument('--bottom_layer', type=int, help="Bottom layer index")
    parser.add_argument('--lpv', type=int, help="Layers per via")
    parser.add_argument('--xbulk', type=int, help="Bulk X")
    parser.add_argument('--ybulk', type=int, help="Bulk Y")
    parser.add_argument('--zbulk', type=int, help="Bulk Z")
    parser.add_argument('--pitch', type=int, help="Pitch")
    parser.add_argument('--res', type=int, help="Resolution")
    parser.add_argument('--xchip', type=int, nargs='+', help="X Chip bounds")
    parser.add_argument('--ychip', type=int, nargs='+', help="Y Chip bounds")


    args, unknown = parser.parse_known_args()

    # Default to GUI if no specific mode and no conflicting args
    if not args.scad and not args.sim and not args.stl:
        run_gui()
    elif args.scad or args.stl:
        # Implicitly run SCAD generation if STL is requested
        run_scad(args)
    elif args.sim:
        run_sim(args)

if __name__ == "__main__":
    main()
