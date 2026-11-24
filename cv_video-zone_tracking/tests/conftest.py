import os
import sys

# Ensure project root and src are in sys.path for test discovery and execution
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(root_dir, "src")

for p in [root_dir, src_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)
