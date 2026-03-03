"""
Model service for token generation.

Provides async generators for streaming chat responses.
Generates confident, domain-expert wildlife analysis.

Design:
- Async generators for non-blocking token yields
- Context-aware responses with prediction data
- Confident wildlife expert tone
- Easy integration point for real model later
"""

import asyncio
import random
from typing import AsyncGenerator, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Species Knowledge Base — Authoritative Responses
# ═══════════════════════════════════════════════════════════

SPECIES_PROFILES = {
    "tiger": {
        "name": "Tiger",
        "sci": "Panthera tigris",
        "tracks": "large, round paw prints (12-16 cm) with four toes and no visible claw marks. The central pad is distinctly bilobed at the rear, creating an asymmetric shape wider than it is long",
        "habitat": "tropical forests, mangroves, and grasslands across India and Southeast Asia",
        "behavior": "Tigers are solitary apex predators that use a direct-register walking gait — placing rear paws precisely in front paw prints. Track spacing indicates walking speed and body size",
        "conservation": "Endangered. Tiger footprint monitoring is critical for population estimates in Project Tiger conservation programs. Individual tigers can be identified by unique pad patterns",
        "field_tips": "Look for asymmetric prints near water sources, game trails, and forest edges. Fresh prints in mud show fine ridges on pad surfaces. Stride length of 55-80 cm indicates adult male",
    },
    "leopard": {
        "name": "Leopard",
        "sci": "Panthera pardus",
        "tracks": "compact, round prints (7-10 cm) with four toes and retractable claws that leave no marks. The pad has a distinct tri-lobed rear edge",
        "habitat": "diverse environments from rainforests to mountains, savannas, and semi-arid regions",
        "behavior": "Leopards are the most adaptable big cats, often resting in trees and hunting at night. Their direct-register walk creates neat, single-line trails",
        "conservation": "Vulnerable. Leopard tracks near human settlements indicate critical wildlife corridors essential for genetic diversity in fragmented habitats",
        "field_tips": "Prints are proportionally rounder and smaller than tiger prints. Check for drag marks near trees — leopards cache prey in branches. Prints may appear in pairs during bounding gait",
    },
    "elephant": {
        "name": "Elephant",
        "sci": "Elephas maximus / Loxodonta africana",
        "tracks": "the largest land animal prints (40-50 cm), perfectly round with a distinctive cracked-skin texture. Heavy soil compression creates deep impressions visible from distance",
        "habitat": "forests, savannas, and wetlands",
        "behavior": "Elephants follow established corridors between water and feeding areas. Their ambling gait creates overlapping front-rear print patterns. Track depth indicates approximate body mass",
        "conservation": "Endangered. Tracking elephant corridors helps prevent human-elephant conflict and guides conservation of critical migration routes",
        "field_tips": "Track circumference in centimeters × 5.5 estimates shoulder height. Fresh prints show crisp skin-texture impressions. Dung piles near tracks confirm recent passage within 12 hours",
    },
    "deer": {
        "name": "Deer",
        "sci": "Cervidae family",
        "tracks": "cloven hooves creating distinctive two-toed prints (5-9 cm) with pointed tips. Dewclaw impressions may appear in soft substrates like mud or snow",
        "habitat": "forests, grasslands, and wetlands worldwide",
        "behavior": "Deer alternate between walking (prints in straight line) and bounding gaits (splayed hooves with dewclaw marks). Track clusters near scraped earth indicate territorial marking",
        "conservation": "Monitoring deer track density provides reliable ecosystem health indicators. Multiple trails converging suggest nearby water sources or mineral licks",
        "field_tips": "Distinguish from goat/sheep by pointed rather than rounded hoof tips. Heart-shaped prints are characteristic. Track size indicates species — smaller prints suggest muntjac, larger indicate sambar",
    },
    "wolf": {
        "name": "Wolf",
        "sci": "Canis lupus",
        "tracks": "oval prints (10-13 cm) with four toes showing visible claw marks. A distinctive X-pattern forms between the two front toes and two rear toes when lines are drawn across the pad",
        "habitat": "forests, tundra, mountains, and grasslands",
        "behavior": "Wolves use energy-efficient direct-register trot — rear paw landing precisely in front paw print creates a single-file trail. Pack trails show parallel tracks with the alpha leading",
        "conservation": "Wolf track monitoring reveals pack size, territory boundaries, and population dynamics. The X-pattern between toes distinguishes wolf from domestic dog prints",
        "field_tips": "Wolf prints are larger and more elongated than domestic dog prints. Check for the negative space X-pattern between toes. Pack trails show 4-8 parallel single-file tracks. Stride length of 65-75 cm indicates trotting adult",
    },
}

