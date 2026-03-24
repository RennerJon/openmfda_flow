import sys
import os
import time

# Ensure we can import urinalysis_main
sys.path.append(os.path.join(os.path.dirname(__file__), "urinalysis_design_automation"))
import urinalysis_main

tests_to_run = [
    {
        "assay": "ketone_v2",
        "num_samples": 2,
        "input_dict": {"sample":50*10**(-6), "R1":50*10**(-6)}
    },
    {
        "assay": "nitrite",
        "num_samples": 3,
        "input_dict": {"sample":100*10**(-6), "R1":50*10**(-6), "R2":50*10**(-6)}
    },
    {
        "assay": "albumin_v2",
        "num_samples": 4,
        "input_dict": {"sample":6*10**(-6), "R1":215*10**(-6), "R2":25*10**(-6), "H2O":10*10**(-6)}
    }
]

platform = "h.r.3.3"
error_condition = 3

os.environ["OPENMFDA_USE_DOCKER"] = "1"

for test in tests_to_run:
    assay = test["assay"]
    num_samples = test["num_samples"]
    input_dict = test["input_dict"]
    
    print(f"\n=========================================")
    print(f"Running batch generation for assay: {assay}")
    print(f"=========================================\n")
    
    start_time = time.time()
    error_list_stored = urinalysis_main.store_design(num_samples)
    
    try:
        # Run main process which generates the scad and stl files
        urinalysis_main.main(assay, platform, num_samples, input_dict, error_condition, start_time, error_list_stored)
        print(f"Successfully finished generating {assay}")
    except Exception as e:
        print(f"Failed to run {assay}: {e}")
