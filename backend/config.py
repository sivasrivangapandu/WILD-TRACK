"""
WildTrackAI — Centralized Configuration
=========================================
All paths, constants, API keys, and static data dictionaries.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Create directories
for _d in [UPLOADS_DIR, OUTPUTS_DIR]:
    os.makedirs(_d, exist_ok=True)

# Model files (order: .keras first, then .h5 variants)
MODEL_PATH_KERAS = os.path.join(MODELS_DIR, "wildtrack_v4_cpu.keras")
MODEL_PATH = os.path.join(MODELS_DIR, "wildtrack_complete_model.h5")
MODEL_PATH_LEGACY = os.path.join(MODELS_DIR, "wildtrack_final.h5")
MODEL_PATH_V4 = os.path.join(MODELS_DIR, "wildtrack_v4.h5")
MODEL_PATH_V3 = os.path.join(MODELS_DIR, "wildtrack_v3_b3.h5")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")

# Default image size (overridden by metadata if available)
IMG_SIZE = 300

# Confidence threshold — below this, prediction is "unknown"
CONFIDENCE_THRESHOLD = 0.40

# ── Model download URLs (cloud deployment) ─────────────────────────
MODEL_URLS = {
    "wildtrack_v4_cpu.keras": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_v4_cpu.keras",
    "wildtrack_complete_model.h5": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_complete_model.h5",
    "wildtrack_final.h5": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_final.h5",
}

# ── API Keys ───────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
NINJA_API_KEY = os.getenv("NINJA_API_KEY", "")

CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "").strip()
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "").strip()
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "").strip()

# ── CORS ───────────────────────────────────────────────────────────
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# ── Animal Info Database ───────────────────────────────────────────
ANIMAL_INFO = {
    'tiger': {
        'scientific_name': 'Panthera tigris',
        'conservation_status': 'Endangered',
        'weight': '100-300 kg',
        'footprint_size': '12-16 cm',
        'habitat': 'Tropical forests, grasslands, mangroves',
        'description': 'Tigers have large, round paw prints with four toes and no claw marks. '
                       'The pad is large and bilobed at the rear.',
        'distribution': 'India, Southeast Asia, Russia',
    },
    'leopard': {
        'scientific_name': 'Panthera pardus',
        'conservation_status': 'Vulnerable',
        'weight': '30-90 kg',
        'footprint_size': '7-10 cm',
        'habitat': 'Forests, savannas, mountains',
        'description': 'Leopard prints are smaller than tiger prints with four toes. '
                       'Claws are retractable and rarely show in tracks.',
        'distribution': 'Africa, Asia',
    },
    'elephant': {
        'scientific_name': 'Elephas maximus / Loxodonta africana',
        'conservation_status': 'Endangered',
        'weight': '2,700-6,000 kg',
        'footprint_size': '40-50 cm',
        'habitat': 'Forests, savannas, wetlands',
        'description': 'Elephant footprints are the largest of any land animal. '
                       'They are round with a distinctive cracked skin pattern.',
        'distribution': 'Africa, South/Southeast Asia',
    },
    'deer': {
        'scientific_name': 'Cervidae (family)',
        'conservation_status': 'Least Concern (varies)',
        'weight': '30-300 kg',
        'footprint_size': '5-9 cm',
        'habitat': 'Forests, grasslands, wetlands',
        'description': 'Deer have cloven hooves creating two-toed prints. '
                       'Dewclaws may show in soft ground.',
        'distribution': 'Worldwide except Antarctica/Australia',
    },
    'wolf': {
        'scientific_name': 'Canis lupus',
        'conservation_status': 'Least Concern',
        'weight': '30-80 kg',
        'footprint_size': '10-13 cm',
        'habitat': 'Forests, tundra, grasslands',
        'description': 'Wolf tracks show four toes with claws visible. '
                       'Larger than domestic dog prints with a more elongated shape.',
        'distribution': 'North America, Europe, Asia',
    },
    'fox': {
        'scientific_name': 'Vulpes vulpes',
        'conservation_status': 'Least Concern',
        'weight': '3-14 kg',
        'footprint_size': '4-6 cm',
        'habitat': 'Forests, grasslands, urban areas',
        'description': 'Fox tracks are smaller than wolf tracks with four toes. '
                       'Prints often appear in a straight line (direct register).',
        'distribution': 'Worldwide',
    },
    'dog': {
        'scientific_name': 'Canis lupus familiaris',
        'conservation_status': 'Domesticated',
        'weight': '1-90 kg',
        'footprint_size': '3-12 cm',
        'habitat': 'Worldwide, human settlements',
        'description': 'Dog paw prints show four toes with visible claw marks. '
                       'Size varies greatly by breed. Often confused with wolf.',
        'distribution': 'Worldwide',
    },
    'cat': {
        'scientific_name': 'Felis catus',
        'conservation_status': 'Domesticated',
        'weight': '3-7 kg',
        'footprint_size': '2-4 cm',
        'habitat': 'Worldwide, human settlements',
        'description': 'Cat prints show four toes without claw marks (retractable claws). '
                       'Small, round prints with a distinctive tri-lobed pad.',
        'distribution': 'Worldwide',
    },
    'hyena': {
        'scientific_name': 'Crocuta crocuta',
        'conservation_status': 'Least Concern',
        'weight': '40-86 kg',
        'footprint_size': '8-11 cm',
        'habitat': 'Savannas, grasslands, semi-deserts',
        'description': 'Hyena tracks show four toes with blunt claw marks. '
                       'Front feet are larger than rear. Pads are rough.',
        'distribution': 'Africa, parts of Asia',
    },
    'bear': {
        'scientific_name': 'Ursidae (family)',
        'conservation_status': 'Varies by species',
        'weight': '60-600 kg',
        'footprint_size': '15-30 cm',
        'habitat': 'Forests, mountains, tundra',
        'description': 'Bear prints show five toes with long claw marks. '
                       'Hind foot is plantigrade, resembling a human footprint.',
        'distribution': 'North/South America, Europe, Asia',
    },
}

# ── Species Feature Data (for structured reasoning) ────────────────
SPECIES_FEATURES = {
    "tiger": {
        "pad_shape": "large, bilobed rear pad",
        "toe_count": 4,
        "claw_marks": False,
        "symmetry": "asymmetric",
        "size_range": "12-16 cm",
        "gait_pattern": "direct register walk",
        "distinguishing": "Largest cat footprint. No claw marks. Asymmetric pad wider than long.",
        "confused_with": ["leopard", "lion"],
        "f1_score": 0.70,
    },
    "leopard": {
        "pad_shape": "compact, round, tri-lobed rear",
        "toe_count": 4,
        "claw_marks": False,
        "symmetry": "round",
        "size_range": "7-10 cm",
        "gait_pattern": "direct register walk",
        "distinguishing": "Smaller than tiger. Proportionally rounder. Retractable claws.",
        "confused_with": ["tiger", "cat"],
        "f1_score": 0.67,
    },
    "elephant": {
        "pad_shape": "large circular with cracked texture",
        "toe_count": 5,
        "claw_marks": False,
        "symmetry": "round",
        "size_range": "40-50 cm",
        "gait_pattern": "ambling",
        "distinguishing": "Largest land animal print. Cracked skin texture. Heavy soil compression.",
        "confused_with": [],
        "f1_score": 0.84,
    },
    "deer": {
        "pad_shape": "cloven hoof, two elongated toes",
        "toe_count": 2,
        "claw_marks": False,
        "symmetry": "bilaterally symmetric",
        "size_range": "5-9 cm",
        "gait_pattern": "bounding/walking",
        "distinguishing": "Two-toed cloven print. Dewclaws visible in soft ground. Pointed tips.",
        "confused_with": ["goat", "sheep"],
        "f1_score": 0.81,
    },
    "wolf": {
        "pad_shape": "oval with triangular heel pad",
        "toe_count": 4,
        "claw_marks": True,
        "symmetry": "oval, elongated",
        "size_range": "10-13 cm",
        "gait_pattern": "direct register trot",
        "distinguishing": "Visible claw marks. More elongated than dog. X-pattern between toes and pad.",
        "confused_with": ["dog", "coyote"],
        "f1_score": 0.71,
    },
}
