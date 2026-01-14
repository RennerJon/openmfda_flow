import os
import shutil
import pathlib

def clean_project():
    """
    Cleans the OpenMFDA project by removing temporary files, caches, and build artifacts.
    """
    root_dir = pathlib.Path(__file__).parent.parent
    
    print(f"Cleaning project at: {root_dir}")

    # Directories to remove
    dirs_to_remove = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "build",
        "dist",
        *([".venv"] if input("Remove .venv? (y/N): ").lower() == "y" else []),
    ]
    
    # Patterns to remove
    patterns_to_remove = [
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        "*.log",
    ]

    for root, dirs, files in os.walk(root_dir):
        # Remove directories
        for d in dirs:
            if d in dirs_to_remove or d == "__pycache__":
                dir_path = os.path.join(root, d)
                print(f"Removing directory: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)

        # Remove files
        for f in files:
            for pattern in patterns_to_remove:
                if pathlib.PurePath(f).match(pattern):
                    file_path = os.path.join(root, f)
                    print(f"Removing file: {file_path}")
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"Error deleting {file_path}: {e}")

    print("Cleanup complete.")

if __name__ == "__main__":
    clean_project()
