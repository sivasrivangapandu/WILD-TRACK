"""
WildTrackAI — Chat Service
============================
Gemini AI chat, structured fallback engine, session memory,
and knowledge base responses.
"""

import json
import time
from collections import defaultdict

from config import (
    GEMINI_API_KEY, ANIMAL_INFO, SPECIES_FEATURES, CONFIDENCE_THRESHOLD,
)

# ── Gemini Initialization ─────────────────────────────────────────
gemini_model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        print(f"  [OK] Gemini AI initialized (gemini-2.0-flash)")
    except Exception as e:
        print(f"  [WARN] Gemini init failed: {e} -- falling back to rule-based chat")
else:
    print("  [WARN] No GEMINI_API_KEY found -- using rule-based chat")


# ── System Prompt ─────────────────────────────────────────────────
WILDTRACK_SYSTEM_PROMPT = """You are the WildTrackAI assistant -- an expert AI chatbot embedded in a wildlife footprint identification system built as a final-year computer science project.

## About the System
- **Project:** WildTrackAI -- AI-powered animal footprint identification
- **Model:** EfficientNetB3 v4 (transfer learning from ImageNet, SE Attention)
- **Input:** 300×300 pixel footprint images
- **Accuracy:** 77.5% on 5 species (with TTA; 74.5% without TTA)
- **Training data:** 2,000 total images (1,600 train + 400 validation, balanced 400/class)
- **Data cleaning:** Perceptual hash deduplication, CLAHE normalization, corrupt image removal
- **Augmentation:** MixUp, CutMix, Random Erasing, SGDR warm restarts
- **Inference:** Test-Time Augmentation (3 passes)
- **Explainability:** Grad-CAM (Gradient-weighted Class Activation Mapping) heatmaps
- **Confidence threshold:** 40% -- below this AND high entropy, species is marked "Unknown"
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** React 18 + Vite + Tailwind CSS + Framer Motion

## Supported Species & Their Details
1. **Tiger** (Panthera tigris) -- Endangered. Footprint: 12-16cm, round & asymmetric, no claw marks.
2. **Leopard** (Panthera pardus) -- Vulnerable. Footprint: 7-10cm, compact & round, no claw marks.
3. **Elephant** (Elephas maximus) -- Endangered. Footprint: 40-50cm, large & round, cracked skin pattern.
4. **Deer** (Cervidae family) -- Least Concern. Footprint: 5-9cm, cloven hoof (two toes).
5. **Wolf** (Canis lupus) -- Least Concern. Footprint: 10-13cm, oval with visible claw marks.

## Response Format (ALWAYS use this structure when analyzing predictions)
### 🔬 Prediction Analysis
### 📊 Confidence Interpretation
### 🐾 Footprint Characteristics
### 🔄 Alternative Hypotheses
### 🌍 Ecological Insight
### 📋 Suggested Next Steps

For text-only questions, respond naturally but stay structured with markdown.

## Your Behavior Rules
- Be helpful, concise, and technically accurate
- Use Markdown formatting (bold, lists, emojis) for readability
- When discussing predictions, reference the actual data provided
- If asked about species NOT in the system, explain closed-set classification
- Never fabricate accuracy numbers or capabilities
- Stay focused on wildlife, footprints, conservation, and the system
"""


# ── Session Memory ────────────────────────────────────────────────
_session_store = defaultdict(lambda: {
    "history": [],
    "last_prediction": None,
    "last_species": None,
    "created": time.time(),
})

MAX_HISTORY = 10


def _get_session(session_id: str) -> dict:
    s = _session_store[session_id]
    if time.time() - s["created"] > 3600:
        _session_store[session_id] = {
            "history": [], "last_prediction": None,
            "last_species": None, "created": time.time(),
        }
    return _session_store[session_id]


def _update_session(session_id: str, user_msg: str, bot_msg: str, prediction: dict = None):
    s = _get_session(session_id)
    s["history"].append({"user": user_msg, "bot": bot_msg[:200]})
    if len(s["history"]) > MAX_HISTORY:
        s["history"] = s["history"][-MAX_HISTORY:]
    if prediction:
        s["last_prediction"] = prediction
        s["last_species"] = prediction.get("predicted_class", None)


# ── Structured Fallback Helpers ───────────────────────────────────

