#!/usr/bin/env python
import sys
import time

print("1. Starting diagnostic...")
t0 = time.time()

try:
    print("2. Importing database...")
    from database import init_db, get_db
    print(f"   ✓ Done in {time.time()-t0:.2f}s")

    print("3. Importing config...")
    from config import *
    print(f"   ✓ Done in {time.time()-t0:.2f}s")

    print("4. Importing FastAPI...")
    from fastapi import FastAPI
    print(f"   ✓ Done in {time.time()-t0:.2f}s")
    
    print("5. All critical imports OK!")
    print(f"Total: {time.time()-t0:.2f}s")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
