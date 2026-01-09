import sys
import os

# Setup environment
root = os.getcwd()
os.environ["OPENMFDA_ROOT"] = root
os.environ["OPENMFDA_USE_DOCKER"] = "1"
os.environ["PYTHON_CMD"] = sys.executable

sys.path.append(os.path.join(root, "src"))

try:
    from openmfda_flow.openmfda_flow_0_2 import run_flow
except ImportError:
    print("Failed to import openmfda_flow")
    sys.exit(1)

print("Starting reproduction run...")
try:
    # Attempt to run flow for myurinalysis on standard platform
    # Matches user's attempt
    run_flow(design_name="myurinalysis", platform="standard", mk_targets=["gen_pcells", "pnr", "render", "simulate"])
    print("Flow finished successfully.")
except Exception as e:
    print(f"Flow failed: {e}")
    sys.exit(1)
