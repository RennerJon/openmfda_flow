import subprocess
import os
import sys

def verify_docker():
    root = os.getcwd()
    print(f"Current Root: {root}")
    
    # 1. Check if Docker is accessible
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[Pass] Docker is installed and accessible.")
    except Exception as e:
        print(f"[Fail] Docker command failed: {e}")
        return

    # 2. Check Image
    image_name = "openmfda-flow"
    print(f"Checking for image: {image_name}")
    try:
        subprocess.run(["docker", "inspect", image_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[Pass] Image '{image_name}' exists.")
    except:
        print(f"[Fail] Image '{image_name}' NOT found. Please build it first.")
        return

    # 3. Test Volume Mount and Tools
    print("Testing container execution and tools...")
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{root}:/home/jovyan/openmfda_flow",
        image_name,
        "bash", "-c", "echo 'Mount OK' && ls /home/jovyan/openmfda_flow/flow/Makefile && which yosys && which python3 && python3 --version"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("[Pass] Container execution successful.")
            print("Container Output:\n", result.stdout)
        else:
            print("[Fail] Container execution failed.")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
    except Exception as e:
         print(f"[Fail] failed to run docker container: {e}")

if __name__ == "__main__":
    verify_docker()
