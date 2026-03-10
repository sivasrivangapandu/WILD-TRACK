import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
import json

model_path = r"d:\Wild Track AI\backend\models\wildtrack_complete_model.h5"
try:
    model = tf.keras.models.load_model(model_path, compile=False)
    print(f"Model Name: {model.name}")
    # Inspect first few layers to find the backbone
    for layer in model.layers[:5]:
        print(f" - Layer: {layer.name} ({layer.__class__.__name__})")
        if hasattr(layer, 'layers'): # If it's a functional model with a base_model layer
             print(f"   Sub-layers of {layer.name}:")
             for sub in layer.layers[:3]:
                 print(f"     * {sub.name}")

    # Check for MobileNet specific layers
    is_mobilenet = any('mobilenet' in l.name.lower() for l in model.layers)
    is_efficientnet = any('efficientnet' in l.name.lower() for l in model.layers)
    
    print(f"\nDetection: is_mobilenet={is_mobilenet}, is_efficientnet={is_efficientnet}")
except Exception as e:
    print(f"Error: {e}")