def _confidence_interpretation(confidence: float, species: str) -> str:
    f1 = SPECIES_FEATURES.get(species, {}).get("f1_score", 0.7)
    if confidence >= 0.85:
        return (f"**Very High Confidence** -- The model is {confidence*100:.1f}% certain. "
                f"This species has an F1 score of {f1:.3f}, indicating reliable identification.")
    elif confidence >= 0.70:
        return (f"**High Confidence** -- At {confidence*100:.1f}%, the model is fairly certain. "
                f"This is above the reliability threshold.")
    elif confidence >= 0.50:
        return (f"**Moderate Confidence** -- At {confidence*100:.1f}%, the model's certainty is above "
                f"our 50% threshold but not conclusive.")
    else:
        return (f"**Below Threshold** -- At {confidence*100:.1f}%, the confidence falls below our "
                f"50% identification threshold.")


def _get_species_characteristics(species: str) -> str:
    feat = SPECIES_FEATURES.get(species, {})
    info = ANIMAL_INFO.get(species, {})
    if not feat:
        return f"Limited feature data available for {species}."

    lines = [
        f"🔹 **Pad shape:** {feat['pad_shape']}",
        f"🔹 **Toe count:** {feat['toe_count']}",
        f"🔹 **Claw marks:** {'Visible' if feat['claw_marks'] else 'Not visible (retractable or absent)'}",
        f"🔹 **Print symmetry:** {feat['symmetry']}",
        f"🔹 **Expected size:** {feat['size_range']}",
        f"🔹 **Key identifier:** {feat['distinguishing']}",
    ]
    if info.get('habitat'):
        lines.append(f"🔹 **Typical habitat:** {info['habitat']}")
    return "\n".join(lines)


def _get_alternative_analysis(top3: list, predicted: str) -> str:
    if not top3 or len(top3) < 2:
        return "No significant alternative candidates identified."
    lines = []
    for t in top3[1:]:
        alt = t["class"]
        conf = t["confidence"]
        feat = SPECIES_FEATURES.get(alt, {})
        reason = ""
        if feat:
            pred_feat = SPECIES_FEATURES.get(predicted, {})
            if pred_feat:
                similarities = []
                if feat.get("toe_count") == pred_feat.get("toe_count"):
                    similarities.append("same toe count")
                if feat.get("claw_marks") == pred_feat.get("claw_marks"):
                    similarities.append("similar claw pattern")
                if similarities:
                    reason = f" (shares {', '.join(similarities)} with {predicted})"
        lines.append(f"🔸 **{alt.title()}** -- {conf*100:.1f}%{reason}")
        if feat.get("distinguishing"):
            lines.append(f"  _{feat['distinguishing']}_")
    return "\n".join(lines)


def _get_ecological_insight(species: str) -> str:
    info = ANIMAL_INFO.get(species, {})
    insights = {
        "tiger": "Tiger footprints are critical for population monitoring in tiger reserves.",
        "leopard": "Leopards are the most adaptable big cats, found from rainforests to mountains.",
        "elephant": "Elephant footprints can reveal age, size, and movement patterns.",
        "deer": "Deer footprints are the most commonly found ungulate tracks.",
        "wolf": "Wolf tracks help monitor pack territories and population dynamics.",
    }
    base = insights.get(species, f"Tracking {species} contributes to understanding population dynamics.")
    if info.get("conservation_status"):
        status = info["conservation_status"]
        if "Endangered" in status:
            base += f"\n\n⚠️ **Conservation Alert:** {species.title()} is listed as {status}."
        elif "Vulnerable" in status:
            base += f"\n\n📋 **Conservation Note:** {species.title()} is {status}."
    return base


