import requests, numpy as np, cv2, io

img = np.full((500, 500, 4), 255, dtype=np.uint8) # 4 channels for PNG (RGBA)
is_success, buffer = cv2.imencode(".png", img)
io_buf = io.BytesIO(buffer)

print("Sending request to /predict...")
r = requests.post("http://localhost:8000/predict", files={"file": ("diagram.png", io_buf, "image/png")})
print("Status Code:", r.status_code)
if r.status_code != 200:
    print("Error:", r.text)
else:
    print("Response keys:", r.json().keys())
