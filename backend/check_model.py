import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

model_path = r"d:\Wild Track AI\backend\models\wildtrack_complete_model.h5"
try:
    model = tf.keras.models.load_model(model_path, compile=False)
    print("Model Layers:")
    for layer in model.layers:
        print(f" - {layer.name}: {layer.__class__.__name__}")
        if 'rescaling' in layer.name.lower() or 'normalization' in layer.name.lower():
            try:
                print(f"   Config: {layer.get_config()}")
            except:
                pass
except Exception as e:
    print(f"Error loading model: {e}")
