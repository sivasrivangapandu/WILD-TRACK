"""Test PDF report endpoint."""
import requests, os

dataset = 'dataset_cleaned'
deer_dir = os.path.join(dataset, 'deer')
img = os.path.join(deer_dir, os.listdir(deer_dir)[0])

with open(img, 'rb') as f:
    r = requests.post('http://localhost:8000/report', files={'file': (os.path.basename(img), f, 'image/jpeg')})

print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('content-type', 'none')}")
print(f"Content-Length: {len(r.content)} bytes")

if r.status_code == 200:
    with open('test_report.pdf', 'wb') as out:
        out.write(r.content)
    print("PDF saved as test_report.pdf")
else:
    print(f"Error: {r.text[:300]}")