def _build_structured_prediction_response(prediction_result: dict, class_names: list = None) -> str:
    """Build a full structured analysis from prediction data."""
    if class_names is None:
        class_names = []

    species = prediction_result.get("predicted_class", "unknown")
    confidence = prediction_result.get("confidence", 0)
    top3 = prediction_result.get("top3", [])
    is_unknown = prediction_result.get("is_unknown", False)
    raw_class = prediction_result.get("raw_class", species)

    sections = []

    sections.append("### 🔬 Prediction Analysis")
    if is_unknown:
        supported_species = ', '.join(c.title() for c in class_names) if class_names else 'N/A'
        sections.append(
            f"⚠️ **Result: Unknown Species**\n\n"
            f"The model could not confidently identify this footprint. "
            f"The highest probability class is **{raw_class.title()}** at only **{confidence*100:.1f}%**, "
            f"which falls below our **{int(CONFIDENCE_THRESHOLD*100)}% confidence threshold**.\n\n"
            f"The system marks this as **Unknown** to prevent forced misclassification."
        )
    else:
        info = ANIMAL_INFO.get(species, {})
        sci_name = info.get("scientific_name", "")
        sections.append(
            f"The model identifies this footprint as **{species.title()}** "
            f"({sci_name}) with **{confidence*100:.1f}%** confidence."
        )

    sections.append("\n### 📊 Confidence Interpretation")
    analysis_species = raw_class if is_unknown else species
    sections.append(_confidence_interpretation(confidence, analysis_species))

    sections.append("\n### 🐾 Key Footprint Characteristics")
    sections.append(_get_species_characteristics(analysis_species))

    sections.append("\n### 🔄 Alternative Hypotheses")
    sections.append(_get_alternative_analysis(top3, analysis_species))

    if not is_unknown:
        sections.append("\n### 🌍 Ecological Insight")
        sections.append(_get_ecological_insight(species))

    sections.append("\n### 📋 Suggested Next Steps")
    if is_unknown:
        sections.append(
            "📸 Upload a **real footprint photo** on natural substrate\n"
            "📏 Measure the physical footprint size\n"
            "🔍 Check the **Grad-CAM heatmap**"
        )
    else:
        sections.append(
            f"📏 Verify by comparing physical footprint size against expected range "
            f"({SPECIES_FEATURES.get(species, {}).get('size_range', 'N/A')})\n"
            f"🔍 Check the **Grad-CAM heatmap**\n"
            f"📸 Upload additional angles for confirmation"
        )

    return "\n".join(sections)


def _handle_contextual_query(message: str, session: dict) -> str:
    """Handle follow-up questions using session memory."""
    msg_lower = message.lower().strip()
    last_pred = session.get("last_prediction")

    if not last_pred:
        return None

    species = last_pred.get("predicted_class", "unknown")
    raw_class = last_pred.get("raw_class", species)
    confidence = last_pred.get("confidence", 0)
    top3 = last_pred.get("top3", [])
    is_unknown = last_pred.get("is_unknown", False)

    # "Why not X?" pattern
    why_not_matches = []
    for sp in SPECIES_FEATURES:
        if sp in msg_lower and sp != species and sp != raw_class:
            why_not_matches.append(sp)

    if ("why" in msg_lower or "not" in msg_lower or "instead" in msg_lower) and why_not_matches:
        alt = why_not_matches[0]
        pred_sp = raw_class if is_unknown else species
        pred_feat = SPECIES_FEATURES.get(pred_sp, {})
        alt_feat = SPECIES_FEATURES.get(alt, {})

        lines = [f"### 🔍 Why {pred_sp.title()} and not {alt.title()}?\n"]

        alt_conf = 0
        for t in top3:
            if t["class"] == alt:
                alt_conf = t["confidence"]
                break

        lines.append(f"The model assigned **{confidence*100:.1f}%** to {pred_sp.title()} "
                     f"vs **{alt_conf*100:.1f}%** to {alt.title()}.\n")
        lines.append("**Key differences:**\n")

        diffs = []
        if pred_feat.get("claw_marks") != alt_feat.get("claw_marks"):
            diffs.append(f"🔹 **Claw marks:** {pred_sp.title()} {'shows' if pred_feat.get('claw_marks') else 'hides'} claws; "
                        f"{alt.title()} {'shows' if alt_feat.get('claw_marks') else 'hides'} claws")
        if pred_feat.get("toe_count") != alt_feat.get("toe_count"):
            diffs.append(f"🔹 **Toe count:** {pred_sp.title()} has {pred_feat.get('toe_count')} toes; "
                        f"{alt.title()} has {alt_feat.get('toe_count')} toes")
        if pred_feat.get("size_range") != alt_feat.get("size_range"):
            diffs.append(f"🔹 **Size range:** {pred_sp.title()} ({pred_feat.get('size_range', '?')}); "
                        f"{alt.title()} ({alt_feat.get('size_range', '?')})")

        if diffs:
            lines.extend(diffs)
        else:
            lines.append("These species have similar morphological features.")

        return "\n".join(lines)

    # "Tell me more" pattern
    if any(phrase in msg_lower for phrase in ["tell me more", "more detail", "more about", "explain more"]):
        pred_sp = raw_class if is_unknown else species
        info = ANIMAL_INFO.get(pred_sp, {})
        lines = [f"### 📖 Detailed Profile: {pred_sp.title()}\n"]
        if info.get("scientific_name"):
            lines.append(f"**Scientific name:** {info['scientific_name']}")
        if info.get("description"):
            lines.append(f"\n{info['description']}")
        lines.append(f"\n**Track analysis:**")
        lines.append(_get_species_characteristics(pred_sp))
        if info.get("distribution"):
            lines.append(f"\n🌍 **Distribution:** {info['distribution']}")
        lines.append(f"\n{_get_ecological_insight(pred_sp)}")
        return "\n".join(lines)

    # "How confident" pattern
    if any(phrase in msg_lower for phrase in ["how confident", "reliable", "sure", "certain", "trust"]):
        pred_sp = raw_class if is_unknown else species
        lines = [f"### 📊 Confidence Deep-Dive\n"]
        lines.append(_confidence_interpretation(confidence, pred_sp))
        f1 = SPECIES_FEATURES.get(pred_sp, {}).get("f1_score", 0)
        if f1:
            lines.append(f"\n**Model reliability for {pred_sp.title()}:** F1 score = {f1:.3f}")
        return "\n".join(lines)

    return None


