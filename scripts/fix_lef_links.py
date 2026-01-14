
import os
import shutil
import sys

def find_file_in_pdk(pdk_root, filename):
    """Recursively search for a file in the PDK directory."""
    for root, dirs, files in os.walk(pdk_root):
        if filename in files:
            return os.path.join(root, filename)
    return None

def fix_lef_links(platforms_dir):
    """Fix LEF links in all platforms."""
    if not os.path.exists(platforms_dir):
        print(f"Error: Platforms directory '{platforms_dir}' not found.")
        return

    print(f"Scanning platforms in: {platforms_dir}")
    
    platforms = [d for d in os.listdir(platforms_dir) if os.path.isdir(os.path.join(platforms_dir, d))]
    
    for platform in platforms:
        platform_path = os.path.join(platforms_dir, platform)
        lef_dir = os.path.join(platform_path, "lef")
        pdk_dir = os.path.join(platform_path, "pdk")
        
        if not os.path.exists(lef_dir):
            continue
            
        print(f"\nChecking platform: {platform}")
        
        for f in os.listdir(lef_dir):
            if not f.endswith(".lef"):
                continue
                
            file_path = os.path.join(lef_dir, f)
            
            # Check if it is a symlink or if it doesn't exist (broken link looks like 'exists' returns False but 'islink' returns True)
            is_link = os.path.islink(file_path)
            exists = os.path.exists(file_path)
            
            # We want to replace symlinks (even valid ones, to be Docker-safe) and broken links
            if is_link or not exists:
                if is_link:
                    target = os.readlink(file_path)
                    print(f"  Found symlink: {f} -> {target}")
                    if exists:
                        print("    (Link is valid, but replacing with hard copy for Docker safety)")
                    else:
                        print("    (Link is BROKEN)")
                else:
                    print(f"  Found missing/broken file: {f}")

                # Find the source file
                source_path = find_file_in_pdk(pdk_dir, f)
                
                if source_path:
                    print(f"    Found source at: {source_path}")
                    try:
                        if os.path.lexists(file_path):
                            os.remove(file_path)
                        shutil.copy2(source_path, file_path)
                        print(f"    FIXED: Replaced with hard copy.")
                    except Exception as e:
                        print(f"    ERROR: Failed to copy file: {e}")
                else:
                    print(f"    ERROR: Could not find '{f}' in {pdk_dir}")
            else:
                 print(f"  OK: {f} is a regular file.")

if __name__ == "__main__":
    # Assuming this script is in scripts/ or tools/ folder move up to root
    # Adjust based on where script is located. 
    # Current plan: scripts/fix_lef_links.py -> root is ..
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    platforms_dir = os.path.join(root_dir, "flow", "platforms")
    
    fix_lef_links(platforms_dir)
