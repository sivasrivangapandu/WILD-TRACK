# 🎯 WildTrack AI - New API Endpoints Reference

## Quick Reference

### 1. Image Classification Endpoint
```
POST /classify-image
```

**Purpose**: Determine if image contains animal/human/thing/other

**Request**:
```bash
curl -X POST http://localhost:8000/classify-image \
  -F "file=@image.jpg"
```

**Response**:
```json
{
  "success": true,
  "image_type": "animal",
  "confidence": 0.85,
  "method": "heuristic_analysis",
  "image_quality": 0.76,
  "quality_level": "Good",
  "detailed_scores": {
    "heuristic_analysis_type": "animal",
    "heuristic_confidence": 0.85
  }
}
```

**Image Types Returned**:
- `animal` - Photos containing animals or animal body parts
- `human` - Photos containing people or faces
- `thing` - Photos containing objects, vehicles, buildings
- `other` - Landscapes, plants, water, sky, unknown

---

### 2. Enhanced Prediction Endpoint  
```
POST /predict/enhanced
```

**Purpose**: Predict animal species with confidence filtering and quality assessment

**Request**:
```bash
curl -X POST http://localhost:8000/predict/enhanced \
  -F "file=@footprint.jpg" \
  -F "latitude=12.34" \
  -F "longitude=56.78"
```

**Response**:
```json
{
  "success": true,
  "prediction": {
    "class": "leopard",
    "confidence": 0.924,
    "confidence_level": "High",
    "meets_threshold": true
  },
  "image_analysis": {
    "type": "animal",
    "type_confidence": 0.85,
    "quality_score": 0.76,
    "quality_level": "Good"
  },
  "top_predictions": [
    {
      "class": "leopard",
      "confidence": 0.924,
      "rank": 1
    },
    {
      "class": "tiger",
      "confidence": 0.052,
      "rank": 2
    },
    {
      "class": "elephant",
      "confidence": 0.018,
      "rank": 3
    }
  ],
  "metadata": {
    "total_alternatives": 5,
    "quality_metrics": {
      "sharpness": 0.72,
      "brightness": 128,
      "blur_level": 45
    },
    "stage1_meta": {}
  }
}
```

**Confidence Levels**:
- `"Very High"` - confidence > 0.80 → Trust this prediction
- `"High"` - confidence > 0.60 → Likely correct
- `"Medium"` - confidence > 0.40 → Possible but verify
- `"Low"` - confidence ≤ 0.40 → Uncertain, probably wrong

**Image Quality Levels**:
- `"Excellent"` - quality > 0.80
- `"Good"` - quality > 0.60
- `"Fair"` - quality > 0.40
- `"Poor"` - quality ≤ 0.40

**Quality Metrics for Upload Image**:
- `sharpness` - Edge definition (0-1)
- `brightness` - Average pixel value (0-255)
- `blur_level` - Blurriness detection (0-100)

---

### 3. Original Prediction Endpoint (Still Works!)
```
POST /predict
```

**Purpose**: Basic prediction (unchanged for backward compatibility)

**Request**:
```bash
curl -X POST http://localhost:8000/predict \
  -F "file=@footprint.jpg"
```

**Response**: Same as before, includes all confidence and species info

---

## Use Cases

### Use Case 1: Filter Out Non-Animal Images
```bash
# Check what type of image user uploaded
POST /classify-image

if image_type == "animal" {
  # Proceed with prediction
  POST /predict/enhanced
} else {
  # Show user: "Please upload animal photos"
}
```

### Use Case 2: High Confidence Predictions Only
```bash
POST /predict/enhanced

if meets_threshold && confidence > 0.7 {
  # Display result with confidence
  Show: "Detected leopard with very high confidence"
} else {
  # Ask user to improve photo
  Show: "Image quality low - try different angle/lighting"
}
```

### Use Case 3: Show Image Quality to User
```bash
POST /predict/enhanced

# Display to user:
Image Quality: [████░░░░░░] Good (0.76)
Confidence: [██████░░░░] High (0.92)
Prediction: Leopard

# Suggestions if quality low:
- Improve lighting
- Get closer to animal track  
- Use steady camera
- Avoid shadows and glare
```

### Use Case 4: Rejection Logic
```bash
POST /classify-image

if image_type != "animal" {
  REJECT with: "This doesn't look like an animal track/footprint"
}

POST /predict/enhanced

if !meets_threshold {
  SUGGEST: "Image quality low. Try: better lighting, steady hand, close-up"
}
```

---

## Response Codes

### Success (2xx)
- `200 OK` - Prediction successful
- `200 OK` - Classification successful

### Client Errors (4xx)
- `400 Bad Request` - Invalid image format
- `422 Unprocessable Entity` - Not a footprint/invalid image
- `404 Not Found` - Image doesn't contain expected content

### Server Errors (5xx)
- `503 Service Unavailable` - Model not loaded yet
- `500 Internal Server Error` - Unexpected error

---

## Integration Examples