# Comprehensive response templates for different query types
GENERAL_TOPICS = {
    "gradcam": "### Grad-CAM Visualization\n\nGrad-CAM (Gradient-weighted Class Activation Mapping) reveals which regions of the footprint image most influenced the model's prediction.\n\n**How to interpret the heatmap:**\n\n• **Red/warm zones** — High activation areas that strongly drove the classification decision. These typically highlight pad shapes, toe configurations, and claw marks.\n• **Blue/cool zones** — Low activation areas with minimal influence. Usually background substrate or uniform regions.\n• **Focus patterns** — A well-trained model focuses on morphologically significant features: central pad geometry, inter-digital spacing, and claw impressions.\n\n**What it tells you:**\nIf the heatmap concentrates on the actual footprint structure, the prediction is morphologically grounded. If it highlights background or edges, the confidence may be unreliable — consider uploading a better-framed image.",

    "model": "### WildTrackAI Model Architecture\n\n**Base:** EfficientNetB3 v4 with SE (Squeeze-and-Excitation) attention blocks\n**Transfer learning:** Pre-trained on ImageNet, fine-tuned on wildlife footprint data\n**Input:** 300×300 pixel RGB images\n**Training data:** 2,000 images across 5 species (400 per class, balanced)\n\n**Performance:**\n• Validation accuracy: 77.5% (with TTA)\n• Per-class F1: Deer 0.81, Elephant 0.84, Leopard 0.67, Tiger 0.70, Wolf 0.71\n• Augmentation: MixUp, CutMix, Random Erasing, SGDR warm restarts\n• Inference: Test-Time Augmentation (3 passes) for improved stability\n\n**Confidence calibration:** Temperature scaling (T=1.2) prevents overconfident predictions. Shannon entropy quantifies uncertainty — high entropy with low confidence triggers the Unknown classification.",

    "conservation": "### Wildlife Conservation & Tracking\n\nFootprint tracking is one of the oldest and most reliable wildlife monitoring techniques, now enhanced by computer vision.\n\n**Why footprint identification matters:**\n\n• **Population estimates** — Track density surveys provide non-invasive population counts without disturbing animals\n• **Individual identification** — Unique pad patterns enable individual recognition, critical for endangered species monitoring\n• **Corridor mapping** — Track line analysis reveals migration corridors essential for habitat connectivity planning\n• **Behavioral insights** — Gait analysis from track spacing indicates health, speed, and behavioral state\n\n**Conservation impact:** Systems like WildTrackAI democratize expert-level track identification, enabling citizen scientists and field teams to contribute to population monitoring programs at scale.",

    "unknown": "### Understanding \"Unknown\" Classifications\n\nWhen WildTrackAI marks a footprint as Unknown, it's exercising responsible AI judgment rather than forcing a potentially incorrect classification.\n\n**The dual-threshold system:**\n\n1. **Confidence threshold (40%)** — If the highest class probability falls below 40%...\n2. **Entropy threshold (90%)** — ...AND Shannon entropy exceeds 90% of maximum...\n3. **Result:** The prediction is marked Unknown to prevent misidentification.\n\n**Common causes:**\n• The image contains a species outside our 5 trained classes (closed-set limitation)\n• Poor image quality — blurry, low contrast, or partial footprint\n• Non-footprint content — drawings, illustrations, or non-track images\n• Ambiguous substrate making track features unclear\n\n**Closed-set note:** WildTrackAI currently identifies Tiger, Leopard, Elephant, Deer, and Wolf. Other species (lion, bear, fox, etc.) will be flagged as Unknown — this is correct behavior, not an error.",
}


