import requests
import sys
import os

if len(sys.argv) > 1:
    img_path = sys.argv[1]
else:
    img_path = r"c:/Users/abhis/Downloads/wolf-print-snow-prints-winter-wolves-animals-footprint-footprints-traces-tracks-X8BFPA.jpg"

print(f"Testing with: {img_path}")
try:
    with open(img_path, "rb") as f:
        r = requests.post("http://localhost:8000/predict", 
                        files={"file": (os.path.basename(img_path), f, "image/jpeg")}, 
                        timeout=30)
        
    print(f"Status Code: {r.status_code}")
    if r.status_code != 200:
        print("Response:", r.text[:500])
    else:
        # Print species and raw probabilities
        res = r.json()
        print(f"Predicted Species: {res.get('species')}")
        print(f"Confidence: {res.get('confidence')}")
        print("Raw Probabilities:")
        if 'raw_probabilities' in res:
            for k, v in res['raw_probabilities'].items():
                print(f"  {k}: {v:.4f}")
        elif 'probabilities' in res:
            for k, v in res['probabilities'].items():
                print(f"  {k}: {v:.4f}")
        else:
            print("  (not returned)")
except Exception as e:
    print(f"Request failed: {e}")
