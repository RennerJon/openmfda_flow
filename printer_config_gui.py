import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from tkinter import filedialog as fd
#Renner Jones - added GUI for printer configuration 11/13/2025


class PrinterConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Printer Library Configuration")
        self.root.geometry("1280x720")
        
        # Define configuration fields with their properties
        self.config_fields = {
            "Printer Settings": [
                ("Printer Name", "printer_name", "string", "Phrozen Sonic Mini 8K"),
                ("Design Name", "design_name", "string", "Print Design Name"),
            ],
            "Resolution & Layer": [
                ("X Resolution (um)", "px_x_val", "float", "22"),
                ("Y Resolution (um)", "px_y_val", "float", "22"),
                ("Layer Height (um)", "layer", "float", "10"), 
            ],
            "Channel Dimensions": [
                ("Channel Width (um)", "chan_w_um", "float", "200"),
                ("Channel Height (um)", "chan_h_um", "float", "200"),
                ("Layers Per Via", "lpv_multiplier", "float", "2.0"),
            ],
            "Print Bed Size": [
                ("Print Size X (mm)", "xbulk_val_mm", "int", "75"),
                ("Print Size Y (mm)", "ybulk_val_mm", "int", "25"),
                ("Print Size Z (mm)", "zbulk_val_mm", "int", "15"),
            ],
        }
        
        self.entries = {}
        self.create_widgets()
        
    def create_widgets(self):
        """Create the GUI form with all fields organized by section"""
        
        # Main frame with scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="Printer Library Configuration", 
                               font=("Cambria", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Create scrollable area
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add mouse wheel scrolling for user if window is too large for screen
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create sections
        for section_name, fields in self.config_fields.items():
            self.create_section(scrollable_frame, section_name, fields)
        
        # Bottom frame for buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10, padx=10, fill=tk.X)
        
        reset_btn = ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        load_btn = ttk.Button(button_frame, text="Load Configuration", command=self.load_config)
        load_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = ttk.Button(button_frame, text="Save Configuration", command=self.save_config)
        save_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(button_frame, text="Delete Configuration", command=self.delete_config)
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        apply_btn = ttk.Button(button_frame, text="Apply & Run Script", command=self.apply_config)
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
    def create_section(self, parent, section_name, fields):
        """Create a section frame with labeled fields"""
        
        # Section frame with border and title
        section_frame = ttk.LabelFrame(parent, text=section_name, padding=10)
        section_frame.pack(fill=tk.X, padx=10, pady=10)
        
        for label_text, field_key, field_type, default_value in fields:
            # Row frame for each field
            row_frame = ttk.Frame(section_frame)
            row_frame.pack(fill=tk.X, pady=5)
            
            # Label for the field
            label = ttk.Label(row_frame, text=label_text, width=25, anchor="w")
            label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Entry field for user input
            entry = ttk.Entry(row_frame, width=30)
            entry.pack(side=tk.LEFT, padx=5)
            entry.insert(0, default_value)
            
            # Store reference
            self.entries[field_key] = {
                "widget": entry,
                "type": field_type,
                "label": label_text,
                "default": default_value
            }
            
            # Help text
            if field_type == "float":
                unit_label = ttk.Label(row_frame, text="(decimal)", foreground="gray")
                unit_label.pack(side=tk.LEFT, padx=5)
            elif field_type == "int":
                unit_label = ttk.Label(row_frame, text="(integer)", foreground="gray")
                unit_label.pack(side=tk.LEFT, padx=5)
    
    def get_values(self):
        """Extract and validate all values from form"""
        values = {}
        
        for field_key, field_data in self.entries.items():
            entry_widget = field_data["widget"]
            field_type = field_data["type"]
            label_text = field_data["label"]
            
            try:
                raw_value = entry_widget.get().strip()
                
                if not raw_value:
                    raise ValueError(f"{label_text} cannot be empty")
                
                if field_type == "float":
                    values[field_key] = float(raw_value)
                elif field_type == "int":
                    values[field_key] = int(raw_value)
                else:  # string
                    values[field_key] = raw_value
                    
            except ValueError as e:
                messagebox.showerror("Input Error", 
                    f"Invalid value for {label_text}: {str(e)}")
                return None
        
        return values
    
    def reset_defaults(self):
        """Reset all fields to default values"""
        for field_key, field_data in self.entries.items():
            field_data["widget"].delete(0, tk.END)
            field_data["widget"].insert(0, field_data["default"])
        messagebox.showinfo("Success", "All fields reset to defaults")
    
    def save_config(self):
        """Save current configuration to JSON file"""
        values = self.get_values()
        if values is None:
            return
        
        configs_dir = os.path.join(os.getcwd(), "printer_configs")
        os.makedirs(configs_dir, exist_ok=True)
        filename = os.path.join(configs_dir, "printer_config.json")
        try:
            with open(filename, 'w') as f:
                json.dump(values, f, indent=4)
            messagebox.showinfo("Success", f"Configuration saved to {filename}")
        except Exception as e:
            messagebox.showerror("Failure", f"Failed to save configuration: {str(e)}")
    
    
    def delete_config(self):
        """Delete a saved configuration file"""
        file_path = fd.askopenfilename(
            parent=self.root,
            initialdir=os.path.join(os.getcwd(), "printer_configs"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Select configuration file to delete"
        )
        
        if not file_path:
            return
        
        confirm = messagebox.askyesno("Confirm Delete", 
            f"Are you sure you want to delete:\n{os.path.basename(file_path)}?")
        
        if confirm:
            try:
                os.remove(file_path)
                messagebox.showinfo("Success", "Configuration file deleted")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete configuration: {str(e)}")


    def load_config(self):
        """Load configuration from JSON file"""
        file_path = fd.askopenfilename(
            parent=self.root,
            initialdir=os.path.join(os.getcwd(), "printer_configs"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Select printer configuration file"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                values = json.load(f)
            
            for field_key, value in values.items():
                if field_key in self.entries:
                    self.entries[field_key]["widget"].delete(0, tk.END)
                    self.entries[field_key]["widget"].insert(0, str(value))
            
            messagebox.showinfo("Success", f"Configuration loaded from:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
    
    def apply_config(self):
        """Apply configuration and prepare for script execution"""
        values = self.get_values()
        if values is None:
            return
        
        # Validate specific constraints
        if values.get("chan_w_um", 0) <= 0 or values.get("chan_h_um", 0) <= 0:
            messagebox.showerror("Validation Error", "Channel dimensions must be positive")
            return
        
        if values.get("px_x_val", 0) <= 0 or values.get("layer", 0) <= 0 or values.get("px_y_val", 0) <= 0:
            messagebox.showerror("Validation Error", "Resolution and layer height must be positive")
            return
        
        # Prompt user to save this configuration under a chosen name (and update default file)
        try:

            configs_dir = os.path.join(os.getcwd(), "printer_configs")
            os.makedirs(configs_dir, exist_ok=True)

            default_name = values.get("printer_name", "printer_config").replace(" ", "_")
            file_path = fd.asksaveasfilename(
            parent=self.root,
            initialdir=configs_dir,
            initialfile=f"{default_name}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save printer configuration as..."
            )

            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(values, f, indent=4)
                # Also update the canonical file used by the existing Load Configuration button
                try:
                    with open("printer_config.json", "w", encoding="utf-8") as f:
                        json.dump(values, f, indent=4)
                except Exception:
                    # non-fatal: keep the user file even if canonical update fails
                    pass

            messagebox.showinfo("Saved", f"Configuration saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            return
        
        # Display summary
        summary = "Configuration ready to apply:\n\n"
        for section_name, fields in self.config_fields.items():
            summary += f"{section_name}:\n"
            for label_text, field_key, _, _ in fields:
                if field_key in values:
                    summary += f"  • {label_text}: {values[field_key]}\n"
            summary += "\n"
        
        result = messagebox.askyesno("Apply Configuration", 
            summary + "Ready to apply these settings?")
        
        if result:
            messagebox.showinfo("Success", 
                "Configuration applied!\n\nYou can now run the printer_library_adjust.py script\n"
                "with these settings, or modify the printer_config.json file directly.")


if __name__ == "__main__":
    root = tk.Tk()
    gui = PrinterConfigGUI(root)
    root.mainloop()
