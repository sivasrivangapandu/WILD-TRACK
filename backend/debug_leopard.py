import requests
import os

img_path = r"D:\footprints-clouded-leopards-267320709.webp"
print(f"Testing with: {img_path}")
try:
    with open(img_path, "rb") as f:
        r = requests.post("http://localhost:8000/predict", 
                        files={"file": (os.path.basename(img_path), f, "image/webp")}, 
                        timeout=30)
        
    print(f"Status Code: {r.status_code}")
    if r.status_code != 200:
        print("Response:", r.text[:500])
    else:
        print("Keys:", r.json().keys())
        print("Species:", r.json().get('species'))
except Exception as e:
    print(f"Request failed: {e}")
