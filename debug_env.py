import sys
import os
print("Python Executable:", sys.executable)
print("Sys Path:", sys.path)
try:
    import lark
    print("Lark imported successfully:", lark.__file__)
except ImportError as e:
    print("Failed to import lark:", e)
