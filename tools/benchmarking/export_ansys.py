import argparse
import os
import sys
import subprocess
import shutil

def get_openmfda_root():
    if "OPENMFDA_ROOT" in os.environ:
        return os.environ["OPENMFDA_ROOT"]
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current))

def run_scad_export(design, platform, export_type):
    root = get_openmfda_root()
    scad_pnr_script = os.path.join(root, "tools", "scad_render", "scad_pnr.py")
    results_dir = os.path.join(root, "flow", "results", design, "base")
    def_file = os.path.join(results_dir, "4_final.def")
    
    if not os.path.exists(def_file):
        print(f"Error: DEF file not found: {def_file}")
        print("Please run the PNR flow first.")
        return False

    # Platform paths
    platform_dir = os.path.join(root, "flow", "platforms", platform)
    tech_lef = os.path.join(platform_dir, "lef", f"{platform}.tlef")
    merged_lef = os.path.join(results_dir, "merged.lef")
    lef_args = []
    if os.path.exists(merged_lef):
        lef_args = ["--lef_file", merged_lef]
    else:
        std_lef = os.path.join(platform_dir, "lef", f"{platform}.lef")
        lef_args = ["--lef_file", std_lef]

    # SCAD config/routing files
    scad_dir = os.path.join(root, "tools", "scad_render")
    
    plat_scad_dir = os.path.join(platform_dir, "scad")
    routing_file = os.path.join(plat_scad_dir, "routing.scad")
    component_file = os.path.join(plat_scad_dir, "ls_components.scad") 
    
    px = "0.00762"
    layer = "0.01"
    lpv = "1"
    pitch = "37" # 37 px
    res = "30"
    
    cmd = [
        sys.executable, scad_pnr_script,
        "--design", design,
        "--platform", platform,
        "--def_file", def_file,
        "--tlef_file", tech_lef,
        "--routing_file", routing_file,
        "--component_file", component_file,
        "--results_dir", results_dir,
        "--px", px,
        "--layer", layer,
        "--lpv", lpv,
        "--pitch", pitch,
        "--res", res,
        "--bottom_layer", "0", #
        "--xbulk", "2000", # Need actual values 
        "--ybulk", "2000",
        "--zbulk", "200",
        "--xchip", "0", "2000",
        "--ychip", "0", "2000",
        "--stl",
        "--export_type", export_type
    ]
    cmd.extend(lef_args)
    
    print(f"Running export ({export_type})...")
    subprocess.run(cmd, check=True)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Ansys-compatible STL files")
    parser.add_argument("--design", required=True)
    parser.add_argument("--platform", default="h.r.3.3")
    args = parser.parse_args()
    
    # 1. Export Fluid Volume
    run_scad_export(args.design, args.platform, "fluid")
    
    # 2. Export Boundaries
    run_scad_export(args.design, args.platform, "boundaries")
    
    print("\nAnsys Export Complete.")
    print(f"Files generated in flow/results/{args.design}/base/")
