import requests
import json
import os

base = 'http://localhost:8000'
print('=' * 60)
print('WILDTRACK AI - COMPREHENSIVE SYSTEM TEST')
print('=' * 60)

tests_passed = 0
tests_failed = 0

# Test 1: Health Check
try:
    r = requests.get(f'{base}/health', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f'\n✅ Health Check: {r.status_code}')
        print(f'   Status: {data.get("status")}')
        print(f'   Model Loaded: {data.get("model_loaded")}')
        print(f'   GradCAM: {data.get("gradcam_available")}')
        print(f'   Classes: {data.get("classes")}')
        tests_passed += 1
    else:
        print(f'\n❌ Health Check: {r.status_code}')
        tests_failed += 1
except Exception as e:
    print(f'\n❌ Health Check: {e}')
    tests_failed += 1

# Test 2: System Status
try:
    r = requests.get(f'{base}/api/system/status', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f'\n✅ System Status: {r.status_code}')
        print(f'   Model: {data.get("model_name")} {data.get("model_version")}')
        print(f'   Architecture: {data.get("architecture")}')
        acc = data.get("validation_accuracy", 0)
        print(f'   Accuracy: {acc:.1%}')
        print(f'   TTA: {data.get("tta_enabled")} ({data.get("tta_passes")} passes)')
        print(f'   Uptime: {data.get("uptime")}')
        tests_passed += 1
    else:
        print(f'\n❌ System Status: {r.status_code}')
        tests_failed += 1
except Exception as e:
    print(f'\n❌ System Status: {e}')
    tests_failed += 1

# Test 3: Species List
try:
    r = requests.get(f'{base}/species', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f'\n✅ Species List: {r.status_code}')
        print(f'   Total Species: {data.get("total")}')
        species_names = [s.get("name") for s in data.get("species", [])]
        print(f'   Classes: {species_names}')
        tests_passed += 1
    else:
        print(f'\n❌ Species List: {r.status_code}')
        tests_failed += 1
except Exception as e:
    print(f'\n❌ Species List: {e}')
    tests_failed += 1

# Test 4: Model Metrics
try:
    r = requests.get(f'{base}/model-metrics', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f'\n✅ Model Metrics: {r.status_code}')
        print(f'   Precision: {data.get("precision", 0):.3f}')
        print(f'   Recall: {data.get("recall", 0):.3f}')
        print(f'   F1 Score: {data.get("f1_score", 0):.3f}')
        tests_passed += 1
    else:
        print(f'\n❌ Model Metrics: {r.status_code}')
        tests_failed += 1
except Exception as e:
    print(f'\n❌ Model Metrics: {e}')
    tests_failed += 1

# Test 5: History
try:
    r = requests.get(f'{base}/history?limit=5', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f'\n✅ History: {r.status_code}')
        print(f'   Total Predictions: {data.get("total")}')
        tests_passed += 1
    else:
        print(f'\n❌ History: {r.status_code}')
        tests_failed += 1
except Exception as e:
    print(f'\n❌ History: {e}')
    tests_failed += 1

# Test 6: Analytics
try:
    r = requests.get(f'{base}/analytics', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f'\n✅ Analytics: {r.status_code}')
        print(f'   Total Predictions: {data.get("total_predictions")}')
        avg = data.get("avg_confidence", 0)
        print(f'   Avg Confidence: {avg:.1%}')
        tests_passed += 1
    else:
        print(f'\n❌ Analytics: {r.status_code}')
        tests_failed += 1
except Exception as e:
    print(f'\n❌ Analytics: {e}')
    tests_failed += 1

print('\n' + '=' * 60)
print(f'CORE ENDPOINTS: {tests_passed}/6 PASSED')
print('=' * 60)

# Test 7: API Ninjas Integration
print('\n' + '=' * 60)
print('API NINJAS INTEGRATION TEST')
print('=' * 60)

api_tests_passed = 0
api_tests_failed = 0

