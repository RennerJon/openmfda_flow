import sys
import os
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTabWidget, QComboBox, QFormLayout, QTableWidget,
                             QTableWidgetItem, QTextEdit, QScrollArea, QSplitter,
                             QSpinBox, QDoubleSpinBox, QGroupBox, QMessageBox,
                             QRadioButton, QButtonGroup, QStackedWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from printer_config import PrinterConfigurator

# Import main flow logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../urinalysis_design_automation")))
import urinalysis_main as flow_main

# Import runners
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from runners import run_scad_logic, run_sim_logic
except ImportError:
    print("Warning: Could not import runners. Simulation/Export features may fail.")

import subprocess

class ScadWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    
    def __init__(self, design, platform, use_docker=False, extra_args=None, def_file=None):
        super().__init__()
        self.design = design
        self.platform = platform
        self.use_docker = use_docker
        self.extra_args = extra_args or {}
        self.def_file = def_file
        
    def run(self):
        method = "Docker" if self.use_docker else "Local"
        self.log_signal.emit(f"Starting SCAD Generation ({method}) for {self.design} on {self.platform}...")
        try:
            run_scad_logic(self.design, self.platform, use_docker=self.use_docker, extra_args=self.extra_args, def_file=self.def_file)
            self.log_signal.emit("SCAD Generation Complete.")
        except subprocess.CalledProcessError as e:
            self.log_signal.emit("SCAD Generation Failed!")
            self.log_signal.emit(f"Output:\n{e.output}")
            self.log_signal.emit(f"Error:\n{e.stderr}")
        except Exception as e:
            self.log_signal.emit(f"Error: {e}")
            import traceback
            self.log_signal.emit(traceback.format_exc())
            if self.use_docker:
                 self.log_signal.emit("Hint: Ensure Docker Desktop is running!")
        self.finished_signal.emit()
class SimWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, design, sim_config=None, extra_args=None):
        super().__init__()
        self.design = design
        self.sim_config = sim_config
        self.extra_args = extra_args
        
    def run(self):
        self.log_signal.emit(f"Starting Simulation for {self.design}...")
        try:
            run_sim_logic(self.design, sim_config=self.sim_config, extra_args=self.extra_args)
            self.log_signal.emit("Simulation Complete.")
        except Exception as e:
            self.log_signal.emit(f"Error: {e}")
            import traceback
            self.log_signal.emit(traceback.format_exc())
        self.finished_signal.emit()

class FlowWorker(QThread):
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)

    def __init__(self, assay, num_samples, input_dict, platform="h.r.3.3"):
        super().__init__()
        self.assay = assay
        self.num_samples = num_samples
        self.input_dict = input_dict
        self.platform = platform
        
    def run(self):
        self.log_signal.emit(f"Starting flow for assay: {self.assay}")
        try:
            error_list_stored = [100 for _ in range(self.num_samples)]
            import time
            start_time = time.time()
            error_condition = 3 # Default 3%
            
            error_list, opt_time, max_x, chan_vol, reg_vol = flow_main.main(
                self.assay, self.platform, self.num_samples, self.input_dict, 
                error_condition, start_time, error_list_stored
            )
            
            result_str = "Flow Complete!\n\n"
            result_str += f"Optimal Time: {opt_time:.2f}s\n"
            result_str += f"Max X: {max_x}\n\nResults:\n"
            
            for i, (name, conc) in enumerate(self.input_dict.items()):
                 if i < len(error_list):
                     err = error_list[i] * 100
                     result_str += f"{name}: Error = {err:.2f}%\n"

            self.result_signal.emit(result_str)

        except Exception as e:
            self.log_signal.emit(f"Error during flow: {str(e)}")
            import traceback
            self.log_signal.emit(traceback.format_exc())

class OpenMFDAGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenMFDA Flow Interface")
        self.setGeometry(100, 100, 1000, 800)
        
        self.printer_config = PrinterConfigurator()

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.setup_run_tab() # Init first so logs are available
        self.setup_design_tab()
        self.setup_printer_tab() # Init last dependent on others
        self.setup_sim_export_tab()
        
        # Add tabs in visual order
        self.tabs.addTab(self.printer_tab, "1. Printer Config")
        self.tabs.addTab(self.design_tab, "2. Design Inputs")
        self.tabs.addTab(self.run_tab, "3. Execution Status")
        self.tabs.addTab(self.sim_export_tab, "4. Sim & Export")
        self.sync_name_to_tabs(self.assay_name.text())
        
    def setup_printer_tab(self):
        self.printer_tab = QWidget()
        main_layout = QVBoxLayout(self.printer_tab)
        
        # Mode Selection
        mode_group = QGroupBox("Configuration Mode")
        mode_layout = QHBoxLayout()
        self.radio_existing = QRadioButton("Use Existing Platform")
        self.radio_create = QRadioButton("Create / Edit Platform")
        self.radio_existing.setChecked(True)
        
        self.mode_bg = QButtonGroup()
        self.mode_bg.addButton(self.radio_existing)
        self.mode_bg.addButton(self.radio_create)
        self.mode_bg.buttonClicked.connect(self.update_printer_mode)
        
        mode_layout.addWidget(self.radio_existing)
        mode_layout.addWidget(self.radio_create)
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        # Stack for modes
        self.printer_stack = QStackedWidget()
        main_layout.addWidget(self.printer_stack)

        # --- PAGE 1: EXISTING PLATFORM ---
        self.page_existing = QWidget()
        layout_existing = QFormLayout(self.page_existing)
        
        self.existing_platform_combo = QComboBox()
        platforms = self.printer_config.get_available_platforms()
        display_items = []
        self.platform_map_existing = {}
        
        for p in platforms:
            if "p.m.8.k" in p:
                name = f"Phrozen Mini 8K ({p})"
            elif "h.r.3.3" in p:
                name = f"H.R. 3.3 ({p})"
            else:
                name = p
            self.platform_map_existing[name] = p
            display_items.append(name)
            
        self.existing_platform_combo.addItems(display_items)
        self.existing_platform_combo.currentTextChanged.connect(self.on_existing_platform_selected)
        
        layout_existing.addRow("Select Platform:", self.existing_platform_combo)
        
        # Info labels
        self.lbl_res = QLabel("-")
        self.lbl_layer = QLabel("-")
        self.lbl_bed = QLabel("-")
        
        layout_existing.addRow("Resolution:", self.lbl_res)
        layout_existing.addRow("Layer Height:", self.lbl_layer)
        layout_existing.addRow("Bed Size:", self.lbl_bed)
        
        self.printer_stack.addWidget(self.page_existing)

        # --- PAGE 2: CREATE / EDIT ---
        self.page_create = QWidget()
        layout_create = QFormLayout(self.page_create)
        
        # Helper for Presets
        self.presets = {
            "Phrozen Sonic Mini 8K": {"px": 0.022, "layer": 0.010, "x": 165, "y": 72, "z": 180},
            "Phrozen Sonic Mini 4K": {"px": 0.035, "layer": 0.035, "x": 134, "y": 75, "z": 130},
            "Bambu Lab X1C (0.4mm nozzle)": {"px": 0.400, "layer": 0.200, "x": 256, "y": 256, "z": 256},
            "Elegoo Mars 3": {"px": 0.035, "layer": 0.035, "x": 143, "y": 89, "z": 175},
            "Elegoo Saturn 2": {"px": 0.0285, "layer": 0.030, "x": 219, "y": 123, "z": 250},
        }
        
        self.printer_select = QComboBox()
        preset_items = [f"[Preset] {name}" for name in self.presets.keys()]
        self.printer_select.addItems(preset_items)
        self.printer_select.addItem("Custom")
        self.printer_select.currentTextChanged.connect(self.load_printer_defaults)
        
        self.platform_name_input = QLineEdit() # Shared / centralized source of truth
        
        self.px_val_input = QDoubleSpinBox()
        self.px_val_input.setRange(0.001, 1.0)
        self.px_val_input.setDecimals(4)
        self.px_val_input.setSuffix(" mm")
        
        self.layer_height_input = QDoubleSpinBox()
        self.layer_height_input.setRange(0.001, 1.0)
        self.layer_height_input.setDecimals(3)
        self.layer_height_input.setSuffix(" mm")
        
        self.bed_x_input = QSpinBox()
        self.bed_x_input.setRange(10, 1000)
        self.bed_x_input.setSuffix(" mm")
        self.bed_y_input = QSpinBox()
        self.bed_y_input.setRange(10, 1000)
        self.bed_y_input.setSuffix(" mm")
        self.bed_z_input = QSpinBox()
        self.bed_z_input.setRange(10, 1000)
        self.bed_z_input.setSuffix(" mm")
        
        update_btn = QPushButton("Update / Create Platform")
        update_btn.clicked.connect(self.update_printer_config)
        update_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")

        layout_create.addRow("Load Preset:", self.printer_select)
        layout_create.addRow("Target Folder Name:", self.platform_name_input)
        layout_create.addRow("XY Resolution:", self.px_val_input)
        layout_create.addRow("Layer Height:", self.layer_height_input)
        layout_create.addRow("Bed Size X:", self.bed_x_input)
        layout_create.addRow("Bed Size Y:", self.bed_y_input)
        layout_create.addRow("Build Height:", self.bed_z_input)
        layout_create.addRow("", update_btn)
        
        self.printer_stack.addWidget(self.page_create)
        
        # Init Defaults
        if display_items:
            self.on_existing_platform_selected(display_items[0])

    def update_printer_mode(self):
        if self.radio_existing.isChecked():
            self.printer_stack.setCurrentIndex(0)
            # Re-trigger selection logic to ensure platform name is correct
            self.on_existing_platform_selected(self.existing_platform_combo.currentText())
        else:
            self.printer_stack.setCurrentIndex(1)
            # When switching to create, we might want to clear the platform name or leave it?
            # Leaving it allows user to 'Edit' the currently selected one.
    
    def on_existing_platform_selected(self, name):
        p_dir = self.platform_map_existing.get(name)
        if p_dir:
            self.platform_name_input.setText(p_dir)
            print(f"DEBUG: Selected platform {p_dir}")
            
            # Load config for display
            config = self.printer_config.load_platform_config(p_dir)
            if config:
                self.lbl_res.setText(f"{config['px']} mm")
                self.lbl_layer.setText(f"{config['layer']} mm")
                self.lbl_bed.setText(f"{config['x']} x {config['y']} x {config['z']} mm")
            else:
                self.lbl_res.setText("Error loading config")
        else:
            self.platform_name_input.clear()

    def load_printer_defaults(self, name):
        print(f"DEBUG: Loading defaults for {name}")
        try:
            if name == "Custom":
                # self.platform_name_input.clear() 
                return
                
            # Check if it's a preset
            if name.startswith("[Preset] "):
                preset_name = name.replace("[Preset] ", "")
                if preset_name in self.presets:
                    vals = self.presets[preset_name]
                    print(f"DEBUG: Found preset vals: {vals}")
                    self.px_val_input.setValue(float(vals["px"]))
                    self.layer_height_input.setValue(float(vals["layer"]))
                    self.bed_x_input.setValue(int(vals["x"]))
                    self.bed_y_input.setValue(int(vals["y"]))
                    self.bed_z_input.setValue(int(vals["z"]))
                return

        except Exception as e:
            print(f"ERROR in load_printer_defaults: {e}")
            import traceback
            traceback.print_exc()

    def update_printer_config(self):
        print("DEBUG: update_printer_config called")
        try:
            platform = self.platform_name_input.text().strip()
            if not platform:
                QMessageBox.warning(self, "Invalid Input", "Please enter a Platform Folder Name.")
                return

            # Check if directory exists
            platform_path = os.path.join(self.printer_config.flow_path, "flow", "platforms", platform)
            if not os.path.isdir(platform_path):
                # Ask user if they want to create it
                reply = QMessageBox.question(self, "Create New Platform?", 
                                           f"The platform '{platform}' does not exist.\nDo you want to create a new platform based on the standard template?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                                           
                if reply == QMessageBox.Yes:
                    self.log_message(f"Creating new platform '{platform}'...")
                    self.printer_config.create_new_platform(platform)
                    self.log_message("Platform created.")
                else:
                    return

            px = self.px_val_input.value()
            layer = self.layer_height_input.value()
            x = self.bed_x_input.value()
            y = self.bed_y_input.value()
            z = self.bed_z_input.value()
            
            self.log_message(f"Updating platform '{platform}'...")
            self.log_message(f"Values: px={px}, layer={layer}, bed={x},{y},{z}")
            
            # Run update
            self.printer_config.update_platform(platform, px, layer, x, y, z)
            
            self.log_message("Printer configuration updated successfully!")
            QMessageBox.information(self, "Success", f"Platform '{platform}' updated.")
            self.tabs.setCurrentIndex(2) # Move to Execution Status tab (index 2)
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.log_message(f"Error updating printer: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def setup_design_tab(self):
        self.design_tab = QWidget()
        layout = QVBoxLayout(self.design_tab)
        
        form_layout = QFormLayout()
        
        self.assay_presets = {
            "Custom": None,
            "Protein Assay (BCA)": {
                "assay_name": "protein_bca_assay",
                "samples": 2,
                "reagents": [("Protein Sample (BSA)", 10.0), ("BCA Reagent", 200.0)]
            },
            "Glucose Assay": {
                "assay_name": "glucose_standard_assay",
                "samples": 3,
                "reagents": [("Glucose Sample", 10.0), ("Enzyme Mix (GOx/HRP)", 100.0), ("Dye (o-dianisidine)", 50.0)]
            },
            "Nitrate Assay (Griess)": {
                "assay_name": "nitrate_water_test",
                "samples": 3,
                "reagents": [("Water Sample", 50.0), ("Griess Reagent A", 25.0), ("Griess Reagent B", 25.0)]
            },
            "HIV-1 Genotyping": {
                "assay_name": "hiv1_genotyping",
                "samples": 4, # Simplified representation
                "reagents": [("Plasma Sample", 140.0), ("Lysis Buffer", 560.0), ("Ethanol", 560.0), ("Wash Buffer", 500.0)]
            }
        }

        self.assay_preset_combo = QComboBox()
        self.assay_preset_combo.addItems(self.assay_presets.keys())
        self.assay_preset_combo.currentTextChanged.connect(self.load_assay_preset)

        self.assay_name = QLineEdit("MyUrinalysis")
        self.assay_name.textChanged.connect(self.sync_name_to_tabs)
        
        self.num_samples_spin = QSpinBox()
        self.num_samples_spin.setRange(1, 10)
        self.num_samples_spin.setValue(2)
        self.num_samples_spin.valueChanged.connect(self.update_reagent_inputs)
        
        form_layout.addRow("Assay Preset:", self.assay_preset_combo)
        form_layout.addRow("Assay Name:", self.assay_name)
        form_layout.addRow("Number of Samples/Reagents:", self.num_samples_spin)
        
        layout.addLayout(form_layout)
        
        # Reagent inputs container
        self.reagents_group = QGroupBox("Reagents & Concentrations (uL)")
        self.reagents_layout = QFormLayout()
        self.reagents_group.setLayout(self.reagents_layout)
        
        layout.addWidget(self.reagents_group)
        
        self.reagent_inputs = [] # List of (name_widget, conc_widget)
        self.update_reagent_inputs(2)

        run_btn = QPushButton("Run Simulation Flow")
        run_btn.clicked.connect(self.run_flow)
        run_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(run_btn)
        
        layout.addStretch()
        # self.tabs.addTab(self.design_tab, "2. Design Inputs")

    def load_assay_preset(self, name):
        if name == "Custom":
            return
            
        preset = self.assay_presets.get(name)
        if preset:
            print(f"DEBUG: Loading assay preset: {name}")
            self.assay_name.setText(preset["assay_name"])
            
            # Update spinbox which triggers update_reagent_inputs
            self.num_samples_spin.setValue(preset["samples"])
            
            reagents = preset["reagents"]
            if len(reagents) == len(self.reagent_inputs):
                for i, (r_name, r_vol) in enumerate(reagents):
                    name_w, conc_w = self.reagent_inputs[i]
                    name_w.setText(r_name)
                    conc_w.setValue(r_vol)

    def update_reagent_inputs(self, num):
        # Clear existing
        # This is a bit brute force, clearing layout
        while self.reagents_layout.count():
            item = self.reagents_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        self.reagent_inputs = []
        
        for i in range(num):
            if i == 0:
                default_name = "sample"
                default_conc = 50.0
            else:
                default_name = f"R{i}"
                default_conc = 50.0
            
            name_edit = QLineEdit(default_name)
            conc_spin = QDoubleSpinBox()
            conc_spin.setRange(0.0, 1000.0)
            conc_spin.setSuffix(" uL")
            conc_spin.setValue(default_conc)
            
            self.reagents_layout.addRow(f"Reagent {i+1} Name:", name_edit)
            self.reagents_layout.addRow(f"Concentration:", conc_spin)
            
            self.reagent_inputs.append((name_edit, conc_spin))

    def setup_run_tab(self):
        self.run_tab = QWidget()
        layout = QVBoxLayout(self.run_tab)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #222; color: #0f0; font-family: Courier;")
        
        layout.addWidget(QLabel("Process Log & Results:"))
        layout.addWidget(self.log_output)
        
        layout.addWidget(self.log_output)
        
        # self.tabs.addTab(self.run_tab, "3. Execution Status")

    def populate_printer_profiles(self):
        import glob
        try:
            # Assuming profile json files are in tools/slicer/profiles/
            root = os.environ.get("OPENMFDA_ROOT", ".")
            profiles_dir = os.path.join(root, "tools", "slicer", "profiles")
            if os.path.exists(profiles_dir):
                files = glob.glob(os.path.join(profiles_dir, "*.json"))
                for f in files:
                    name = os.path.splitext(os.path.basename(f))[0]
                    self.scad_profile_combo.addItem(name)
        except Exception as e:
            print(f"Error loading profiles: {e}")

    def populate_platforms(self, combo):
        platforms = self.printer_config.get_available_platforms()
        combo.addItems(platforms)

    def populate_designs(self, combo):
        root = os.environ.get("OPENMFDA_ROOT", ".")
        designs_dir = os.path.join(root, "flow", "designs")
        if os.path.exists(designs_dir):
            found_designs = set()
            for platform in os.listdir(designs_dir):
                p_path = os.path.join(designs_dir, platform)
                if os.path.isdir(p_path):
                    for design in os.listdir(p_path):
                         if os.path.isdir(os.path.join(p_path, design)):
                             found_designs.add(design)
            combo.addItems(sorted(list(found_designs)))

    def setup_sim_export_tab(self):
        self.sim_export_tab = QWidget()
        layout = QVBoxLayout(self.sim_export_tab)
        
        # --- SCAD Generation ---
        scad_group = QGroupBox("3D Model Generation (OpenSCAD)")
        scad_layout = QFormLayout()
        scad_group.setLayout(scad_layout)
        
        self.scad_design_combo = QComboBox()
        self.populate_designs(self.scad_design_combo)
        self.scad_design_combo.setEditable(True) # Allow typing specific names too

        self.scad_platform_combo = QComboBox()
        self.populate_platforms(self.scad_platform_combo)
        self.scad_platform_combo.setEditable(True)
        self.scad_docker_check = QComboBox()
        self.scad_docker_check.addItems(["Run Locally (Requires opendbpy)", "Run in Docker (Recommended)"])
        self.scad_docker_check.setCurrentIndex(1) # Default to Docker
        self.scad_stl_check = QGroupBox("Export STL")
        self.scad_stl_check.setCheckable(True)
        self.scad_stl_check.setChecked(False)
        
        self.scad_def_input = QLineEdit()
        self.scad_def_input.setPlaceholderText("Optional: Absolute path to .def file")
        
        btn_scad = QPushButton("Generate 3D Model")
        btn_scad.clicked.connect(self.start_scad_gen)
        
        scad_layout.addRow("Design Name:", self.scad_design_combo)
        scad_layout.addRow("Platform:", self.scad_platform_combo)
        scad_layout.addRow("Execution Mode:", self.scad_docker_check)
        scad_layout.addRow("Export STL:", self.scad_stl_check)
        scad_layout.addRow("Input DEF File:", self.scad_def_input)
        scad_layout.addRow("", btn_scad)
        
        layout.addWidget(scad_group)
        
        # --- Simulation ---
        sim_group = QGroupBox("Electrical/Fluidic Simulation (Xyce)")
        sim_layout = QFormLayout()
        sim_group.setLayout(sim_layout)
        
        self.sim_design_input = QLineEdit()
        self.sim_config_input = QLineEdit("sim_config.config")
        self.sim_plot_check = QComboBox() 
        self.sim_plot_check.addItems(["No Plot", "Plot Results"])
        
        btn_sim = QPushButton("Run Simulation")
        btn_sim.clicked.connect(self.start_sim_run)
        
        sim_layout.addRow("Design Name:", self.sim_design_input)
        sim_layout.addRow("Config File:", self.sim_config_input)
        sim_layout.addRow("Plotting:", self.sim_plot_check)
        sim_layout.addRow("", btn_sim)
        
        layout.addWidget(sim_group)
        layout.addStretch()

    def sync_name_to_tabs(self, text):
        formatted = text.strip().replace(" ", "_").lower()
        self.scad_design_combo.setCurrentText(formatted)
        self.sim_design_input.setText(formatted)

        # Auto-fill verification DEF for myurinalysis demo to help user
        if formatted == "myurinalysis":
             # Calculate root based on current file location (tools/gui/app.py -> ../..)
             root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
             demo_def = os.path.join(root, "tools/route_scripts/testing_files/6_reroute_cp.def")
             if os.path.exists(demo_def):
                 print(f"DEBUG: Auto-filling DEF: {demo_def}")
                 self.scad_def_input.setText(demo_def)
             else:
                 print(f"DEBUG: DEF file not found at {demo_def}")

    def sync_inputs(self):
        # Helper to pull values from other tabs
        design = self.assay_name.text().strip().replace(" ", "_").lower()
        platform = self.platform_name_input.text().strip()
        
        if not self.scad_design_combo.currentText():
            self.scad_design_combo.setCurrentText(design)
        if not self.scad_platform_combo.currentText():
            self.scad_platform_combo.setCurrentText(platform)
        if not self.sim_design_input.text():
            self.sim_design_input.setText(design)

    def start_scad_gen(self):
        self.sync_inputs()
        design = self.scad_design_combo.currentText().strip()
        platform = self.scad_platform_combo.currentText().strip()
        use_docker = (self.scad_docker_check.currentIndex() == 1)
        
        generate_stl = self.scad_stl_check.isChecked()
        def_file = self.scad_def_input.text().strip()
        
        if not design or not platform:
             QMessageBox.warning(self, "Missing Info", "Design and Platform are required.")
             return
             
        self.tabs.setCurrentIndex(2) # Go to log
        extras = {}
        if generate_stl:
            extras['stl'] = True

        self.scad_worker = ScadWorker(design, platform, use_docker=use_docker, extra_args=extras, def_file=def_file)
        self.scad_worker.log_signal.connect(self.log_message)
        self.scad_worker.start()

    def start_sim_run(self):
        self.sync_inputs()
        design = self.sim_design_input.text().strip()
        config = self.sim_config_input.text().strip()
        
        if not design:
             QMessageBox.warning(self, "Missing Info", "Design name is required.")
             return
        
        extra = {}
        if self.sim_plot_check.currentIndex() == 1:
            extra['plot'] = True
            
        self.tabs.setCurrentIndex(2) # Go to log
        self.sim_worker = SimWorker(design, sim_config=config, extra_args=extra)
        self.sim_worker.log_signal.connect(self.log_message)
        self.sim_worker.start()

    def log_message(self, msg):
        if hasattr(self, 'log_output'):
            self.log_output.append(msg)
            # Ensure latest log is visible
            sb = self.log_output.verticalScrollBar()
            sb.setValue(sb.maximum())
        else:
            print(f"LOG (pre-init): {msg}")

    def run_flow(self):
        self.tabs.setCurrentIndex(2)
        self.log_message("Preparing to run flow...")
        
        # Gather inputs
        assay = self.assay_name.text().strip().replace(" ", "_").lower()
        self.scad_design_combo.setCurrentText(assay)
        self.sim_design_input.setText(assay)
        
        num_samples = self.num_samples_spin.value()
        
        input_dict = {}
        for name_w, conc_w in self.reagent_inputs:
            name = name_w.text()
            conc = conc_w.value() * 1e-6 # Convert uL to L
            input_dict[name] = conc
            
        platform = self.platform_name_input.text().strip()
        if not platform:
            QMessageBox.warning(self, "Missing Platform", "Please enter a valid Platform Folder Name (e.g. 'p.m.8.k' or create a new one).")
            return

        self.worker = FlowWorker(assay, num_samples, input_dict, platform)
        self.worker.log_signal.connect(self.log_message)
        self.worker.result_signal.connect(self.log_message)
        self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Simple stylesheet for aesthetics
    app.setStyleSheet("""
        QWidget {
            font-size: 14px;
        }
        QGroupBox {
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
        }
    """)
    
    window = OpenMFDAGUI()
    window.show()
    sys.exit(app.exec_())
