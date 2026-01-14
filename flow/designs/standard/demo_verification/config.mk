export DESIGN_NAME     	= demo_verification
export VERILOG_FILES 	= ./designs/src/$(DESIGN_NAME)/$(DESIGN_NAME).v
export SDC_FILE      	= ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc
export IO_CONSTRAINTS	= ./designs/$(PLATFORM)/$(DESIGN_NAME)/io_constraints.tcl
export SIMULATION_CONFIG= ./designs/$(PLATFORM)/$(DESIGN_NAME)/simulation.config

SCAD_LIB = $(PLATFORM_DIR)/pdk/scad_lib

# Use p_cell_generator utils
export BUILD_PDK_LIBRARY ?= T
include $(FLOW_HOME)/../tools/p_cell_generator/util.mk

export GLOBAL_PLACEMENT_ARGS = -skip_nesterov_place
