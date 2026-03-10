"""
Rebuild MobileNetV2 model from architecture + weights.

The .h5 full-model files contain a TrueDivide layer from Keras 3.x
preprocess_input() which is not portable across TF versions.

Fix: rebuild the architecture using a Lambda layer for preprocessing,
load the checkpoint weights, and re-save cleanly.
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

IMG_SIZE = 160
NUM_CLASSES = 5
WEIGHTS_PATH = 'backend/models/checkpoint_best.weights.h5'

print(f'TF version: {tf.__version__}')

# ---- Custom preprocessing layer (safe serialization, no Lambda) ----
@keras.utils.register_keras_serializable(package='WildTrackAI')
class MobileNetPreprocess(layers.Layer):
    """MobileNetV2 preprocessing: scale [0,255] -> [-1,1]."""
    def call(self, x):
        x = tf.cast(x, tf.float32)
        return (x / 127.5) - 1.0

# ---- Rebuild architecture (matches train_cpu.py) ----
base = keras.applications.MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False,
    weights='imagenet',
)
# Unfreeze top 50 layers (matches Phase 2 training state)
base.trainable = True
for layer in base.layers[:-50]:
    layer.trainable = False

inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
# Use registered custom layer instead of Lambda to avoid serialization issues
x = MobileNetPreprocess(name='preprocess')(inputs)
x = base(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
x = layers.Dense(128, activation='relu')(x)
x = layers.Dropout(0.2)(x)
outputs = layers.Dense(NUM_CLASSES, activation='softmax')(x)

model = keras.Model(inputs, outputs, name='WildTrackAI_MobileNetV2')
print(f'Architecture rebuilt: {model.count_params():,} params')

# ---- Load trained weights ----
print(f'Loading weights from {WEIGHTS_PATH}...')
model.load_weights(WEIGHTS_PATH)
print('Weights loaded successfully')

# ---- Quick sanity check ----
dummy = np.random.randint(0, 255, (1, IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
pred = model.predict(dummy, verbose=0)
print(f'Sanity check prediction shape: {pred.shape}, sum: {pred.sum():.4f}')

# ---- Save in multiple formats ----
# 1. Native .keras format (primary - best portability)
keras_path = 'backend/models/wildtrack_v4_cpu.keras'
model.save(keras_path)
print(f'Saved .keras: {os.path.getsize(keras_path)/1024/1024:.1f} MB -> {keras_path}')

# 2. Full model .h5 (legacy, needs safe_mode=False on load)
h5_path = 'backend/models/wildtrack_complete_model.h5'
model.save(h5_path)
print(f'Saved .h5: {os.path.getsize(h5_path)/1024/1024:.1f} MB -> {h5_path}')

# 3. Copy as wildtrack_final.h5
import shutil
final_path = 'backend/models/wildtrack_final.h5'
shutil.copy2(h5_path, final_path)
print(f'Copied -> {final_path}')

# 4. Copy as wildtrack_v4.h5
v4_path = 'backend/models/wildtrack_v4.h5'
shutil.copy2(h5_path, v4_path)
print(f'Copied -> {v4_path}')

# 5. Verify the .keras model loads cleanly
print('Verifying .keras model loads...')
m2 = keras.models.load_model(keras_path, compile=False)
pred2 = m2.predict(dummy, verbose=0)
print(f'Reload check: shape={pred2.shape}, match={np.allclose(pred, pred2, atol=1e-5)}')

# 6. Verify .h5 loads with safe_mode=False
print('Verifying .h5 model loads (safe_mode=False)...')
m3 = keras.models.load_model(h5_path, compile=False, safe_mode=False)
pred3 = m3.predict(dummy, verbose=0)
print(f'h5 reload check: shape={pred3.shape}, match={np.allclose(pred, pred3, atol=1e-5)}')

print('DONE - All model files re-saved successfully')