### Python
```python
import requests

# Classify image
response = requests.post(
    "http://localhost:8000/classify-image",
    files={"file": open("image.jpg", "rb")}
)
data = response.json()
print(f"Image type: {data['image_type']}")
print(f"Quality: {data['image_quality']}")

# Get enhanced prediction
response = requests.post(
    "http://localhost:8000/predict/enhanced",
    files={"file": open("footprint.jpg", "rb")},
    data={"latitude": 12.34, "longitude": 56.78}
)
result = response.json()
print(f"Detected: {result['prediction']['class']}")
print(f"Confidence: {result['prediction']['confidence']}")
```

### JavaScript/React
```javascript
// Classify image
const formData = new FormData();
formData.append('file', imageFile);

const response = await fetch('/api/classify-image', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log(`Image type: ${data.image_type}`);
console.log(`Quality: ${data.image_quality}`);

// Enhanced prediction
const response2 = await fetch('/api/predict/enhanced', {
  method: 'POST',
  body: formData
});

const result = await response2.json();
console.log(`Detected: ${result.prediction.class}`);
console.log(`Confidence: ${result.prediction.confidence}`);
```

### cURL Examples
```bash
# Test classification endpoint
curl -X POST http://localhost:8000/classify-image \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.jpg" \
  -s | jq .

# Test enhanced prediction
curl -X POST http://localhost:8000/predict/enhanced \
  -H "Content-Type: multipart/form-data" \
  -F "file=@footprint.jpg" \
  -F "latitude=12.34" \
  -F "longitude=56.78" \
  -s | jq .

# Check endpoint availability
curl -i http://localhost:8000/health
```

---

## Performance Characteristics

### Latency (Approximate)
- `/classify-image`: 200-300ms
- `/predict/enhanced`: 800ms-1.2s (includes model inference)
- `/predict`: 800ms-1.2s

### Throughput
- Max 2-4 concurrent requests per instance
- Queue excess requests
- Render handles auto-scaling

### Limitations
- Max image size: 50MB
- Max batch size: 20 images
- Max request timeout: 120 seconds

---

## Error Handling

### Example Error Response
```json
{
  "detail": "❌ **Not a Footprint Detected**\n\nThis image does not appear to contain an animal footprint..."
}
```

### How to Handle
```python
if response.status_code != 200:
    error_msg = response.json().get('detail')
    # Clean and display to user
    print(f"Error: {error_msg}")
    # Suggest user improvement
else:
    result = response.json()
    # Process successful prediction
```

---

## Configuration

### Confidence Thresholds
Set in `backend/services/enhanced_prediction.py`:
```python
THRESHOLDS = {
    "animal": 0.4,      # Minimum confidence for animal predictions
    "human": 0.3,       # Minimum confidence for human predictions  
    "thing": 0.35,      # Minimum confidence for object predictions
    "other": 0.3        # Minimum confidence for unknown
}
```

### Adjust Image Quality Weights
In `PredictionEnhancer.calculate_image_quality()`:
```python
quality = (
    sharpness_score * 0.4 +   # 40% weight on sharpness
    brightness_score * 0.3 +  # 30% weight on brightness
    contrast_score * 0.3      # 30% weight on contrast
)
```

---

## Troubleshooting

### "404 Not Found" Error
- Backend service may still be deploying
- Wait 2-5 minutes for Render deployment
- Check: https://dashboard.render.com/services/wildtrack-backend-s3lq

### Low Confidence Scores
- Image quality may be poor
- Check `image_quality` field
- Suggest user improve photo quality
- Verify it's actually an animal footprint

### Image Type Detection Failing
- Image is ambiguous or mixed content
- May contain both animal and human elements
- Falls back to text-based analysis
- Manual review recommended

### Timeout Errors
- Image file too large (>50MB)
- Network connectivity issue
- Backend overloaded (queue request)
- Check Render service status

---

## Monitoring & Debugging

### Check Service Health
```bash
curl http://localhost:8000/health | jq .
```

Response includes:
- `model_loaded` - Is ML model ready?
- `uptime_seconds` - How long running?
- `gradcam_available` - Is visualization ready?

### Run Diagnostics
```bash
python diagnostic_fix.py
```

This tests:
- Backend connectivity
- Model loading
- Endpoint availability
- Prediction accuracy
- Suggests fixes if issues found

---

## API Versioning

All endpoints are v1 (no version prefix).

Future endpoints will be:
- `/api/v2/classify-image`
- `/api/v2/predict/enhanced`

For now, use:
- `/classify-image` (current)
- `/predict/enhanced` (current)

---

## Need Help?

- **API Issues**: Check response JSON for `detail` field
- **Image Quality**: Upload clearer, well-lit photos
- **Confidence Low**: Try `/classify-image` first to verify image type
- **Server Down**: Monitor https://dashboard.render.com/services/wildtrack-backend-s3lq

---

**Last Updated**: April 15, 2026  
**API Version**: 1.0  
**Status**: ✅ Deployed
