"""
WildTrackAI - Phase 7: Embedding Extractor
===========================================
Extracts 512-dim feature vectors from the penultimate layer.
Provides similarity search using cosine similarity.
Stores embeddings in the database for later retrieval.

Usage (integrated into main.py via import):
    from embedding_module import EmbeddingExtractor
    
    extractor = EmbeddingExtractor(model)
    embedding = extractor.extract(image_array)
    similarity = extractor.cosine_similarity(emb1, emb2)
"""

import numpy as np
import tensorflow as tf


class EmbeddingExtractor:
    """Extract feature embeddings from the penultimate layer of the model."""

    def __init__(self, model):
        """
        Args:
            model: Loaded Keras model with Dense layers
        """
        self.model = model
        self.embedding_model = self._build_embedding_model()
        self.embedding_dim = self._get_embedding_dim()
        print(f"[Embeddings] Initialized ({self.embedding_dim}-dim vectors)")

    def _build_embedding_model(self):
        """Build a model that outputs the penultimate Dense layer."""
        # Find the second-to-last Dense layer (before softmax)
        dense_layers = []
        for layer in self.model.layers:
            if isinstance(layer, tf.keras.layers.Dense):
                dense_layers.append(layer)

        if len(dense_layers) < 2:
            # Fallback: use GlobalAveragePooling output
            for layer in self.model.layers:
                if isinstance(layer, tf.keras.layers.GlobalAveragePooling2D):
                    return tf.keras.Model(
                        inputs=self.model.input,
                        outputs=layer.output
                    )
            raise ValueError("Cannot find suitable embedding layer")

        # Use the layer before the final Dense (softmax)
        penultimate = dense_layers[-2]
        return tf.keras.Model(
            inputs=self.model.input,
            outputs=penultimate.output
        )

    def _get_embedding_dim(self):
        """Get the dimensionality of the embedding."""
        output_shape = self.embedding_model.output_shape
        return output_shape[-1] if isinstance(output_shape, tuple) else output_shape

    def extract(self, img_array):
        """
        Extract embedding from a preprocessed image array.
        
        Args:
            img_array: Preprocessed image (1, H, W, 3), normalized to [0,1]
            
        Returns:
            numpy array: Feature embedding vector
        """
        if len(img_array.shape) == 3:
            img_array = np.expand_dims(img_array, axis=0)

        embedding = self.embedding_model.predict(img_array, verbose=0)[0]

        # L2 normalize for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    @staticmethod
    def cosine_similarity(emb1, emb2):
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            emb1, emb2: L2-normalized embedding vectors
            
        Returns:
            float: Similarity score in [-1, 1], higher = more similar
        """
        return float(np.dot(emb1, emb2))

    @staticmethod
    def euclidean_distance(emb1, emb2):
        """Compute Euclidean distance between two embeddings."""
        return float(np.linalg.norm(emb1 - emb2))

    def find_most_similar(self, query_embedding, stored_embeddings, top_k=5):
        """
        Find the most similar embeddings to a query.
        
        Args:
            query_embedding: The query embedding vector
            stored_embeddings: List of (id, embedding) tuples
            top_k: Number of results to return
            
        Returns:
            List of (id, similarity_score) tuples, sorted by similarity
        """
        similarities = []
        for emb_id, emb in stored_embeddings:
            sim = self.cosine_similarity(query_embedding, emb)
            similarities.append((emb_id, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
