# update_design.tcl
# Re-runs routing from a modified placement DEF (2_place.def) to produce
# an updated routed DEF (3_route_1.def) for SCAD rendering.
# Called by the `run_tcl_script` make target in design config.mk files.

# Read lef
if [info exists ::env(GENERIC_TECH_LEF)] {
  read_lef $::env(GENERIC_TECH_LEF)
} else {
  read_lef $::env(TECH_LEF)
}
read_lef $::env(SC_LEF)
if {[info exist ::env(ADDITIONAL_LEFS)]} {
    foreach lef $::env(ADDITIONAL_LEFS) {
      read_lef $lef
    }
}

# Read liberty files
foreach libFile $::env(LIB_FILES) {
  read_liberty $libFile
}

# Read the modified placement DEF
read_def $::env(RESULTS_DIR)/2_place.def

if [file exists $::env(PLATFORM_DIR)/derate_final.tcl] {
  source $::env(PLATFORM_DIR)/derate_final.tcl
}

# Global routing
if {[info exist ::env(FASTROUTE_TCL)]} {
  foreach fast_rt $::env(FASTROUTE_TCL) {
    source $fast_rt
  }
} else {
  set_global_routing_layer_adjustment $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) 0.5
  set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)
  set_macro_extension 2
}

global_route -guide_file $::env(RESULTS_DIR)/route.guide \
               -congestion_iterations 200 \
               -verbose

# Detailed routing
set_thread_count $::env(NUM_CORES)

detailed_route -output_drc $::env(REPORTS_DIR)/3_route_drc.rpt \
               -output_guide $::env(RESULTS_DIR)/output_guide.mod \
               -output_maze $::env(RESULTS_DIR)/maze.log \
               -droute_end_iter 2 \
               -verbose 1 \
               -clean_patches

# Write wire lengths
report_wire_length -net {*} \
                   -file $::env(RESULTS_DIR)/wire_length.csv \
                   -verbose

# Write the routed DEF (used by SCAD renderer via SCAD_DEF = 3_route_1.def)
write_def $::env(RESULTS_DIR)/3_route_1.def

exit
