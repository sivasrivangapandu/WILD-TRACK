"""
Test Level 4 Gatekeeper - Verify it rejects screenshots and non-footprints
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from main import _local_footprint_check
import cv2
import numpy as np
from PIL import Image
import io

def numpy_to_pil(arr):
    """Convert numpy array to PIL Image"""
    arr_uint8 = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(cv2.cvtColor(arr_uint8, cv2.COLOR_BGR2RGB))

def test_screenshot_rejection():
    """Test that screenshots are rejected"""
    print("\n✓ TEST: Level 4 Gatekeeper Screenshot Detection")
    print("=" * 60)
    
    # Create a mock screenshot-like image
    # (high uniformity, regular patterns, many straight lines)
    img = np.ones((400, 600, 3), dtype=np.uint8)
    
    # Add UI-like elements (uniform color blocks = buttons)
    img[50:100, 100:200] = [200, 100, 100]  # Red button
    img[50:100, 250:350] = [100, 200, 100]  # Green button
    img[120:200, 100:500] = [150, 150, 150]  # Gray panel
    img[250:350, 100:500] = [200, 200, 200]  # Text area
    
    # Add text-like patterns (horizontal lines)
    for y in [260, 280, 300, 320]:
        img[y:y+2, 150:450] = [100, 100, 100]
    
    # Convert to PIL and then to cv2 format for validation
    pil_img = numpy_to_pil(img)
    img_cv2 = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    valid, msg = _local_footprint_check(img_cv2)
    
    print(f"Input: Screenshot-like (UI elements, uniform blocks)")
    print(f"Result: {'✅ REJECTED' if not valid else '❌ ACCEPTED (FAILED)'}")
    print(f"Message: {msg}")
    print(f"Status: {'PASS ✓' if not valid else 'FAIL ✗'}")
    
    return not valid

def test_natural_footprint_acceptance():
    """Test that real footprint-like images are accepted"""
    print("\n✓ TEST: Level 4 Gatekeeper Natural Footprint Detection")
    print("=" * 60)
    
    # Create a natural-looking image with organic shapes
    img = np.full((500, 500, 3), fill_value=180, dtype=np.uint8)
    
    # Add realistic texture (varied grayscale values)
    noise = np.random.randint(0, 50, (500, 500, 3), dtype=np.uint8)
    img = np.clip(img.astype(int) + noise.astype(int), 0, 255).astype(np.uint8)
    
    # Add an organic footprint-like shape (irregular edges, not geometric)
    # Create a circular-ish blob with irregular edges
    center_y, center_x = 250, 250
    
    for y in range(200, 300):
        for x in range(200, 300):
            dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            # Irregular circle (not perfect)
            radius = 60 + np.random.randint(-15, 15)
            if dist < radius:
                img[y, x] = [100, 80, 70]  # Dark brown (footprint color)
    
    # Convert to proper format
    pil_img = numpy_to_pil(img)
    img_cv2 = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    valid, msg = _local_footprint_check(img_cv2)
    
    print(f"Input: Natural-looking footprint (organic shapes, texture)")
    print(f"Result: {'✅ ACCEPTED' if valid else '❌ REJECTED (FAILED)'}")
    print(f"Message: {msg}")
    print(f"Status: {'PASS ✓' if valid else 'FAIL ✗'}")
    
    return valid

def test_ui_dialog_rejection():
    """Test that UI dialogs/windows are rejected"""
    print("\n✓ TEST: Level 4 Gatekeeper UI Dialog Detection")
    print("=" * 60)
    
    # Create UI dialog-like image
    img = np.full((600, 800, 3), fill_value=200, dtype=np.uint8)  # Light background
    
    # Add dialog box (perfect rectangles)
    img[150:500, 200:600] = [240, 240, 240]  # Dialog background
    
    # Add title bar (uniform color block)
    img[150:180, 200:600] = [52, 152, 219]  # Blue title bar
    
    # Add buttons (perfect rectangles)
    img[450:490, 250:350] = [100, 100, 100]  # Cancel button
    img[450:490, 400:500] = [76, 175, 80]   # OK button
    
    # Add text lines (horizontal patterns)
    for y in range(220, 420, 30):
        img[y:y+1, 250:550] = [50, 50, 50]
    
    # Convert to proper format
    pil_img = numpy_to_pil(img)
    img_cv2 = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    valid, msg = _local_footprint_check(img_cv2)
    
    print(f"Input: UI Dialog (rectangles, uniform blocks, regular patterns)")
    print(f"Result: {'✅ REJECTED' if not valid else '❌ ACCEPTED (FAILED)'}")
    print(f"Message: {msg}")
    print(f"Status: {'PASS ✓' if not valid else 'FAIL ✗'}")
    
    return not valid

if __name__ == "__main__":
    print("\n🔒 WILDTRACK AI - LEVEL 4 GATEKEEPER TEST SUITE")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Screenshot Rejection", test_screenshot_rejection()))
        results.append(("Natural Footprint", test_natural_footprint_acceptance()))
        results.append(("UI Dialog Rejection", test_ui_dialog_rejection()))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 ALL TESTS PASSED - LEVEL 4 GATEKEEPER WORKING!" if all_passed else "⚠️ SOME TESTS FAILED"))
