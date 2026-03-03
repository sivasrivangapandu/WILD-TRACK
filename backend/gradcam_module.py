"""
WildTrackAI - Phase 4: Grad-CAM Explainable AI Module
======================================================
Automatically detects the last convolutional layer.
Generates heatmaps showing what the model "sees".
Returns overlaid heatmap as base64 for API responses.
Saves overlay images to output folder.

Usage:
    from gradcam_module import GradCAM
    
    gcam = GradCAM(model)
    heatmap_b64, overlay_path = gcam.generate(image_path)
"""

import os
import base64
import numpy as np
import cv2
import tensorflow as tf


class GradCAM:
    """Professional Grad-CAM implementation with auto layer detection."""

    def __init__(self, model, output_dir=None):
        """
        Args:
            model: Loaded Keras model
            output_dir: Directory to save overlay images (optional)
        """
        self.model = model
        self.output_dir = output_dir
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Find the base model (EfficientNet) and last conv layer
        self.base_model = None
        self.conv_layer_name = None
        self.feature_model = None
        self._setup()
        print(f"[GradCAM] Using layer: {self.conv_layer_name}")

    def _setup(self):
        """Find base model and last conv layer, identify head layers."""
        # Find the EfficientNet base model (nested Keras model)
        base_model_idx = None
        for i, layer in enumerate(self.model.layers):
            if isinstance(layer, tf.keras.Model):
                self.base_model = layer
                base_model_idx = i
                break

        if self.base_model is None:
            self.base_model = self.model

        # Find last Conv2D layer in the base model
        conv_layers = []
        for layer in self.base_model.layers:
            if isinstance(layer, tf.keras.layers.Conv2D):
                conv_layers.append(layer.name)
            elif 'conv' in layer.name.lower() and hasattr(layer, 'kernel'):
                conv_layers.append(layer.name)

        if not conv_layers:
            raise ValueError("No Conv2D layer found in model!")

        self.conv_layer_name = conv_layers[-1]

        # Collect the "head" layers (everything after the base model)
        if base_model_idx is not None:
            self.head_layers = self.model.layers[base_model_idx + 1:]
        else:
            self.head_layers = []

    def _compute_heatmap(self, img_array):
        """
        Compute Grad-CAM heatmap using GradientTape.
        Uses base model output → sequential head layers with proper handling
        of SE Attention Multiply (multi-input merge layer).
        """
        img_tensor = tf.cast(img_array, tf.float32)

        with tf.GradientTape() as tape:
            # Forward pass through base model to get spatial features
            conv_outputs = self.base_model(img_tensor, training=False)
            tape.watch(conv_outputs)

            # Forward through head layers, handling Multiply (SE Attention)
            x = conv_outputs
            gap_output = None  # Saved for SE Attention Multiply

            for layer in self.head_layers:
                if isinstance(layer, tf.keras.layers.GlobalAveragePooling2D):
                    x = layer(x)
                    gap_output = x  # Save features for Multiply
                elif isinstance(layer, (tf.keras.layers.Multiply,
                                        tf.keras.layers.Add,
                                        tf.keras.layers.Concatenate)):
                    # SE Attention: Multiply([original_features, attention_weights])
                    if gap_output is not None:
                        x = layer([gap_output, x])
                    else:
                        x = layer([x, x])
                else:
                    try:
                        x = layer(x, training=False)
                    except TypeError:
                        x = layer(x)

            predictions = x
            predicted_class = tf.argmax(predictions[0])
            class_output = predictions[:, predicted_class]

        # Compute gradients of the predicted class w.r.t. spatial features
        grads = tape.gradient(class_output, conv_outputs)

        if grads is None:
            print("[GradCAM] WARNING: Gradients are None. Returning blank heatmap.")
            return np.zeros((img_array.shape[1], img_array.shape[2]), dtype=np.float32)

        # Global average pooling of gradients
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Weight feature maps by gradients
        conv_out = conv_outputs[0]
        heatmap = tf.reduce_sum(conv_out * pooled_grads, axis=-1)

        # ReLU and normalize
        heatmap = tf.nn.relu(heatmap)
        heatmap = heatmap / (tf.reduce_max(heatmap) + 1e-8)
        return heatmap.numpy()

    def _overlay_heatmap(self, heatmap, base_img, h, w, confidence=None):
        """Create overlay of heatmap on base image.
        Reduces heatmap intensity for low-confidence predictions to show uncertainty.
        """
        heatmap_resized = cv2.resize(heatmap, (w, h))
        
        # Scale heatmap intensity based on prediction confidence
        # Low confidence = weaker heatmap overlay (shows model is unsure)
        if confidence is not None and confidence < 0.5:
            # Scale alpha from 0.15 (very low conf) to 0.4 (near threshold)
            alpha = max(0.15, confidence * 0.8)
        else:
            alpha = 0.4
        
        heatmap_uint8 = np.uint8(255 * heatmap_resized)
        heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(base_img, 1.0 - alpha, heatmap_colored, alpha, 0)

        # Add "LOW CONFIDENCE" watermark for uncertain predictions
        if confidence is not None and confidence < 0.5:
            font = cv2.FONT_HERSHEY_SIMPLEX
            text = "LOW CONFIDENCE"
            font_scale = max(0.4, min(w, h) / 600)
            thickness = max(1, int(font_scale * 2))
            (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
            # Semi-transparent overlay bar at top
            overlay_bar = overlay.copy()
            cv2.rectangle(overlay_bar, (0, 0), (w, th + 12), (0, 0, 0), -1)
            overlay = cv2.addWeighted(overlay, 0.7, overlay_bar, 0.3, 0)
            cv2.putText(overlay, text, (6, th + 6), font, font_scale, (0, 100, 255), thickness)

        _, buffer = cv2.imencode('.jpg', overlay, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return base64.b64encode(buffer).decode('utf-8')

    def generate(self, image_path, img_size=300, save_name=None, confidence=None):
        """
        Generate Grad-CAM heatmap for an image file.
        
        Args:
            image_path: Path to input image
            img_size: Model input size
            save_name: Optional filename for saving overlay
            confidence: Prediction confidence for adaptive overlay intensity
            
        Returns:
            tuple: (heatmap_base64, overlay_path or None)
        """
        original = cv2.imread(image_path)
        if original is None:
            raise ValueError(f"Cannot read image: {image_path}")

        img = cv2.resize(original, (img_size, img_size))
        # EfficientNet expects [0, 255] — do NOT rescale to [0, 1]
        img_array = np.expand_dims(img.astype('float32'), axis=0)

        heatmap = self._compute_heatmap(img_array)

        h, w = original.shape[:2]
        heatmap_b64 = self._overlay_heatmap(heatmap, original, h, w, confidence=confidence)

        # Save overlay if output_dir is set
        overlay_path = None
        if self.output_dir and save_name:
            heatmap_resized = cv2.resize(heatmap, (w, h))
            heatmap_uint8 = np.uint8(255 * heatmap_resized)
            heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
            overlay = cv2.addWeighted(original, 0.6, heatmap_colored, 0.4, 0)
            overlay_path = os.path.join(self.output_dir, f"gradcam_{save_name}")
            cv2.imwrite(overlay_path, overlay)

        return heatmap_b64, overlay_path

    def generate_from_array(self, img_array, original_image=None, img_size=300, confidence=None):
        """
        Generate Grad-CAM from preprocessed numpy array.
        
        Args:
            img_array: Preprocessed image array (1, H, W, 3), in [0, 255] range
            original_image: Original image for overlay (numpy BGR)
            img_size: Model input size
            confidence: Prediction confidence for adaptive overlay intensity
            
        Returns:
            heatmap_base64: Base64 encoded overlay image
        """
        if len(img_array.shape) == 3:
            img_array = np.expand_dims(img_array, axis=0)

        heatmap = self._compute_heatmap(img_array)

        if original_image is not None:
            h, w = original_image.shape[:2]
            base_img = original_image
        else:
            h, w = img_size, img_size
            base_img = np.uint8(np.clip(img_array[0], 0, 255))
            if base_img.shape[-1] == 3:
                base_img = cv2.cvtColor(base_img, cv2.COLOR_RGB2BGR)

        return self._overlay_heatmap(heatmap, base_img, h, w, confidence=confidence)
