import argparse
import subprocess
import os
import sys
import shutil

def get_openmfda_root():
    if "OPENMFDA_ROOT" in os.environ:
        return os.environ["OPENMFDA_ROOT"]
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current))

def run_benchmark(design, comsol_file, platform="standard"):
    root = get_openmfda_root()
    main_script = os.path.join(root, "main.py")
    compare_script = os.path.join(root, "tools", "benchmarking", "compare_comsol.py")
    
    print(f"--- Running Benchmark for {design} ---")
    
    # 1. Run Simulation
    print("Step 1: Running OpenMFDA Simulation...")
    # Using Docker auto-detection from main.py
    cmd = [sys.executable, main_script, "--sim", "--design", design, "--work_dir", f"./benchmarks/{design}"]
    
    # Assuming standard project structure or simple arguments.
    # If the design is in benchmarks/ folder, be careful about paths.
    # Assuming the user runs this from the project root for now
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Simulation failed: {e}")
        return

    # 2. Find Result File
    # Xyce output usually defaults to [design]_xyceOut.csv in the results dir
    # main.py defaults to using 'tools/simulation' logic which puts results in 'results' or 'work_dir'
    
    # Based on runMFDASim.py: csv_out = f"{prn_dir}/{design_name}_xyceOut.csv" where prn_dir is in work_dir
    # We passed work_dir as ./benchmarks/{design}
    
    # Let's grep for the output file
    xyce_out = None
    search_dir = f"./benchmarks/{design}"
    if os.path.exists(search_dir):
        for root_dir, dirs, files in os.walk(search_dir):
            for f in files:
                if f.endswith("_xyceOut.csv"):
                    xyce_out = os.path.join(root_dir, f)
                    break
    
    if not xyce_out:
        print("Error: Could not find Xyce output CSV.")
        return

    print(f"Found Xyce output: {xyce_out}")

    # 3. Run Comparison
    print("Step 2: Comparing with COMSOL Data...")
    cmd_compare = [sys.executable, compare_script, xyce_out, comsol_file]
    
    try:
        subprocess.run(cmd_compare, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Comparison failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OpenMFDA Benchmark Suite")
    parser.add_argument("--design", required=True, help="Design name (must exist)")
    parser.add_argument("--comsol", required=True, help="Path to reference COMSOL CSV")
    
    args = parser.parse_args()
    
    run_benchmark(args.design, args.comsol)
