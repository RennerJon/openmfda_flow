import subprocess
import os
import glob
import math
import re
import shutil

class PrinterConfigurator:
    def __init__(self):
        # tools/gui -> tools -> root
        self.flow_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def edit_file(self, filename, parameter, new_value, sub_num):
        """
        Refactored edit_file to work with relative paths from the project root
        or absolute paths.
        """
        # Ensure filename is correct relative to flow root if it's not absolute
        if not os.path.isabs(filename):
            filename = os.path.join(self.flow_path, filename)

        if not os.path.exists(filename):
            print(f"Warning: File not found: {filename}")
            return

        # regex string assignment based on file type/needs
        if sub_num == 0:
            sub_str = rf"({parameter})+\s*=\s*\d+(\.\d+)?"
        elif sub_num == 1:
            sub_str = rf"({parameter})+\s*=[\s*0]*\s*\d+(\.\d+)?\s*\d+(\.\d+)?"
        elif sub_num == 2:
            sub_str = rf"({parameter})\s*\d+(\.\d+)?\s*\d+(\.\d+)?\s*\d+(\.\d+)?"
        elif sub_num == 3:
            sub_str = rf"({parameter})\s*\d+(\.\d+)?"
        elif sub_num == 4:
            sub_str = rf"({parameter})+\s*=\s*[a-z].*"
        elif sub_num == 5:
            sub_str = rf"({parameter})\s*[a-z]*+_+[a-z]*"
        elif sub_num == 6:
            sub_str = rf"({parameter})+\s*=\s*\"[a-z].*"
        else:
            sub_str = rf"({parameter})+\s*=\s*.?(\/[a-z]*)*\$\(DESIGN_NAME\)\/[a-z]*_[a-z]*.v"
            
        # regex string
        re_str = re.compile(sub_str)

        # find parameter of interest in file and replace with new value
        try:
            with open(filename, 'r') as f:
                ifile = f.read()
            
            ifile = re_str.sub(f"{parameter} {new_value}", ifile)
            
            with open(filename, "w") as f:
                f.writelines(ifile)
        except Exception as e:
            print(f"Error editing {filename}: {e}")

    def create_new_platform(self, new_platform_name, base_platform="h.r.3.3"):
        """
        Creates a new platform directory by copying a base template.
        """
        base_path = os.path.join(self.flow_path, "flow", "platforms", base_platform)
        new_path = os.path.join(self.flow_path, "flow", "platforms", new_platform_name)
        
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"Base platform template '{base_platform}' not found at {base_path}")
            
        if os.path.exists(new_path):
            print(f"Platform '{new_platform_name}' allready exists.")
            return

        print(f"Creating new platform '{new_platform_name}' from '{base_platform}'...")
        try:
            shutil.copytree(base_path, new_path, symlinks=True, ignore_dangling_symlinks=True)
            print("Copy complete.")
        except shutil.Error as e:
            print(f"Warning during copy: {e}")
            print("Proceeding anyway as some files might be broken symlinks in the repo.")
        except Exception as e:
             print(f"Critical error creating platform: {e}")
             raise e

    def update_platform(self, platform_name, px_val_mm, layer_height_mm, x_bulk_mm, y_bulk_mm, z_bulk_mm):
        """
        Updates the platform configuration with new printer specifications.
        """
        # Derived values
        px_val = px_val_mm
        layer = layer_height_mm
        
        # Channel defaults (from original script, can be arguments later)
        chan_w_mm = 0.200 # 200um
        chan_h_mm = 0.200 # 200um
        
        chan_w = int(chan_w_mm / px_val)
        chan_h = int(chan_h_mm / layer)
        lpv = chan_h * 2 
        
        xbulk_val = int(x_bulk_mm / px_val)
        ybulk_val = int(y_bulk_mm / px_val)
        zbulk_val = int(z_bulk_mm / layer)
        
        print(f"Updating {platform_name} with: px={px_val}, layer={layer}, size=({xbulk_val}, {ybulk_val}, {zbulk_val})")

        # MODIFY config.mk WITH NEW PRINTER SPECS
        config_mk = f"flow/platforms/{platform_name}/config.mk"
        
        self.edit_file(config_mk, "PX_VAL", f"= {px_val}", 0)
        self.edit_file(config_mk, " LAYER_VAL", f"= {layer}", 0) # Note the space in key
        self.edit_file(config_mk, "LPV_VAL", f"= {lpv}", 0)
        self.edit_file(config_mk, "XBULK_VAL", f"= {xbulk_val}", 0)
        self.edit_file(config_mk, "YBULK_VAL", f"= {ybulk_val}", 0)
        self.edit_file(config_mk, "ZBULK_VAL", f"= {zbulk_val}", 0)
        self.edit_file(config_mk, "DIE_AREA", f"= 0 0 {xbulk_val} {ybulk_val}", 1)
        self.edit_file(config_mk, "CORE_AREA", f"= 0 0 {xbulk_val} {ybulk_val}", 1)
        self.edit_file(config_mk, "--io_size", f"{chan_w} {chan_w}", 2)
        self.edit_file(config_mk, "--routing_size", f"{chan_w} {chan_w} {chan_h}", 2)

        # MODIFY scad_header.scad
        scad_header = f"flow/platforms/{platform_name}/pdk/py_scripts/scad_header.scad"
        self.edit_file(scad_header, "px", f"= {px_val}", 0)
        self.edit_file(scad_header, "layer", f"= {layer}", 0)
        self.edit_file(scad_header, "lpv", f"= {lpv}", 0)

        # MODIFY INDIVIDUAL SCAD FILES in PDK
        files = glob.glob(os.path.join(self.flow_path, f"flow/platforms/{platform_name}/pdk/Components/*/*/*.scad"), recursive=True)
        for file in files:
            self.edit_file(file, "px", f"= {px_val}", 0)
            self.edit_file(file, "layer", f"= {layer}", 0)
            self.edit_file(file, "hchan", f"= {chan_h}", 0)
            self.edit_file(file, "chan_h", f"= {chan_h}", 0)
            self.edit_file(file, "Wchan", f"= {chan_w}", 0)
            self.edit_file(file, "chan_w", f"= {chan_w}", 0)
            self.edit_file(file, "lpv", f"= {lpv}", 0)
            self.edit_file(file, "dwn_chan_h", f"= {chan_h}", 0)
            self.edit_file(file, "dwn_chan_w", f"= {chan_w}", 0)
            self.edit_file(file, "port_chan_h", f"= {chan_h}", 0)
            self.edit_file(file, "port_chan_w", f"= {chan_w}", 0)

        # MODIFY lef_scad_config.scad
        lef_config = f"flow/platforms/{platform_name}/pdk/scad_include/lef_scad_config.scad"
        self.edit_file(lef_config, '"lpv",', lpv, 3)
        self.edit_file(lef_config, '"px",', px_val, 3)
        self.edit_file(lef_config, '"layer",', layer, 3)
        self.edit_file(lef_config, '"via_w",', chan_w, 3)

        # Rebuild LEF and SCAD libraries (requires make commands)
        # Assuming make is available in path
        try:
             # make scad_2_lef in pdk/Components
            subprocess.run(f"cd flow/platforms/{platform_name}/pdk/Components && make scad_2_lef", shell=True, check=False)
            # make build_lef in pdk/Components
            subprocess.run(f"cd flow/platforms/{platform_name}/pdk/Components && make build_lef", shell=True, check=False)
            # make build_scad in pdk/Components
            subprocess.run(f"cd flow/platforms/{platform_name}/pdk/Components && make build_scad", shell=True, check=False)
            # make build_scad in pdk
            subprocess.run(f"cd flow/platforms/{platform_name}/pdk && make build_scad", shell=True, check=False)
        except Exception as e:
            print(f"Error running make commands: {e}")

        # MODIFY INDIVIDUAL VA FILES
        files = glob.glob(os.path.join(self.flow_path, f"flow/platforms/{platform_name}/pdk/Components/*/*/*.va"), recursive=True)
        for file in files:
            self.edit_file(file, "pixel_size", f"= {px_val*10**3}", 0)
            self.edit_file(file, "layer_height", f"= {layer*10**3}", 0)
            self.edit_file(file, "ch_height_layers", f"= {chan_h}", 0)
            self.edit_file(file, "ch_width_pixels", f"= {chan_w}", 0)
            self.edit_file(file, "lpv", f"= {lpv}", 0)
            
            if "diffmix_25px_" in file:
                self.edit_file(file, "LENGTH1", f"= {round(0.19 * px_val / (7.6e-3), 3)}", 0)
                self.edit_file(file, "LENGTH2", f"= {round(0.269 * px_val / (7.6e-3), 3)}", 0)  
                self.edit_file(file, "LENGTH3", f"= {round(0.19 * px_val / (7.6e-3), 3)}", 0)

        # Rebuild VA (requires make commands)
        try:
             subprocess.run(f"cd flow/platforms/{platform_name}/pdk/Components && make build_va", shell=True, check=False)
        except Exception as e:
            print(f"Error running make build_va: {e}")
            
        print("Platform update complete.")

    def get_available_platforms(self):
        """
        Returns a list of platform names found in flow/platforms.
        """
        platforms_dir = os.path.join(self.flow_path, "flow", "platforms")
        if not os.path.isdir(platforms_dir):
            return []
        
        # List directories only
        platforms = [d for d in os.listdir(platforms_dir) 
                     if os.path.isdir(os.path.join(platforms_dir, d)) and not d.startswith('.')]
        return sorted(platforms)

    def load_platform_config(self, platform_name):
        """
        Reads config.mk for the given platform and returns a dictionary
        of printer settings {px, layer, x_mm, y_mm, z_mm}.
        """
        config_mk = os.path.join(self.flow_path, f"flow/platforms/{platform_name}/config.mk")
        
        if not os.path.exists(config_mk):
            print(f"Config file not found: {config_mk}")
            return None
            
        settings = {}
        
        try:
            with open(config_mk, 'r') as f:
                content = f.read()
                
            # Helper to extract value using regex
            def extract(key):
                # Regex looking for export KEY = value
                # Handles spaces around = and comments
                match = re.search(rf"export\s+{key}\s*=\s*([\d\.]+)", content)
                if match:
                    return float(match.group(1))
                return None

            px_val = extract("PX_VAL")
            layer_val = extract("LAYER_VAL")
            x_bulk = extract("XBULK_VAL")
            y_bulk = extract("YBULK_VAL")
            z_bulk = extract("ZBULK_VAL")
            
            if None in [px_val, layer_val, x_bulk, y_bulk, z_bulk]:
                print(f"Warning: Could not parse all values from {config_mk}")
                # Fallback or partial
                return None
                
            settings = {
                "px": px_val,
                "layer": layer_val,
                "x": int(x_bulk * px_val), # Convert px to mm
                "y": int(y_bulk * px_val), # Convert px to mm
                "z": int(z_bulk * layer_val) # Convert layers to mm
            }
            return settings
            
        except Exception as e:
            print(f"Error reading config: {e}")
            return None

if __name__ == "__main__":
    # Test block
    pc = PrinterConfigurator()
    print("Platforms:", pc.get_available_platforms())
    print("p.m.8.k config:", pc.load_platform_config("p.m.8.k"))
    # pc.update_platform("p.m.8.k", 0.022, 0.010, 160, 80, 15) # Example for Mini 8K
