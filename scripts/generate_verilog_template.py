import os
import argparse

def generate_verilog_ams_template(module_name, ports, output_dir="."):
    """
    Generates a basic Verilog-AMS template for a microfluidic component.
    
    Args:
        module_name (str): The name of the module.
        ports (list): A list of port names (strings).
        output_dir (str): Directory where the file should be saved.
    """
    
    filename = os.path.join(output_dir, f"{module_name}.vams")
    
    # Basic header and include
    content = [
        '`include "disciplines.vams"',
        '',
        f'module {module_name} ({", ".join(ports)});',
        '    // Define electrical/fluidic disciplines for ports'
    ]
    
    # Define ports as electrical/fluidic (defaulting to electrical for generic template, 
    # but strictly in MFDA check for fluid dynamic nature)
    for port in ports:
        content.append(f'    inout {port};')
        content.append(f'    electrical {port}; // Change to fluidic if using custom natures')
    
    content.append('')
    content.append('    // Parameters')
    content.append('    parameter real resistance = 1.0 from (0:inf);')
    content.append('')
    content.append('    // Behavior')
    content.append('    analog begin')
    content.append('        // Creating a simple resistive relationship between first two ports as example')
    if len(ports) >= 2:
         content.append(f'        I({ports[0]}, {ports[1]}) <+ V({ports[0]}, {ports[1]}) / resistance;')
    else:
         content.append('        // Add equations here')
    
    content.append('    end')
    content.append('endmodule')
    
    with open(filename, 'w') as f:
        f.write('\n'.join(content))
    
    print(f"Generated Verilog-AMS template at: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Verilog-AMS template.")
    parser.add_argument("name", help="Module name")
    parser.add_argument("ports", nargs='+', help="List of port names")
    parser.add_argument("--dir", default=".", help="Output directory")
    
    args = parser.parse_args()
    
    generate_verilog_ams_template(args.name, args.ports, args.dir)
