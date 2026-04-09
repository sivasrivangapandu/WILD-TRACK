"""Quick test: verify elephant predictions work after preprocessing fix."""
import requests, os, sys

dataset = os.path.join(os.getcwd(), "dataset_strict", "elephant")
if not os.path.isdir(dataset):
    dataset = os.path.join(os.getcwd(), "dataset", "elephant")
if not os.path.isdir(dataset):
    print("NO ELEPHANT DATASET FOUND")
    sys.exit(1)

imgs = [f for f in os.listdir(dataset) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
print(f"Found {len(imgs)} elephant images in {dataset}")

tested = 0
correct = 0
for img_name in imgs[:5]:
    img_path = os.path.join(dataset, img_name)
    with open(img_path, "rb") as f:
        r = requests.post("http://localhost:8000/predict", files={"file": (img_name, f, "image/jpeg")}, timeout=60)
    if r.status_code == 200:
        data = r.json()
        species = data.get("species", "?")
        conf = data.get("confidence", 0)
        top3_str = ", ".join([f"{t['class']}={t['confidence']*100:.1f}%" for t in data.get("top3", [])])
        is_correct = species == "elephant"
        tested += 1
        if is_correct:
            correct += 1
        status = "OK" if is_correct else "WRONG"
        print(f"  {img_name}: predicted={species} ({conf*100:.1f}%) top3=[{top3_str}] {status}")
    else:
        print(f"  {img_name}: ERROR {r.status_code}")

print(f"\nAccuracy: {correct}/{tested} ({correct/max(tested,1)*100:.0f}%)")