# Test Lion
try:
    r = requests.get(f'{base}/api/animal-info?name=lion', timeout=5)
    if r.status_code == 200:
        data = r.json()
        if data.get("found"):
            animal = data.get("animal", {})
            print(f'\n✅ Lion Search: {r.status_code}')
            print(f'   Name: {animal.get("name")}')
            print(f'   Diet: {animal.get("diet")}')
            print(f'   Habitat: {animal.get("habitat")}')
            print(f'   Weight: {animal.get("weight")}')
            api_tests_passed += 1
        else:
            print(f'\n❌ Lion Search: No data found')
            api_tests_failed += 1
    else:
        print(f'\n❌ Lion Search: {r.status_code}')
        api_tests_failed += 1
except Exception as e:
    print(f'\n❌ Lion Search: {e}')
    api_tests_failed += 1

# Test Elephant
try:
    r = requests.get(f'{base}/api/animal-info?name=elephant', timeout=5)
    if r.status_code == 200:
        data = r.json()
        if data.get("found"):
            animal = data.get("animal", {})
            print(f'\n✅ Elephant Search: {r.status_code}')
            print(f'   Name: {animal.get("name")}')
            print(f'   Diet: {animal.get("diet")}')
            print(f'   Weight: {animal.get("weight")}')
            api_tests_passed += 1
        else:
            print(f'\n❌ Elephant Search: No data found')
            api_tests_failed += 1
    else:
        print(f'\n❌ Elephant Search: {r.status_code}')
        api_tests_failed += 1
except Exception as e:
    print(f'\n❌ Elephant Search: {e}')
    api_tests_failed += 1

# Test Wolf
try:
    r = requests.get(f'{base}/api/animal-info?name=wolf', timeout=5)
    if r.status_code == 200:
        data = r.json()
        if data.get("found"):
            animal = data.get("animal", {})
            print(f'\n✅ Wolf Search: {r.status_code}')
            print(f'   Name: {animal.get("name")}')
            print(f'   Type: {animal.get("type")}')
            api_tests_passed += 1
        else:
            print(f'\n❌ Wolf Search: No data found')
            api_tests_failed += 1
    else:
        print(f'\n❌ Wolf Search: {r.status_code}')
        api_tests_failed += 1
except Exception as e:
    print(f'\n❌ Wolf Search: {e}')
    api_tests_failed += 1

print('\n' + '=' * 60)
print(f'API NINJAS: {api_tests_passed}/3 PASSED')
print('=' * 60)

# Test 8: Prediction with real image
print('\n' + '=' * 60)
print('PREDICTION TEST')
print('=' * 60)

pred_passed = 0
pred_failed = 0

test_images = [
    'backend/dataset_quarantine_r2/tiger/000003.jpg',
    'backend/dataset_quarantine_r2/wolf/000015.jpg',
]

for img_path in test_images:
    if os.path.exists(img_path):
        try:
            with open(img_path, 'rb') as f:
                r = requests.post(f'{base}/predict', files={'file': f}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    species = data.get('species')
                    conf = data.get('confidence', 0)
                    print(f'\n✅ Predict {os.path.basename(img_path)}: {r.status_code}')
                    print(f'   Species: {species}')
                    print(f'   Confidence: {conf:.1%}')
                    has_heatmap = "Yes" if data.get("heatmap") else "No"
                    print(f'   Heatmap: {has_heatmap}')
                    pred_passed += 1
                else:
                    print(f'\n❌ Predict {os.path.basename(img_path)}: {r.status_code}')
                    pred_failed += 1
        except Exception as e:
            print(f'\n❌ Predict {os.path.basename(img_path)}: {e}')
            pred_failed += 1
    else:
        print(f'\n⚠️  Image not found: {img_path}')

print('\n' + '=' * 60)
print(f'PREDICTION: {pred_passed}/{len(test_images)} PASSED')
print('=' * 60)

# Final Summary
print('\n' + '=' * 60)
print('FINAL SUMMARY')
print('=' * 60)
total_passed = tests_passed + api_tests_passed + pred_passed
total_tests = 6 + 3 + len(test_images)
print(f'\nTotal Tests Passed: {total_passed}/{total_tests}')
print(f'Success Rate: {total_passed/total_tests*100:.1f}%')

if total_passed == total_tests:
    print('\n🎉 ALL SYSTEMS OPERATIONAL!')
else:
    print(f'\n⚠️  {total_tests - total_passed} test(s) failed')

print('=' * 60)
