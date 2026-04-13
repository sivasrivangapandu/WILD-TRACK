#!/usr/bin/env python
import sys
import time

print("Testing main.py import...")
t0 = time.time()

try:
    print("Importing main app...")
    from main import app
    print(f"✓ Success! Took {time.time()-t0:.2f}s")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    print(f"Total time: {time.time()-t0:.2f}s")