def _generate_knowledge_response(message: str, class_names: list = None) -> str:
    """Knowledge-base response for text-only queries."""
    if class_names is None:
        class_names = []
    msg_lower = message.lower().strip()

    if any(w in msg_lower for w in ['hello', 'hi ', 'hey', 'greetings', 'good morning', 'good evening']):
        return ("👋 **Welcome to WildTrackAI!**\n\n"
                "I'm your AI wildlife assistant. Here's what I can do:\n\n"
                "🔍 **Identify footprints** -- Upload an image and get structured analysis\n"
                "📊 **Analyze predictions** -- Confidence scores, alternatives, and reasoning\n"
                "🔄 **Compare species** -- Ask \"why not leopard?\" after a prediction\n"
                "🌍 **Conservation info** -- Habitats, status, and ecological insights\n\n"
                "Try uploading a footprint image or ask about any species!")

    for species_name, info in ANIMAL_INFO.items():
        if species_name in msg_lower:
            feat = SPECIES_FEATURES.get(species_name, {})
            lines = [f"### 🐾 {species_name.title()} ({info.get('scientific_name', 'N/A')})\n"]
            if info.get('description'):
                lines.append(info['description'])
            lines.append(f"\n**Track Profile:**")
            if feat:
                lines.append(_get_species_characteristics(species_name))
            if info.get('conservation_status'):
                status = info['conservation_status']
                lines.append(f"\n**Conservation status:** {status}")
            if info.get('weight'):
                lines.append(f"⚖️ **Weight:** {info['weight']}")
            if info.get('distribution'):
                lines.append(f"🌍 **Range:** {info['distribution']}")
            return "\n".join(lines)

    if any(w in msg_lower for w in ['help', 'what can you', 'how to', 'how do', 'features', 'capabilities']):
        return ("### 📋 WildTrackAI Guide\n\n"
                "**Image Analysis:**\n"
                "1. Upload a footprint image using the 📸 button\n"
                "2. Get structured analysis with confidence scores\n"
                "3. View Grad-CAM heatmaps showing model focus areas\n\n"
                "**Conversational Features:**\n"
                "🔄 After a prediction, ask **\"why not leopard?\"** for comparison\n"
                "📖 Ask **\"tell me more\"** for deeper species info\n"
                "📊 Ask **\"how confident?\"** for reliability analysis")

    if any(w in msg_lower for w in ['accuracy', 'model', 'architecture', 'technical', 'how accurate']):
        return ("### 🧠 Model Architecture\n\n"
                "**Base:** EfficientNetB3 v4 (transfer learning from ImageNet)\n"
                f"**Classes:** {', '.join(c.title() for c in class_names)}\n"
                "**Training pipeline:** MixUp/CutMix augmentation + CLAHE normalization\n"
                "**Explainability:** Grad-CAM heatmaps\n"
                f"**OOD handling:** {int(CONFIDENCE_THRESHOLD*100)}% confidence threshold + Unknown class")

    if any(w in msg_lower for w in ['gradcam', 'grad-cam', 'heatmap', 'explain', 'xai', 'interpretab']):
        return ("### 🔍 Grad-CAM Explainability\n\n"
                "**Gradient-weighted Class Activation Mapping** visualizes which image regions "
                "influenced the model's prediction.\n\n"
                "**Reading the heatmap:**\n"
                "🔴 **Red/warm** = High importance (model focused here)\n"
                "🔵 **Blue/cool** = Low importance")

    if any(w in msg_lower for w in ['footprint', 'track', 'paw', 'print', 'identify']):
        return ("### 🐾 Footprint Identification Guide\n\n"
                "**Key distinguishing features:**\n\n"
                "| Feature | Cat family | Dog family | Ungulates |\n"
                "|---------|-----------|-----------|----------|\n"
                "| Claws | Hidden | Visible | Hooves |\n"
                "| Toes | 4, round | 4, oval | 2 (cloven) |\n"
                "| Pad | Large, bilobed | Triangular | None |\n\n"
                "Upload a footprint image for AI-powered identification!")

    if any(w in msg_lower for w in ['conserv', 'endanger', 'protect', 'wildlife', 'iucn']):
        return ("### 🌍 Conservation & WildTrackAI\n\n"
                "**Species Conservation Status:**\n"
                "🔴 **Endangered:** Tiger, Elephant\n"
                "🟡 **Vulnerable:** Leopard\n"
                "🟢 **Least Concern:** Deer, Wolf")

    return ("I'm your WildTrackAI assistant! I can help with:\n\n"
            "🔍 **Upload a footprint** for structured AI analysis\n"
            "🐾 **Ask about species** -- tiger, leopard, elephant, deer, wolf\n"
            "🧠 **Technical questions** -- model, Grad-CAM, accuracy\n"
            "🌍 **Conservation** -- status, tracking methods")