# ═══════════════════════════════════════════════════════════
# Token Generation (Async Generators)
# ═══════════════════════════════════════════════════════════

async def get_model_tokens(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    token_delay_range: tuple = (30, 80),
) -> AsyncGenerator[str, None]:
    """
    Generate streaming tokens for a chat message.
    
    Context-aware: uses prediction data when available for
    authoritative, species-specific analysis.
    """
    try:
        response = _build_response(message, context)
        tokens = response.split(" ")
        
        for i, token in enumerate(tokens):
            if i < len(tokens) - 1:
                token = token + " "
            yield token
            delay_ms = random.uniform(token_delay_range[0], token_delay_range[1])
            await asyncio.sleep(delay_ms / 1000.0)
    
    except asyncio.CancelledError:
        logger.info("Token generation cancelled by client")
        raise
    except Exception as e:
        logger.error(f"Error during token generation: {e}")
        raise


def _build_response(
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build an authoritative, context-aware response.
    Uses prediction data for confident species analysis.
    """
    context = context or {}
    msg_lower = message.lower().strip()
    
    # Check if prediction context is available
    prediction = context.get("prediction")
    
    # Priority 1: Prediction-aware analysis
    if prediction:
        return _build_prediction_response(message, prediction)
    
    # Priority 2: Topic-specific expertise
    topic_response = _match_topic(msg_lower)
    if topic_response:
        return topic_response
    
    # Priority 3: Species-specific questions
    species_response = _match_species_query(msg_lower)
    if species_response:
        return species_response
    
    # Priority 4: Intelligent general response
    return _build_general_response(msg_lower)


def _build_prediction_response(message: str, prediction: dict) -> str:
    """Generate confident analysis for a prediction result."""
    species = prediction.get("predicted_class", "unknown")
    raw_class = prediction.get("raw_class", species)
    confidence = prediction.get("confidence", 0)
    top3 = prediction.get("top3", [])
    is_unknown = prediction.get("is_unknown", False)
    
    profile = SPECIES_PROFILES.get(raw_class if is_unknown else species, {})
    pct = f"{confidence * 100:.1f}"
    
    if is_unknown:
        return (
            f"### 🔍 Prediction Analysis\n\n"
            f"The footprint presents morphological features that don't strongly match any single trained species. "
            f"The highest probability is **{raw_class.title()}** at **{pct}%**, which falls below the confidence threshold.\n\n"
            f"**Morphological observations:**\n"
            f"The print structure shows characteristics that could belong to multiple species families. "
            f"{'The closest match (' + raw_class.title() + ') typically shows ' + profile.get('tracks', 'distinctive pad and toe patterns') + '.' if profile else ''}\n\n"
            f"### 📌 Recommended Steps\n\n"
            f"• Upload a clearer image with the footprint centered and well-lit\n"
            f"• Measure the physical print size — this is the strongest discriminator between species\n"
            f"• Note the substrate type (mud, sand, snow) as it affects print clarity\n"
            f"• Check the Grad-CAM heatmap to verify the model focused on the actual footprint features\n\n"
            f"WildTrackAI currently identifies 5 species: Tiger, Leopard, Elephant, Deer, and Wolf. "
            f"Species outside this set will be correctly flagged as Unknown."
        )
    
    # Confident prediction response
    sections = []
    
    sections.append(
        f"### 🔍 Prediction Analysis\n\n"
        f"This footprint is identified as **{species.title()}** ({profile.get('sci', '')}) "
        f"with **{pct}%** confidence.\n\n"
        f"**Track morphology:** {profile.get('name', species.title())} prints show "
        f"{profile.get('tracks', 'distinctive characteristics')}."
    )
    
    # Confidence interpretation
    if confidence >= 0.80:
        conf_text = f"At {pct}%, this is a **high-confidence identification**. The morphological features strongly align with known {species.title()} track patterns."
    elif confidence >= 0.60:
        conf_text = f"At {pct}%, confidence is **moderate to high**. The primary identification is reliable, though minor feature overlap with related species exists."
    else:
        conf_text = f"At {pct}%, confidence is **moderate**. Consider cross-referencing with physical measurements and habitat context for confirmation."
    
    sections.append(f"\n### 📊 Confidence Assessment\n\n{conf_text}")
    
    # Alternatives
    if len(top3) > 1:
        alt_lines = []
        for t in top3[1:]:
            alt_name = t.get("class", "").title()
            alt_conf = f"{t.get('confidence', 0) * 100:.1f}"
            alt_profile = SPECIES_PROFILES.get(t.get("class", ""), {})
            alt_tracks = alt_profile.get("tracks", "similar features")
            alt_lines.append(f"• **{alt_name}** ({alt_conf}%) — typically shows {alt_tracks}")
        sections.append(f"\n### ⚖️ Alternative Considerations\n\n" + "\n".join(alt_lines))
    
    # Field notes
    if profile.get("field_tips"):
        sections.append(f"\n### 🧭 Field Verification\n\n{profile['field_tips']}")
    
    # Ecology
    if profile.get("conservation"):
        sections.append(f"\n### 🌍 Ecological Context\n\n{profile['conservation']}")
    
    return "\n".join(sections)


def _match_topic(msg_lower: str) -> Optional[str]:
    """Match general topics."""
    if any(w in msg_lower for w in ["gradcam", "grad-cam", "heatmap", "activation map"]):
        return GENERAL_TOPICS["gradcam"]
    if any(w in msg_lower for w in ["model", "architecture", "efficientnet", "how does it work", "accuracy"]):
        return GENERAL_TOPICS["model"]
    if any(w in msg_lower for w in ["conservation", "protect", "endangered", "save wildlife"]):
        return GENERAL_TOPICS["conservation"]
    if any(w in msg_lower for w in ["unknown", "not recognized", "can't identify", "threshold"]):
        return GENERAL_TOPICS["unknown"]
    return None


def _match_species_query(msg_lower: str) -> Optional[str]:
    """Match species-specific questions."""
    for key, profile in SPECIES_PROFILES.items():
        if key in msg_lower or profile["name"].lower() in msg_lower:
            return (
                f"### {profile['name']} ({profile['sci']})\n\n"
                f"**Track characteristics:** {profile['name']} prints show {profile['tracks']}.\n\n"
                f"**Habitat:** Found in {profile['habitat']}.\n\n"
                f"**Behavior:** {profile['behavior']}.\n\n"
                f"**Field identification:** {profile['field_tips']}\n\n"
                f"**Conservation:** {profile['conservation']}"
            )
    return None


def _build_general_response(msg_lower: str) -> str:
    """Build an intelligent general response."""
    if any(w in msg_lower for w in ["hello", "hi ", "hey", "greetings"]):
        return (
            "### Welcome to WildTrackAI\n\n"
            "I'm your wildlife tracking assistant. I can help you with:\n\n"
            "• **Footprint analysis** — Upload an image and I'll identify the species and explain the morphological features\n"
            "• **Species information** — Ask about any of our 5 trained species (Tiger, Leopard, Elephant, Deer, Wolf)\n"
            "• **Technical details** — Model architecture, Grad-CAM interpretation, confidence calibration\n"
            "• **Field tracking tips** — Practical guidance for identifying tracks in the wild\n\n"
            "Upload a footprint image or ask a question to get started."
        )
    
    if any(w in msg_lower for w in ["compare", "difference", "vs", "versus"]):
        return (
            "### Species Comparison Guide\n\n"
            "Key discriminators between commonly confused species:\n\n"
            "**Tiger vs Leopard:**\n"
            "• Size: Tiger 12-16 cm vs Leopard 7-10 cm\n"
            "• Shape: Tiger asymmetric, wider than long vs Leopard round, compact\n"
            "• Both lack claw marks (retractable)\n\n"
            "**Wolf vs Dog:**\n"
            "• Wolf prints are more elongated with the X-pattern between toes\n"
            "• Dogs show rounder prints without consistent X-pattern\n"
            "• Wolf trails follow direct-register single-file patterns\n\n"
            "**Deer identification:**\n"
            "• Only cloven-hooved species in our set — two-toed prints are distinctive\n"
            "• Dewclaws visible in soft substrate help confirm deer vs goat\n\n"
            "Use the **Compare** feature in Species Explorer for side-by-side analysis."
        )
    
    if any(w in msg_lower for w in ["footprint", "track", "print", "paw", "identify"]):
        return (
            "### Footprint Identification Guide\n\n"
            "For accurate identification, examine these diagnostic features:\n\n"
            "1. **Toe count** — Cats: 4 toes, no claws. Canids: 4 toes with claws. Deer: 2 toes (cloven). Elephants: 5 toes.\n"
            "2. **Pad shape** — Central pad geometry is the primary discriminator between species.\n"
            "3. **Claw visibility** — Present in canids (wolf, dog), absent in felines (retractable claws).\n"
            "4. **Print size** — Measure the longest dimension for species narrowing.\n"
            "5. **Gait pattern** — Direct-register (single line) vs bounding vs ambling.\n\n"
            "Upload a clear, well-lit image with the footprint centered for best results."
        )
    
    return (
        "### Wildlife Tracking Analysis\n\n"
        "I can provide detailed analysis on wildlife footprints and tracking. Here's what I can help with:\n\n"
        "• **Upload a footprint image** for species identification with confidence analysis\n"
        "• **Ask about specific species** — I have detailed track morphology data for Tiger, Leopard, Elephant, Deer, and Wolf\n"
        "• **Interpretation guidance** — I can explain Grad-CAM heatmaps, confidence scores, and entropy values\n"
        "• **Field tracking advice** — Practical tips for finding and identifying tracks in different substrates\n\n"
        "Try asking: 'Tell me about tiger tracks' or 'How do I distinguish wolf from dog prints?'"
    )


# ═══════════════════════════════════════════════════════════
# Real Model Integration Point (Future)
# ═══════════════════════════════════════════════════════════

async def get_model_tokens_real(
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """
    PLACEHOLDER for real model inference.
    
    Replace this implementation when you have:
    - Actual image encoding
    - Wildlife classification model
    - Species confidence scoring
    - Real async model API
    
    Args:
        message: User message (or image metadata)
        context: Optional context
        
    Yields:
        Real tokens from the model
    """
    raise NotImplementedError(
        "Real model integration not yet implemented. "
        "Currently using simulation via get_model_tokens()."
    )


# ═══════════════════════════════════════════════════════════
# Configuration & Metrics
# ═══════════════════════════════════════════════════════════

class ModelMetrics:
    """Track model performance metrics."""
    
    def __init__(self):
        self.total_requests = 0
        self.completed_streams = 0
        self.failed_streams = 0
        self.total_tokens_generated = 0
        self.average_latency_ms = 0.0
    
    def record_completion(self, token_count: int, latency_ms: float):
        """Record a successful stream completion."""
        self.completed_streams += 1
        self.total_tokens_generated += token_count
        # Simple moving average
        current_avg = self.average_latency_ms * (self.completed_streams - 1)
        self.average_latency_ms = (current_avg + latency_ms) / self.completed_streams
    
    def record_failure(self):
        """Record a failed stream."""
        self.failed_streams += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        success_rate = (
            self.completed_streams / (self.completed_streams + self.failed_streams)
            if (self.completed_streams + self.failed_streams) > 0
            else 0
        )
        
        return {
            "total_requests": self.total_requests,
            "completed_streams": self.completed_streams,
            "failed_streams": self.failed_streams,
            "success_rate": success_rate,
            "total_tokens_generated": self.total_tokens_generated,
            "average_latency_ms": round(self.average_latency_ms, 2),
        }


# Global metrics instance
metrics = ModelMetrics()
