import sys
import os
import subprocess
import shutil

def get_openmfda_root():
    if "OPENMFDA_ROOT" in os.environ:
        return os.environ["OPENMFDA_ROOT"]
    # Fallback: assume this file is in tools/
    # This file: tools/runners.py
    # Root: ../
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current)

def run_scad_logic(design, platform, def_file=None, results_dir=None, extra_args=None, use_docker=False):
    """
    Logic directly adapted from run.py run_scad to be reusable.
    extra_args: dict of argument name to value
    use_docker: if True, run inside the openmfda-flow container
    """
    root = get_openmfda_root()
    script_path = os.path.join(root, "tools/scad_render/scad_pnr.py")
    
    if not design or not platform:
        raise ValueError("Design and Platform are required for SCAD generation.")

    if use_docker:
        # Construct docker command
        # docker run --rm -v "root:/home/jovyan/openmfda_flow" openmfda-flow python3 tools/scad_render/scad_pnr.py ...
        cmd = ["docker", "run", "--rm", 
               "-v", f"{root}:/home/jovyan/openmfda_flow",
               "openmfda-flow",
               "python3", "tools/scad_render/scad_pnr.py"]
    else:
        cmd = [sys.executable, script_path]

    cmd.extend(["--design", design])
    cmd.extend(["--platform", platform])
    
    flow_root = os.path.join(root, "flow")
    
    def adjust_path_for_docker(path):
        if not use_docker or not path: return path
        if path.startswith(root):
            rel = os.path.relpath(path, root)
            return f"/home/jovyan/openmfda_flow/{rel}"
        return path # Hope for the best if outside root?

    if def_file:
         cmd.extend(["--def_file", adjust_path_for_docker(def_file)])
    else:
        # Try to guess
        guess = os.path.join(flow_root, "results", design, "base", "2_place.def")
        if os.path.exists(guess):
             # For docker, we pass the Adjusted Guess
             cmd.extend(["--def_file", adjust_path_for_docker(guess)])
        else:
             print(f"Warning: DEF file not found at {guess}, and not provided.")

    if results_dir:
        cmd.extend(["--results_dir", adjust_path_for_docker(results_dir)])
    else:
        out = os.path.join(flow_root, "results", design, "scad")
        cmd.extend(["--results_dir", adjust_path_for_docker(out)])

    if extra_args:
        for k, v in extra_args.items():
            if v is None: continue
            if isinstance(v, list):
                for item in v:
                    cmd.extend([f"--{k}", str(item)])
            elif isinstance(v, bool):
                if v: cmd.append(f"--{k}")
            else:
                if isinstance(v, str) and v.startswith(root):
                    v = adjust_path_for_docker(v)
                cmd.extend([f"--{k}", str(v)])

    print(f"Running SCAD generation (Docker={use_docker}): {' '.join(cmd)}")
    
    # Run with output capture
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("SCAD Generation Failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    
    print("SCAD Generation Success!")
    print(result.stdout)
    
    # Attempt to open the generated SCAD file
    if results_dir:
        out_dir = results_dir
    else:
        out_dir = os.path.join(flow_root, "results", design, "scad")
    
    # Check for .scad files in out_dir
    if os.path.exists(out_dir):
        scad_files = [f for f in os.listdir(out_dir) if f.endswith('.scad')]
        if scad_files:
            latest_file = os.path.join(out_dir, scad_files[0]) # Just pick one
            print(f"Opening generated file: {latest_file}")
            
            # Prefer local OpenSCAD app on macOS
            openscad_app = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
            if sys.platform == 'darwin' and os.path.exists(openscad_app):
                print(f"Using local OpenSCAD app: {openscad_app}")
                subprocess.Popen([openscad_app, latest_file])
            elif sys.platform == 'darwin':
                subprocess.run(['open', latest_file])
            elif sys.platform.startswith('linux'):
                subprocess.run(['xdg-open', latest_file])
            elif sys.platform == 'win32':
                os.startfile(latest_file)
    else:
        print(f"Warning: Results directory {out_dir} not found, cannot open SCAD file.")

def run_sim_logic(design, sim_config=None, verilog_file=None, library_file=None, work_dir=None, plot=False, extra_args=None, use_docker=False):
    """
    Logic adapted from run.py run_sim.
    """
    root = get_openmfda_root()

    if use_docker:
        # Construct docker command
        cmd = ["docker", "run", "--rm", 
               "-v", f"{root}:/home/jovyan/openmfda_flow",
               "openmfda-flow",
               "python3", "main.py", "--sim"]
        
        cmd.extend(["--design", design])
        if sim_config:
            # Adjust path? Simplest is to assume relative or in-root paths
            cmd.extend(["--sim_config", sim_config])
        if verilog_file:
            cmd.extend(["--verilog_file", verilog_file])
        if library_file:
            cmd.extend(["--library_file", library_file])
        if work_dir:
            cmd.extend(["--work_dir", work_dir])
        if plot:
            cmd.append("--plot")
        
        if extra_args:
             for k, v in extra_args.items():
                if v is None: continue
                # Basic arg passing
                cmd.extend([f"--{k}", str(v)])
        
        print(f"Running Simulation in Docker: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("Simulation Failed in Docker!")
            print(result.stdout)
            print(result.stderr)
            raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
        print("Simulation Success!")
        print(result.stdout)
        return

    # We need to add tools/simulation to path to import runMFDASim
    sim_tools_path = os.path.join(root, 'tools', 'simulation')
    if sim_tools_path not in sys.path:
        sys.path.append(sim_tools_path)
        
    try:
        from runMFDASim import runSimulation
    except ImportError:
        # If we are running from a place where runMFDASim isn't in path, this helps
        print(f"Error: Could not import runMFDASim from {sim_tools_path}")
        raise

    print(f"Running Simulation for {design}...")
    
    if not design:
        raise ValueError("Design name is required.")
        
    wd = work_dir or os.getcwd()
    verilog = verilog_file or f"{design}.v"
    
    final_extras = {}
    if plot:
         final_extras['plot'] = True
    if extra_args:
        final_extras.update(extra_args)
        
    runSimulation(
        design=design,
        verilogFile=verilog,
        sim_config=sim_config,
        workDir=wd,
        libraryFile=library_file,
        isLocalXyce=True,
        extra_args=final_extras
    )