# ── Main Chat Response Generator ──────────────────────────────────

def generate_chat_response(message: str, prediction_result: dict = None, session_id: str = "default",
                           class_names: list = None) -> str:
    """Generate a contextual chat response using tiered intelligence."""
    if class_names is None:
        class_names = []
    session = _get_session(session_id)

    # Build context for Gemini
    context_parts = []

    if prediction_result:
        species = prediction_result.get("predicted_class", "unknown")
        confidence = prediction_result.get("confidence", 0)
        top3 = prediction_result.get("top3", [])
        is_unknown = prediction_result.get("is_unknown", False)
        raw_class = prediction_result.get("raw_class", species)

        context_parts.append("## Current Prediction Context")
        if is_unknown:
            context_parts.append(f"- **Result:** UNKNOWN (confidence {confidence*100:.1f}% is below threshold)")
            context_parts.append(f"- **Closest match (raw):** {raw_class}")
        else:
            context_parts.append(f"- **Predicted species:** {species}")
            context_parts.append(f"- **Confidence:** {confidence*100:.1f}%")

        if top3:
            context_parts.append("- **Top predictions:** " + ", ".join(
                f"{t['class']} ({t['confidence']*100:.1f}%)" for t in top3
            ))

        info = ANIMAL_INFO.get(raw_class if is_unknown else species, {})
        if info:
            context_parts.append(f"- **Species info:** {json.dumps({k: v for k, v in info.items() if k != 'description'}, default=str)}")

    if session["history"]:
        context_parts.append("\n## Recent Conversation")
        for h in session["history"][-3:]:
            context_parts.append(f"User: {h['user']}")
            context_parts.append(f"Bot: {h['bot']}")

    prediction_context = "\n".join(context_parts) if context_parts else ""

    # Tier 1: Try Gemini
    if gemini_model:
        try:
            import google.generativeai as genai
            user_prompt = message.strip() or "Analyze this footprint"
            if prediction_context:
                user_prompt = f"{prediction_context}\n\n**User message:** {user_prompt}"

            response = gemini_model.generate_content(
                [
                    {"role": "user", "parts": [f"System Instructions:\n{WILDTRACK_SYSTEM_PROMPT}"]},
                    {"role": "model", "parts": ["Understood. I'm the WildTrackAI assistant."]},
                    {"role": "user", "parts": [user_prompt]},
                ],
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000, temperature=0.7,
                ),
            )
            if response and response.text:
                result_text = response.text.strip()
                _update_session(session_id, message, result_text, prediction_result)
                return result_text
        except Exception as e:
            print(f"Gemini API error (falling back to local engine): {type(e).__name__}")

    # Tier 2: Structured Local Engine
    if prediction_result:
        result_text = _build_structured_prediction_response(prediction_result, class_names)
        _update_session(session_id, message, result_text, prediction_result)
        return result_text

    contextual = _handle_contextual_query(message, session)
    if contextual:
        _update_session(session_id, message, contextual)
        return contextual

    # Tier 3: Knowledge base fallback
    result_text = _generate_knowledge_response(message, class_names)
    _update_session(session_id, message, result_text)
    return result_text
