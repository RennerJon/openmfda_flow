import sys
import os
import subprocess
import shutil
#This file is used to run the SCAD PNR script and the simulation script for the purpose of testing the tools 

def get_openmfda_root():
    if "OPENMFDA_ROOT" in os.environ:
        return os.environ["OPENMFDA_ROOT"]
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current)

def run_scad_logic(design, platform, def_file=None, results_dir=None, extra_args=None, use_docker=False):
    """
    extra_args: dict of argument name to value
    use_docker: if True, run inside the openmfda-flow container
    """
    print("DEBUG: Executing run_scad_logic VERSION 2")
    root = get_openmfda_root()
    script_path = os.path.join(root, "tools/scad_render/scad_pnr.py")
    
    if not design or not platform:
        raise ValueError("Design and Platform are required for SCAD generation.")

    if use_docker:
        cmd = ["docker", "run", "--rm", 
               "-v", f"{root}:/home/jovyan/openmfda_flow",
               "openmfda-flow",
               "openroad", "-python", "tools/scad_render/scad_pnr.py"]
    else:
        cmd = [sys.executable, script_path]

    cmd.extend(["--design", design])
    cmd.extend(["--platform", platform])
    
    flow_root = os.path.join(root, "flow")

    platform_dir = os.path.join(flow_root, "platforms", platform)
    

    

    tlef_path = None
    lef_paths = []
    
    if os.path.exists(platform_dir):
        # Scan for TLEF in the platform directory
        for root_d, dirs, files in os.walk(platform_dir):
            for f in files:
                if f.endswith(".tlef"):
                    if "tech" in f or "merged" not in f: 
                         if not tlef_path: tlef_path = os.path.join(root_d, f)
                if f.endswith(".lef"):
                     if "merged" in f or "p_cell" in f:
                         if f.startswith("p_cell_"): continue
                         lef_paths.append(os.path.join(root_d, f))
    
    if def_file and os.path.exists(def_file):
        def_dir = os.path.dirname(args.def_file) if 'args' in locals() else os.path.dirname(def_file)
        # Checking the following folders for LEF files: def_dir/lef or def_dir/../lef 
        cands = [os.path.join(def_dir, "lef"), os.path.join(os.path.dirname(def_dir), "lef")]
        for d in cands:
             if os.path.exists(d):
                 for root_d, dirs, files in os.walk(d):
                     for f in files:
                         if f.endswith(".lef"):
                            if f.startswith("p_cell_"): continue
                            print(f"DEBUG: Found adjacent LEF: {f}")
                            lef_paths.append(os.path.join(root_d, f))
    
    routing_file = os.path.join(platform_dir, "scad", "routing.scad")
    if not os.path.exists(routing_file): # Fallback to pdk directory
        routing_file = os.path.join(platform_dir, "pdk", "py_scripts", "routing.scad")
        
    component_file = os.path.join(platform_dir, "scad", "components.scad")
    if not os.path.exists(component_file): # Fallback to pdk directory
        component_file = os.path.join(platform_dir, "pdk", "py_scripts", "components.scad")
    
    def adjust_path_for_docker(path):
        if not use_docker or not path: return path
        if path.startswith(root):
            rel = os.path.relpath(path, root)
            return f"/home/jovyan/openmfda_flow/{rel}"
        return path

    if def_file:
         cmd.extend(["--def_file", adjust_path_for_docker(def_file)])
    else:
        guess = os.path.join(flow_root, "results", design, "base", "2_place.def")
        if os.path.exists(guess):
             cmd.extend(["--def_file", adjust_path_for_docker(guess)])
        if os.path.exists(guess):
             cmd.extend(["--def_file", adjust_path_for_docker(guess)])
        else:
             print(f"Warning: DEF file not found at {guess}, and not provided.")
    

    # Parse config.mk for physical parameters and library paths
    config_mk = os.path.join(platform_dir, "config.mk")
    if os.path.exists(config_mk):
        print(f"DEBUG: Parsing config from {config_mk}")
        config_vars = {}
        with open(config_mk, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("export"):
                    parts = line.replace("export", "", 1).split("=")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip()
                        config_vars[key] = val
        
        # Check if config defines component/routing libs
        if "SCAD_COMPONENT_LIBRARY" in config_vars:
            lib = config_vars["SCAD_COMPONENT_LIBRARY"].replace("$(PLATFORM_DIR)", platform_dir).strip()
            if os.path.exists(lib):
                print(f"DEBUG: Using Component Lib from config: {lib}")
                component_file = lib
        
        if "SCAD_ROUTING_LIBRARY" in config_vars:
            lib = config_vars["SCAD_ROUTING_LIBRARY"].replace("$(PLATFORM_DIR)", platform_dir).strip()
            if os.path.exists(lib):
                print(f"DEBUG: Using Routing Lib from config: {lib}")
                routing_file = lib

        # Map variables to arguments
        # Mapping: keys in config_vars -> arg name
        var_map = {
            "PX_VAL": "px",
            "LAYER_VAL": "layer",
            "BOT_LAYER_VAL": "bottom_layer",
            "LPV_VAL": "lpv",
            "XBULK_VAL": "xbulk",
            "YBULK_VAL": "ybulk",
            "ZBULK_VAL": "zbulk",
            "RES_VAL": "res",
            "PITCH": "pitch"
        }
        
        for v_key, arg_name in var_map.items():
            if v_key in config_vars:
                cmd.extend([f"--{arg_name}", config_vars[v_key]])

        # List arguments
        if "XCHIP_VALS" in config_vars:
             vals = config_vars["XCHIP_VALS"].split()
             cmd.append("--xchip")
             cmd.extend(vals)
        if "YCHIP_VALS" in config_vars:
             vals = config_vars["YCHIP_VALS"].split()
             cmd.append("--ychip")
             cmd.extend(vals)

    print(f"DEBUG: Command Constructed: {cmd}")
    
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

    if tlef_path:
        cmd.extend(["--tlef_file", adjust_path_for_docker(tlef_path)])
    if lef_paths:
        for lp in lef_paths:
             cmd.extend(["--lef_file", adjust_path_for_docker(lp)])
             
    # Pass the component/routing files determined earlier (either default or from config)
    if os.path.exists(routing_file):
        cmd.extend(["--routing_file", adjust_path_for_docker(routing_file)])
    if os.path.exists(component_file):
        cmd.extend(["--component_file", adjust_path_for_docker(component_file)])

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
            latest_file = os.path.join(out_dir, scad_files[0]) # Pick the first file
            print(f"Opening generated file: {latest_file}")
            
            # Prefer local OpenSCAD
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

    sim_tools_path = os.path.join(root, 'tools', 'simulation')
    if sim_tools_path not in sys.path:
        sys.path.append(sim_tools_path)
        
    try:
        from runMFDASim import runSimulation
    except ImportError:
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
    # Running of the simulation
    runSimulation(
        design=design,
        verilogFile=verilog,
        sim_config=sim_config,
        workDir=wd,
        libraryFile=library_file,
        isLocalXyce=True,
        extra_args=final_extras
    )