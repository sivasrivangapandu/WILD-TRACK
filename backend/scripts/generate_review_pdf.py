"""
WildTrack AI — Exhaustive Review PDF Generator
Generates a comprehensive academic review document covering every aspect
of the project: frontend logic, backend implementation, model training,
inference pipeline, database, authentication, and more.
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem,
    PageBreak, Table, TableStyle, KeepTogether
)

PAGE_W, PAGE_H = A4
ROOT = Path(r"d:\Wild Track AI")
OUT = ROOT / "WildTrackAI_Exhaustive_Review.pdf"

# ─── styles ───────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def _s(name, **kw):
    if name in [s.name for s in styles.byName.values()]:
        return
    styles.add(ParagraphStyle(name=name, **kw))

_s("CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
   fontSize=26, leading=32, alignment=TA_CENTER,
   textColor=colors.HexColor("#0f3b5c"), spaceAfter=6)
_s("CoverSub", parent=styles["Normal"], fontName="Helvetica",
   fontSize=13, leading=17, alignment=TA_CENTER,
   textColor=colors.HexColor("#4a6072"), spaceAfter=24)
_s("ChapterTitle", parent=styles["Heading1"], fontName="Helvetica-Bold",
   fontSize=17, leading=22, textColor=colors.HexColor("#0f3b5c"),
   spaceBefore=18, spaceAfter=10)
_s("SectionTitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
   fontSize=13, leading=17, textColor=colors.HexColor("#1a5276"),
   spaceBefore=12, spaceAfter=6)
_s("SubSection", parent=styles["Heading3"], fontName="Helvetica-Bold",
   fontSize=11, leading=15, textColor=colors.HexColor("#27678c"),
   spaceBefore=8, spaceAfter=4)
_s("Body", parent=styles["BodyText"], fontName="Helvetica",
   fontSize=10, leading=14, spaceAfter=5, alignment=TA_JUSTIFY)
_s("BodySmall", parent=styles["BodyText"], fontName="Helvetica",
   fontSize=9, leading=13, spaceAfter=4)
_s("Code", parent=styles["BodyText"], fontName="Courier",
   fontSize=8.5, leading=12, leftIndent=12, spaceAfter=4,
   backColor=colors.HexColor("#f4f6f8"), borderPadding=4)
_s("BulletText", parent=styles["BodyText"], fontName="Helvetica",
   fontSize=10, leading=13, leftIndent=4)
_s("TableHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
   fontSize=9, leading=12, textColor=colors.white)
_s("TableCell", parent=styles["Normal"], fontName="Helvetica",
   fontSize=9, leading=12)

# ─── helper functions ─────────────────────────────────────────────
story = []

def h1(text): story.append(Paragraph(text, styles["ChapterTitle"]))
def h2(text): story.append(Paragraph(text, styles["SectionTitle"]))
def h3(text): story.append(Paragraph(text, styles["SubSection"]))
def p(text):  story.append(Paragraph(text, styles["Body"]))
def ps(text): story.append(Paragraph(text, styles["BodySmall"]))
def code(text): story.append(Paragraph(text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"), styles["Code"]))
def sp(h=6): story.append(Spacer(1, h))

def bullets(items):
    elems = [ListItem(Paragraph(i, styles["BulletText"])) for i in items]
    story.append(ListFlowable(elems, bulletType="bullet", leftIndent=18, bulletFontSize=6))
    sp(4)

def numbered(items):
    elems = [ListItem(Paragraph(i, styles["BulletText"])) for i in items]
    story.append(ListFlowable(elems, bulletType="1", leftIndent=18))
    sp(4)

def table(headers, rows, col_widths=None):
    data = [[Paragraph(h, styles["TableHeader"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), styles["TableCell"]) for c in row])
    if col_widths is None:
        col_widths = [int((PAGE_W - 84) / len(headers))] * len(headers)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f9fafb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f9fafb"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    sp(6)

def page_break(): story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════
#  BUILD THE DOCUMENT
# ═══════════════════════════════════════════════════════════════════

# ─── Cover Page ───────────────────────────────────────────────────
sp(80)
story.append(Paragraph("WildTrack AI", styles["CoverTitle"]))
story.append(Paragraph("AI-Powered Wildlife Footprint Identification System", styles["CoverSub"]))
sp(12)
story.append(Paragraph("Exhaustive Project Review Document", styles["CoverSub"]))
sp(6)
story.append(Paragraph("Covering Every Aspect: Model Architecture, Training Pipeline,<br/>"
                        "Backend Implementation, Frontend Logic, Database Design,<br/>"
                        "Authentication, Deployment, and More", styles["CoverSub"]))
sp(30)
p("Upload a footprint image and get instant species identification, confidence scoring, Grad-CAM heatmap explanation, consensus validation, and wildlife insights.")
sp(20)
table(["Parameter", "Detail"],
      [["Domain", "Wildlife Conservation / Computer Vision"],
       ["Model", "EfficientNetB3 v4 (Transfer Learning)"],
       ["Dataset", "2,528 footprint images, 5 species"],
       ["Accuracy (TTA)", "77.5%"],
       ["Backend", "FastAPI + TensorFlow + SQLite"],
       ["Frontend", "React 18 + Vite + Tailwind CSS"],
       ["AI Chat", "Google Gemini 2.0 Flash"],
       ["Explainability", "Grad-CAM heatmaps"],
       ["Auth", "JWT + bcrypt"],
       ["Deployment", "Render / Vercel ready"]],
      col_widths=[170, 340])
page_break()

# ─── TABLE OF CONTENTS ───────────────────────────────────────────
h1("Table of Contents")
sp(4)
toc_items = [
    "Chapter 1: Project Overview and Problem Statement",
    "Chapter 2: Objectives",
    "Chapter 3: Dataset — Collection, Cleaning, and Augmentation",
    "Chapter 4: Model Architecture — EfficientNetB3 v4",
    "Chapter 5: Training Strategy — Three-Phase Pipeline",
    "Chapter 6: Loss Functions and Regularization",
    "Chapter 7: Test-Time Augmentation (TTA)",
    "Chapter 8: Multi-Stage Inference Pipeline",
    "Chapter 9: Consensus Validation System",
    "Chapter 10: Explainable AI — Grad-CAM Module",
    "Chapter 11: Embedding Extraction and Similarity Search",
    "Chapter 12: Backend Architecture — FastAPI Server (main.py)",
    "Chapter 13: Image Preprocessing Functions",
    "Chapter 14: Prediction Logic and Heuristics",
    "Chapter 15: API Endpoints — Complete Reference",
    "Chapter 16: Database Design — SQLAlchemy ORM Models",
    "Chapter 17: Authentication System — JWT and bcrypt",
    "Chapter 18: Chat Streaming Architecture",
    "Chapter 19: Chat Persistence Service",
    "Chapter 20: Model Service — Token Generation",
    "Chapter 21: Pydantic Schemas — Request/Response Validation",
    "Chapter 22: MLOps and Active Learning Routes",
    "Chapter 23: Frontend Architecture Overview",
    "Chapter 24: App Entry Point and Routing (App.jsx / main.jsx)",
    "Chapter 25: Context Providers — Theme, Auth, AppState",
    "Chapter 26: API Service Layer (api.js)",
    "Chapter 27: Page — Home (Landing Page)",
    "Chapter 28: Page — Upload (Core Prediction Interface)",
    "Chapter 29: Page — Dashboard (Analytics)",
    "Chapter 30: Page — Chat (AI Assistant)",
    "Chapter 31: Page — History (Prediction Browser)",
    "Chapter 32: Page — Species Explorer",
    "Chapter 33: Page — Batch Process",
    "Chapter 34: Page — Compare (Side-by-Side Analysis)",
    "Chapter 35: Page — Map Viewer (Leaflet + GBIF)",
    "Chapter 36: Page — MLOps Dashboard",
    "Chapter 37: Page — Settings",
    "Chapter 38: Page — Login/Register",
    "Chapter 39: Page — About",
    "Chapter 40: UI Components — Layout and Sidebar",
    "Chapter 41: UI Components — ProtectedRoute and ErrorBoundary",
    "Chapter 42: UI Components — Visual Primitives",
    "Chapter 43: UI Components — Loading, Skeleton, EmptyState",
    "Chapter 44: UI Components — Toast and Notifications",
    "Chapter 45: UI Components — ThemeSelector and ValidatedInput",
    "Chapter 46: Design System — global.css",
    "Chapter 47: Build Configuration — Vite, Tailwind, PostCSS",
    "Chapter 48: Technology Stack — Complete Reference",
    "Chapter 49: Deployment Architecture",
    "Chapter 50: Challenges, Solutions, and Innovation",
    "Chapter 51: Limitations and Future Scope",
    "Chapter 52: Conclusion and Viva Summary",
]
numbered(toc_items)
page_break()

# ═══════════════════════════════════════════════════════════════════
# CHAPTERS
# ═══════════════════════════════════════════════════════════════════

# ─── Chapter 1 ────────────────────────────────────────────────────
h1("Chapter 1: Project Overview and Problem Statement")
sp(4)
h2("1.1 Project Title")
p("WildTrack AI: AI-Powered Wildlife Footprint Identification System")
sp(4)
h2("1.2 Overview")
p("WildTrack AI is a full-stack AI application that identifies wild animals from photographs of their footprints. "
  "It combines a TensorFlow-based deep learning classifier, a FastAPI REST backend, a React single-page application, "
  "Grad-CAM explainability overlays, prediction history stored in SQLite, real-time analytics dashboards, "
  "JWT-secured authentication, and an AI chat assistant powered by Google Gemini.")
sp(4)
h2("1.3 Problem Statement")
p("Wildlife monitoring is fundamental to conservation biology, anti-poaching enforcement, and habitat management. "
  "Footprint identification — the art of determining species from track impressions left in soil, mud, sand, or snow — "
  "has been practiced for centuries by indigenous trackers and field biologists. However, this skill is:")
bullets([
    "Scarce: Fewer than a few thousand expert trackers exist worldwide for dozens of critical species.",
    "Slow: Manual identification in the field takes minutes per track set; surveying large territories is impractical.",
    "Inconsistent: Field conditions (lighting, soil, weather) introduce subjective variability.",
    "Non-digital: Paper-based records are difficult to aggregate, analyze, or share across organizations."
])
p("WildTrack AI addresses these problems by providing an automated, consistent, explainable, and scalable system "
  "that any field officer can use with a smartphone camera.")
sp(4)
h2("1.4 Motivation")
p("The International Union for Conservation of Nature (IUCN) lists tigers and Asian elephants as Endangered, "
  "and leopards as Vulnerable. Monitoring population trends through non-invasive footprint surveys is a recognized "
  "methodology (e.g., FIT — Footprint Identification Technique). Automating image-based footprint classification "
  "can dramatically increase the geographic scale and temporal frequency of such surveys.")
page_break()

# ─── Chapter 2 ────────────────────────────────────────────────────
h1("Chapter 2: Objectives")
h2("2.1 Main Objective")
p("Build a practical, explainable, and deployable system that classifies animal footprints into supported species "
  "and provides decision support through confidence scores, heatmaps, history, analytics, and AI-assisted interaction.")
h2("2.2 Specific Objectives")
numbered([
    "Develop a deep learning CNN that classifies footprint images into five species with at least 75% accuracy.",
    "Provide Grad-CAM heatmaps so users can verify which regions of the image influenced the prediction.",
    "Build a full-stack web application with a responsive, modern user interface accessible on desktop and mobile.",
    "Store every prediction in a database for auditing, trend analysis, and model improvement.",
    "Provide real-time analytics dashboards showing species distribution, confidence trends, and system health.",
    "Implement user authentication with secure password hashing and JWT tokens.",
    "Integrate an AI chatbot (Google Gemini) for wildlife educational support and prediction context.",
    "Implement a multi-stage inference pipeline with quality checks, YOLO detection, consensus validation, and confidence calibration.",
    "Design for production deployment with health checks, environment variables, and cloud-ready configuration.",
])
page_break()

# ─── Chapter 3 ────────────────────────────────────────────────────
h1("Chapter 3: Dataset — Collection, Cleaning, and Augmentation")
h2("3.1 Dataset Statistics")
table(["Species", "Images", "Conservation Status"],
      [["Tiger", "702", "Endangered"],
       ["Leopard", "492", "Vulnerable"],
       ["Elephant", "484", "Endangered"],
       ["Deer", "500", "Least Concern"],
       ["Wolf", "350", "Least Concern"],
       ["Total", "2,528", "—"]],
      col_widths=[160, 120, 230])
h2("3.2 Collection Method")
p("Images were collected from online sources using the iCrawler web scraping library (backend/scrape_dataset.py). "
  "Search queries targeted photographs of real animal footprints on natural substrates (mud, sand, snow, soil).")
h2("3.3 Multi-Stage Cleaning Pipeline")
p("Raw scraped images contain significant noise: drawings, cartoons, photos of the animal (not the footprint), "
  "duplicates, and severely blurry images. The project implements a multi-stage cleaning pipeline:")
numbered([
    "auto_clean.py — Automated cleaning using blur detection and perceptual hash deduplication.",
    "clean_dataset.py — Removes clearly non-footprint images based on heuristics.",
    "strict_filter_dataset.py — Applies stricter quality thresholds and removes edge cases.",
    "round2_clean.py — Second pass for remaining problematic images.",
    "review_dataset.py — Generates an HTML review page for manual human verification.",
])
p("Each cleaning stage produces a separate output directory (dataset_cleaned, dataset_strict, dataset_quarantine), "
  "allowing the training script to select the optimal dataset version.")
h2("3.4 Data Augmentation")
p("The training script applies multiple augmentation techniques on-the-fly during training:")
bullets([
    "Random rotation (up to 30 degrees)",
    "Random zoom (up to 20%)",
    "Horizontal and vertical flips",
    "Random brightness and contrast shifts",
    "Gaussian noise injection",
    "MixUp augmentation (alpha=0.3): Blends two images and their labels for smoother decision boundaries.",
    "CutMix augmentation (alpha=1.0): Cuts a rectangular patch from one image and pastes it on another.",
    "Progressive resizing: Training starts at 224x224 and increases to 300x300 as an implicit regularizer.",
])
h2("3.5 Why This Dataset Is Challenging")
bullets([
    "Footprint appearance varies drastically with soil type, moisture, angle, depth, and lighting.",
    "Some species have similar prints (leopard vs tiger, wolf vs dog).",
    "Class imbalance: Wolf has 350 images while Tiger has 702.",
    "Images from the internet may include non-standard framing, watermarks, or low resolution.",
])
page_break()

# ─── Chapter 4 ────────────────────────────────────────────────────
h1("Chapter 4: Model Architecture — EfficientNetB3 v4")
h2("4.1 Why EfficientNetB3")
p("EfficientNet uses compound scaling to optimize network depth, width, and input resolution simultaneously. "
  "EfficientNetB3 offers the best accuracy-to-computation trade-off for medium-sized datasets (1,000–5,000 images). "
  "It was pre-trained on ImageNet (14 million images, 1,000 classes), giving strong initial feature extraction capabilities.")
h2("4.2 Architecture Diagram")
code("Input Image (300 x 300 x 3 RGB)\n"
     "        |\n"
     "  EfficientNetB3 Backbone (ImageNet weights, frozen initially)\n"
     "        |\n"
     "  Squeeze-and-Excitation (SE) Attention Block\n"
     "        |\n"
     "  Global Average Pooling 2D\n"
     "        |\n"
     "  Dense(512, ReLU) -> BatchNorm -> Dropout(0.4)\n"
     "        |\n"
     "  Dense(256, ReLU) -> BatchNorm -> Dropout(0.3)\n"
     "        |\n"
     "  Dense(5, Softmax) -> Species Probability Distribution")
h2("4.3 Squeeze-and-Excitation (SE) Attention")
p("The SE block learns to re-weight each feature channel based on its importance. "
  "After Global Average Pooling, a small network (Dense -> ReLU -> Dense -> Sigmoid) produces per-channel weights (0–1). "
  "These weights are multiplied element-wise with the original features, allowing the model to emphasize "
  "informative channels (e.g., pad shape detectors) and suppress irrelevant ones (e.g., background texture).")
h2("4.4 Custom Head Design")
p("The classification head uses two Dense layers with BatchNormalization and Dropout between them. "
  "BatchNorm stabilizes training by normalizing activations. Dropout randomly zeros neurons during training "
  "to prevent co-adaptation, acting as an ensemble of sub-networks.")
h2("4.5 Input Preprocessing")
p("EfficientNetB3 expects RGB images in the [0, 255] range (not [0, 1]). The training script uses tf.data pipelines "
  "with tf.image.resize for resizing and tf.cast(float32) for type conversion. No additional normalization is applied; "
  "EfficientNet has internal preprocessing layers.")
page_break()

# ─── Chapter 5 ────────────────────────────────────────────────────
h1("Chapter 5: Training Strategy — Three-Phase Pipeline")
h2("5.1 Phase 1: Head Training (20 epochs)")
p("The EfficientNetB3 backbone is completely frozen (all layers set to trainable=False). "
  "Only the custom head layers (Dense, BatchNorm, Dropout) are trained. This prevents catastrophic forgetting "
  "of the pre-trained ImageNet features while the head learns to map backbone features to the 5 footprint classes.")
p("Optimizer: AdamW. Learning rate: 1e-3. Image size: 224x224 (warmup resolution).")
h2("5.2 Phase 2: Fine-Tuning (20 epochs)")
p("The last 80 layers of EfficientNetB3 are unfrozen. The learning rate is reduced to 1e-4 with cosine annealing "
  "(SGDR — Stochastic Gradient Descent with Warm Restarts). The model adapts pre-trained features to footprint-specific "
  "patterns: pad shapes, toe configurations, claw marks, and substrate textures.")
p("Image size transitions to 300x300 (progressive resizing).")
h2("5.3 Phase 3: Deep Fine-Tune + SWA (15 epochs)")
p("All layers are trainable. Learning rate is further reduced. Stochastic Weight Averaging (SWA) is applied: "
  "the optimizer maintains a running average of weights across training steps, producing a model that sits in a flatter "
  "region of the loss landscape — improving generalization to unseen footprints.")
h2("5.4 Callbacks Used")
bullets([
    "EarlyStopping: Stops training if validation loss does not improve for a configurable patience period.",
    "ModelCheckpoint: Saves the best model weights based on validation accuracy.",
    "ReduceLROnPlateau: Reduces learning rate when validation loss plateaus.",
    "TensorBoard: Logs training and validation metrics for visualization.",
])
page_break()

# ─── Chapter 6 ────────────────────────────────────────────────────
h1("Chapter 6: Loss Functions and Regularization")
h2("6.1 Focal Loss")
p("Focal Loss was introduced by Lin et al. (2017) for object detection on imbalanced datasets. "
  "It modifies cross-entropy by adding a modulating factor (1 - p_t)^gamma that down-weights well-classified examples.")
code("FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)\n\ngamma = 2.0 (default)\nalpha = class-frequency-based weights")
p("When an example is correctly classified with high confidence (p_t close to 1), the (1-p_t)^gamma factor approaches zero, "
  "reducing the loss contribution. Misclassified or hard examples (p_t close to 0) retain full loss magnitude.")
h2("6.2 Label Smoothing")
p("Instead of one-hot labels [0, 0, 1, 0, 0], label smoothing uses soft targets like [0.02, 0.02, 0.92, 0.02, 0.02]. "
  "This prevents the model from becoming overconfident on training examples and improves calibration. "
  "The project uses smoothing factor epsilon = 0.1.")
h2("6.3 Dropout")
p("Dropout(0.4) after the first Dense layer and Dropout(0.3) after the second. During training, 40% and 30% "
  "of neurons are randomly set to zero, forcing the network to learn redundant representations.")
h2("6.4 Weight Decay (AdamW)")
p("AdamW applies L2 regularization (weight decay) decoupled from the adaptive learning rate mechanism. "
  "This penalizes large weights, reducing overfitting on limited training data.")
page_break()

# ─── Chapter 7 ────────────────────────────────────────────────────
h1("Chapter 7: Test-Time Augmentation (TTA)")
p("TTA improves prediction robustness by making multiple augmented forward passes through the model at inference time "
  "and averaging the resulting probability distributions.")
h2("7.1 How TTA Works in WildTrack AI")
numbered([
    "The input image is augmented N times (default N=3) with random flips and small rotations.",
    "Each augmented version is fed through the model independently.",
    "The softmax probability vectors from all passes are averaged element-wise.",
    "The averaged probabilities produce a more stable and accurate prediction.",
])
h2("7.2 Why TTA Helps")
p("A single forward pass can be sensitive to the exact orientation and framing of the footprint. "
  "TTA simulates different perspectives, reducing variance and improving the expected accuracy by 2–5%.")
page_break()

# ─── Chapter 8 ────────────────────────────────────────────────────
h1("Chapter 8: Multi-Stage Inference Pipeline")
p("File: backend/pipeline.py")
p("Instead of a simple image-in/label-out classifier, WildTrack AI uses a multi-stage inference pipeline "
  "implemented in the InferencePipeline class.")
h2("8.1 Stage 0: Data Quality Gate")
p("<b>Blur Detection</b>: Computes the Laplacian variance of the grayscale image. The Laplacian operator highlights edges; "
  "blurry images have low variance. Images with blur_level below a threshold are flagged with a quality warning.")
p("<b>Perceptual Hash (pHash)</b>: Computes a 64-bit hash of the image's frequency content. If the hash matches "
  "a recently seen image, a duplicate flag is set, preventing redundant inference.")
h2("8.2 Stage 1: YOLO Object Detection (Optional)")
p("If a YOLO model is loaded, it detects footprint regions in the image and crops to the highest-confidence bounding box "
  "with a configurable expansion margin (default 15%). This removes background clutter that can confuse the classifier.")
h2("8.3 Stage 2: EfficientNetB3 Classifier")
p("The preprocessed image (300x300 RGB float32) is passed through the classifier with TTA. "
  "The output is a probability distribution over 5 classes.")
h2("8.4 Stage 3: Geo-Aware Filtering")
p("If GPS coordinates are provided, the pipeline applies geographic constraints. "
  "For example, tiger probabilities are zeroed in Africa (where tigers do not exist), "
  "and elephant probabilities are zeroed outside Africa/Asia. "
  "Probabilities are re-normalized after zeroing.")
h2("8.5 Stage 4: Temperature Scaling (Confidence Calibration)")
p("Raw softmax outputs tend to be overconfident. Temperature scaling divides logits by T=1.2 before re-applying softmax:")
code("calibrated = softmax(logits / T)\n\nT > 1 makes the distribution softer (less overconfident)\nT < 1 makes it sharper")
p("This produces better-calibrated confidence scores that more accurately reflect the true probability of being correct.")
page_break()

# ─── Chapter 9 ────────────────────────────────────────────────────
h1("Chapter 9: Consensus Validation System")
p("File: backend/consensus.py")
p("WildTrack AI implements a consensus module that simulates a 'second opinion' by comparing two prediction paths:")
bullets([
    "Path A (Primary): TTA-augmented, temperature-calibrated prediction.",
    "Path B (Second Opinion): Single-pass prediction without TTA.",
])
h2("9.1 Agreement Analysis")
p("The module computes: whether both paths agree on the top class, the disagreement score (absolute confidence difference), "
  "the cross-confidence (what Path B thinks about Path A's choice), and whether confidences are stable (difference < 0.15).")
h2("9.2 Verdict Levels")
table(["Verdict", "Condition"],
      [["Verified Detection", "Both agree, primary >= 75%, stable confidence"],
       ["Consensus Reached", "Both agree, primary >= 60%"],
       ["Weak Consensus", "Both agree but low confidence"],
       ["Primary Dominant", "Disagree but primary >= 70% and cross-confidence >= 50%"],
       ["Ambiguous - Requires Review", "Both disagree"],
       ["Insufficient Confidence", "Below threshold entirely"]],
      col_widths=[180, 330])
h2("9.3 Output Structure")
p("The consensus module returns a dictionary containing: primary_prediction, primary_confidence, "
  "second_opinion_prediction, second_opinion_confidence, agreement (bool), disagreement_score, "
  "cross_confidence, confidence_stable, alternative (if disagreement), verdict, and verdict_level.")
page_break()

# ─── Chapter 10 ───────────────────────────────────────────────────
h1("Chapter 10: Explainable AI — Grad-CAM Module")
p("File: backend/gradcam_module.py")
h2("10.1 What Is Grad-CAM")
p("Gradient-weighted Class Activation Mapping (Grad-CAM) produces a heatmap that highlights which spatial regions "
  "of the input image most influenced the model's prediction. It works by computing the gradients of the predicted class score "
  "with respect to the last convolutional layer's feature maps, then weighting each feature map by its gradient importance.")
h2("10.2 Implementation Details")
numbered([
    "Auto-detection: The GradCAM class automatically finds the base model (EfficientNetB3) and the last Conv2D layer within it.",
    "Head layer tracking: It identifies all layers after the base model (Dense, BatchNorm, Dropout, Multiply) and replays them during gradient computation.",
    "SE Attention handling: The Multiply layer in the SE attention block requires special multi-input handling. The implementation saves the GAP output and passes it as a second input to Multiply.",
    "GradientTape: TensorFlow's GradientTape API computes gradients of the predicted class score w.r.t. the conv feature maps.",
    "Heatmap generation: Gradients are globally averaged, multiplied with feature maps, summed, ReLU'd, and normalized to [0, 1].",
    "Overlay: The heatmap is resized to the original image dimensions, colored with the JET colormap, and blended with the original image using configurable alpha.",
    "Confidence-adaptive intensity: Low-confidence predictions get weaker heatmap overlays (alpha scales from 0.15 to 0.4).",
    "Low confidence watermark: Images with confidence below 50% get a 'LOW CONFIDENCE' text watermark.",
    "Output: The overlaid image is JPEG-encoded and returned as a base64 string for API transmission.",
])
page_break()

# ─── Chapter 11 ───────────────────────────────────────────────────
h1("Chapter 11: Embedding Extraction and Similarity Search")
p("File: backend/embedding_module.py")
p("The EmbeddingExtractor class extracts feature vectors from the penultimate Dense layer of the model.")
h2("11.1 Embedding Model Construction")
p("The module introspects the model's layers, finds all Dense layers, and creates a sub-model "
  "that outputs the second-to-last Dense layer's activations. If fewer than 2 Dense layers exist, "
  "it falls back to the GlobalAveragePooling2D output.")
h2("11.2 L2 Normalization")
p("Extracted embeddings are L2-normalized (divided by their Euclidean norm), ensuring unit-length vectors "
  "suitable for cosine similarity comparison.")
h2("11.3 Similarity Search")
p("The cosine_similarity static method computes the dot product between two L2-normalized vectors (equivalent to cosine similarity). "
  "The find_most_similar method compares a query embedding against a collection of stored embeddings "
  "and returns the top-K most similar results, sorted by similarity score.")
page_break()

# ─── Chapter 12 ───────────────────────────────────────────────────
h1("Chapter 12: Backend Architecture — FastAPI Server (main.py)")
p("File: backend/main.py (~1200 lines)")
h2("12.1 Server Configuration")
bullets([
    "Framework: FastAPI with ASGI server Uvicorn",
    "CORS: Allows all origins (configured for development; restrict in production)",
    "Middleware: CORSMiddleware with wildcard allow_origins, allow_methods, allow_headers",
    "Lifespan: Uses asynccontextmanager to load the model once at startup",
    "Static files: Serves uploaded avatar images from /uploads/ directory",
    "Database: SQLite via SQLAlchemy; initialized at startup via init_db()",
])
h2("12.2 Model Loading Strategy")
p("The load_model() function implements a robust multi-fallback loading strategy:")
numbered([
    "Download missing models from GitHub Releases (for cloud deployment) with retry logic and exponential backoff.",
    "Try loading in order: .keras format first, then .h5 variants (v4, complete, final, v3).",
    "Register custom objects for deserialization: MobileNetPreprocess layer, FocalLoss, TrueDivide.",
    "Load model metadata from model_metadata.json for class names, image size, accuracy, and version.",
    "Initialize GradCAM with the loaded model.",
    "Store diagnostic information about which file was loaded and any errors encountered.",
])
h2("12.3 External Service Integration")
bullets([
    "Google Gemini AI: Initialized via GEMINI_API_KEY environment variable. Used for the chat endpoint.",
    "API Ninjas: Initialized via NINJA_API_KEY. Provides animal search for the species explorer.",
    "Cloudinary: Configured via CLOUDINARY_URL or individual credentials. Stores prediction images in the cloud.",
])
h2("12.4 Animal Information Database")
p("ANIMAL_INFO is a Python dictionary containing detailed information for 10 species: "
  "tiger, leopard, elephant, deer, wolf, fox, dog, cat, hyena, and bear. "
  "Each entry includes: scientific_name, conservation_status, weight, footprint_size, habitat, description, and distribution.")
h2("12.5 Router Registration")
p("The app registers four routers: chat_router (/api/chat), chat_db_router (/api/chat), "
  "auth_router (/api/auth), and mlops_router (/mlops).")
page_break()

# ─── Chapter 13 ───────────────────────────────────────────────────
h1("Chapter 13: Image Preprocessing Functions")
p("The backend implements several image processing utilities that work together in the preprocessing pipeline.")
h2("13.1 Blur Detection (detect_blur)")
p("Converts to grayscale, computes Laplacian (second derivative) of the image, and measures variance. "
  "Higher variance means sharper edges. The blur_level is scaled to 0–100 for interpretability.")
h2("13.2 Quality Warning Generation (generate_quality_warning)")
p("Maps blur_level to human-readable warnings with severity levels:")
table(["Blur Level", "Severity", "Message"],
      [[">=75", "None", "Sharp image, no warning"],
       ["60-74", "Caution", "Moderate clarity, retake suggested"],
       ["45-59", "Warning", "Significantly blurry, field validation recommended"],
       ["<45", "Critical", "Severely blurry, prediction should not be trusted"]],
      col_widths=[80, 80, 350])
h2("13.3 Contrast Enhancement (normalize_contrast)")
p("Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to the L-channel of LAB color space. "
  "This enhances local contrast without oversaturation — critical for footprints on low-contrast substrates.")
h2("13.4 Edge Enhancement (enhance_edges)")
p("Applies unsharp masking: subtracts a Gaussian-blurred version from the original, multiplied by a gain factor (1.4). "
  "This sharpens pad and toe boundaries without introducing ringing artifacts.")
h2("13.5 Brightness/Gamma Correction (correct_brightness_gamma)")
p("Detects mean luminance from the L-channel. If below thresholds (85, 100, 115), "
  "applies gamma correction: output = (input/255)^(1/gamma) * 255. "
  "Critical for photos taken in dark forest conditions.")
h2("13.6 Intelligent Resize (intelligent_resize)")
p("Resizes while preserving aspect ratio by fitting the image into a square canvas centered with neutral gray padding.")
h2("13.7 Main Preprocessing Function (preprocess_image)")
p("This function matches the training pipeline exactly to avoid domain gap:")
numbered([
    "Decode image from bytes with OpenCV (gives BGR).",
    "Collect quality metrics (blur, pHash, brightness) — does NOT modify the image.",
    "Run Stage 1 YOLO detection if available.",
    "Convert BGR to RGB (TensorFlow training used RGB).",
    "Letterbox resize: Scale to fit target_size maintaining aspect ratio, center on gray canvas.",
    "Cast to float32 [0, 255] — no rescaling to [0, 1].",
    "Return preprocessed array, original image, quality metrics, and YOLO metadata.",
])
page_break()

# ─── Chapter 14 ───────────────────────────────────────────────────
h1("Chapter 14: Prediction Logic and Heuristics")
h2("14.1 predict_single() Function")
p("The core prediction function applies TTA, temperature scaling, entropy calculation, "
  "quality-adjusted confidence, and consensus validation.")
h2("14.2 Unknown Detection (Dual Threshold)")
p("A prediction is marked 'unknown' only when BOTH conditions are met:")
bullets([
    "Confidence < 0.40 (40% — the minimum acceptable confidence)",
    "Entropy ratio > 0.90 (90% of maximum entropy — the model is nearly uniformly uncertain)",
])
p("This dual-threshold approach prevents false 'unknown' flags for genuinely low-confidence but still informative predictions.")
h2("14.3 Quality-Adjusted Confidence")
p("The raw confidence is penalized based on image quality:")
bullets([
    "Critical blur (blur_level < 45): Confidence multiplied by 0.75",
    "Moderate blur (blur_level < 60): Confidence multiplied by 0.90",
    "Gamma correction applied: Confidence multiplied by 0.95",
])
h2("14.4 Snow Track Heuristic")
p("Wolf/canine tracks in snow lose claw marks and are frequently misclassified as leopards. "
  "The system detects this scenario by checking:")
bullets([
    "Predicted class is leopard or tiger",
    "Wolf is in top-3 with confidence > 15%",
    "Image brightness > 130 (indicative of snow or overexposure)",
])
p("When all conditions are met, the prediction is corrected to wolf.")
h2("14.5 Dynamic Crop Re-evaluation")
p("If YOLO was used and the initial prediction is low-confidence (<60%) for an ambiguous species (leopard, wolf, tiger, etc.), "
  "a second pass runs without the expansion margin. If the fallback yields higher confidence, it replaces the original result.")
h2("14.6 Active Learning Flagging")
p("Predictions below the confidence threshold or marked as unknown are flagged with needs_review=1 "
  "in the database for human-in-the-loop review via the MLOps interface.")
page_break()

# ─── Chapter 15 ───────────────────────────────────────────────────
h1("Chapter 15: API Endpoints — Complete Reference")
table(["Method", "Endpoint", "Description"],
      [["GET/HEAD", "/", "Root — service info and available endpoints"],
       ["GET/HEAD", "/health", "System health with model status and diagnostics"],
       ["GET", "/ready", "Readiness probe (503 if model not loaded)"],
       ["GET", "/api/system/status", "Production status — version, accuracy, uptime"],
       ["POST", "/predict", "Single image prediction with full pipeline"],
       ["POST", "/predict/batch", "Batch prediction for multiple images"],
       ["GET", "/species", "List all supported species with details"],
       ["GET", "/species/{name}", "Detail for a specific species"],
       ["POST", "/species-search", "AI-powered species search (Gemini)"],
       ["GET", "/history", "Paginated prediction history with filters"],
       ["GET", "/analytics", "Dashboard statistics and charts data"],
       ["GET", "/model-metrics", "Model performance metrics"],
       ["POST", "/chat", "Legacy chat endpoint (FormData)"],
       ["POST", "/api/chat/stream", "NDJSON streaming chat with Gemini"],
       ["POST", "/api/chat/save", "Persist completed chat exchange"],
       ["POST", "/api/chat/sessions", "Create new chat session"],
       ["GET", "/api/chat/sessions", "List user's chat sessions"],
       ["GET", "/api/chat/sessions/{id}", "Get session with messages"],
       ["DELETE", "/api/chat/sessions/{id}", "Delete chat session"],
       ["GET", "/api/chat/metrics", "Chat service performance metrics"],
       ["GET", "/api/chat/health", "Chat service health check"],
       ["POST", "/api/auth/register", "Create new user account"],
       ["POST", "/api/auth/login", "Authenticate and get JWT"],
       ["GET", "/api/auth/me", "Get current user from token"],
       ["PUT", "/api/auth/profile", "Update user name"],
       ["PUT", "/api/auth/password", "Change password"],
       ["POST", "/api/auth/avatar", "Upload profile picture"],
       ["PUT", "/api/auth/notifications", "Update notification preferences"],
       ["DELETE", "/api/auth/account", "Delete user account"],
       ["GET", "/mlops/review-queue", "Get items needing human review"],
       ["POST", "/mlops/review/{id}", "Submit human review decision"],
       ["GET", "/mlops/analytics", "MLOps analytics and statistics"],
       ["POST", "/report", "Generate downloadable PDF report"]],
      col_widths=[60, 170, 280])
page_break()

# ─── Chapter 16 ───────────────────────────────────────────────────
h1("Chapter 16: Database Design — SQLAlchemy ORM Models")
h2("16.1 Database Configuration (database.py)")
p("Uses SQLite with SQLAlchemy ORM. The database file (wildtrack.db) is stored in the backend directory. "
  "Connection pooling is configured with check_same_thread=False for FastAPI's async context.")
h2("16.2 Prediction Model (prediction_model.py)")
table(["Column", "Type", "Description"],
      [["id", "String PK", "UUID4 (8 chars)"],
       ["species", "String", "Predicted species name"],
       ["confidence", "Float", "Prediction confidence (0-1)"],
       ["top3", "Text (JSON)", "Top 3 predictions serialized"],
       ["timestamp", "DateTime", "UTC prediction timestamp"],
       ["image_path", "String", "Cloudinary URL or local path"],
       ["filename", "String", "Original upload filename"],
       ["heatmap_generated", "Integer", "1 if Grad-CAM was generated"],
       ["latitude", "Float", "GPS latitude (optional)"],
       ["longitude", "Float", "GPS longitude (optional)"],
       ["model_version", "String", "e.g., 'v4'"],
       ["dataset_version", "String", "e.g., 'v1.2-cleaned'"],
       ["accuracy_benchmark", "String", "Benchmark accuracy string"],
       ["is_rejected", "Integer", "1 if auto-rejected (severe blur)"],
       ["needs_review", "Integer", "1 if flagged for HITL review"]],
      col_widths=[120, 100, 290])

h2("16.3 User Model (user_model.py)")
table(["Column", "Type", "Description"],
      [["id", "String PK", "UUID4"],
       ["name", "String(120)", "Display name"],
       ["email", "String(255)", "Unique, indexed"],
       ["hashed_password", "String(255)", "bcrypt hash"],
       ["avatar_url", "Text", "Cloudinary avatar URL"],
       ["role", "String(30)", "Default: 'researcher'"],
       ["is_active", "Boolean", "Account enabled/disabled"],
       ["notify_predictions", "Boolean", "Prediction alerts"],
       ["notify_updates", "Boolean", "App update notifications"],
       ["notify_emails", "Boolean", "Email notifications"],
       ["created_at", "DateTime", "Account creation UTC"],
       ["updated_at", "DateTime", "Last modification UTC"]],
      col_widths=[130, 100, 280])

h2("16.4 Chat Models (chat_models.py)")
p("Two related models implement the chat persistence layer:")
p("<b>ChatSession</b>: id (PK), user_id (indexed), title, created_at, updated_at. "
  "Has a one-to-many relationship with ChatMessage (cascade delete).")
p("<b>ChatMessage</b>: id (PK), session_id (FK to ChatSession, cascade), role (user/assistant), "
  "content (Text), token_count, duration_ms, created_at.")
page_break()

# ─── Chapter 17 ───────────────────────────────────────────────────
h1("Chapter 17: Authentication System — JWT and bcrypt")
p("File: backend/auth.py")
h2("17.1 Password Hashing")
p("Passwords are hashed using bcrypt with a random salt. bcrypt is a CPU-intensive hash function designed to be slow, "
  "making brute-force attacks impractical. The hash_password function encodes the plaintext to UTF-8, "
  "generates a salt via bcrypt.gensalt(), and returns the hash as a string.")
h2("17.2 JWT Token Flow")
numbered([
    "User submits credentials (email + password) to POST /api/auth/login.",
    "Backend verifies password against stored bcrypt hash.",
    "On success, create_access_token generates a JWT with payload {sub: user_id, exp: now + 24h}.",
    "JWT is signed with HS256 using a secret key from JWT_SECRET environment variable.",
    "Frontend stores token in localStorage under key 'wildtrack_token'.",
    "On each API request, the Axios interceptor attaches the token as Authorization: Bearer header.",
    "Protected endpoints call get_current_user which decodes the JWT and loads the user from the database.",
    "If the token is expired or invalid, the backend returns 401 and the frontend auto-clears localStorage.",
])
h2("17.3 Auth Routes")
p("Registration validates name length (>=2) and password length (>=6). "
  "Login checks email existence and password match. Avatar upload validates MIME type "
  "(JPEG/PNG/WebP/GIF) and file size (<= 5 MB).")
page_break()

# ─── Chapter 18 ───────────────────────────────────────────────────
h1("Chapter 18: Chat Streaming Architecture")
p("Files: backend/routes/chat.py, backend/services/model_service.py")
h2("18.1 NDJSON Streaming Protocol")
p("The chat uses Newline-Delimited JSON (NDJSON) for streaming. Each line is a JSON object with a 'type' field:")
table(["Event Type", "Payload"],
      [["start", "{}"],
       ["token", "{content: 'word '}"],
       ["complete", "{}"],
       ["error", "{message: '...'}"]],
      col_widths=[120, 390])
h2("18.2 Server-Side Flow")
numbered([
    "POST /api/chat/stream receives the message and session_id.",
    "stream_with_metrics is an async generator that yields NDJSON events.",
    "It calls get_model_tokens which is also an async generator yielding individual tokens.",
    "StreamingResponse sends tokens as they are generated (no buffering).",
    "Metrics (request count, token count, latency) are recorded after completion.",
])
h2("18.3 Client-Side Streaming (Chat.jsx)")
numbered([
    "Frontend calls fetch() with the stream endpoint (not Axios, because Axios does not support streaming).",
    "Response body is read via reader.read() using TextDecoder.",
    "Each accumulated line is parsed as JSON.",
    "Token events are batched with requestAnimationFrame to prevent excessive re-renders.",
    "Accumulated text is stored in a React ref (not state) during streaming for performance.",
    "On 'complete' event, the final accumulated text is committed to React state.",
    "The completed exchange is saved to the backend via POST /api/chat/save.",
    "AbortController.abort() is used to cancel in-flight streaming requests.",
])
h2("18.4 Token Generation (model_service.py)")
p("The service contains a comprehensive knowledge base with species profiles, field tips, and domain-specific responses. "
  "The _build_response function prioritizes: (1) prediction context analysis, (2) topic matching (GradCAM, model, conservation), "
  "(3) species-specific queries, (4) general wildlife responses. "
  "When Google Gemini is configured, the actual Gemini model generates responses instead of the rule-based system.")
page_break()

# ─── Chapter 19-22 ────────────────────────────────────────────────
h1("Chapter 19: Chat Persistence Service")
p("File: backend/services/chat_persistence.py")
p("The save_chat_to_db function creates or finds the chat session, inserts both user and assistant messages "
  "with timestamped IDs, auto-generates a title from the first 5 words of the user's message, "
  "updates the session's updated_at timestamp, and commits the transaction.")

h1("Chapter 20: Model Service — Token Generation")
p("File: backend/services/model_service.py")
p("Contains SPECIES_PROFILES dictionary with 5 species entries (tiger, leopard, elephant, deer, wolf), "
  "each with: name, sci (scientific name), tracks (morphological description), habitat, behavior, conservation, and field_tips. "
  "GENERAL_TOPICS dictionary covers gradcam, model, conservation, and unknown interpretation.")
p("The ModelMetrics class tracks: total_requests, successful, failed, total_tokens, total_latency_ms, "
  "and provides a get_summary method. The async get_model_tokens generator yields space-split tokens "
  "with random delays (30-80ms) simulating typing speed.")

h1("Chapter 21: Pydantic Schemas — Request/Response Validation")
p("File: backend/schemas/chat_schemas.py")
p("Defines type-safe request/response models: ChatStreamRequest (message, session_id, context), "
  "SaveChatRequest (session_id, user_id, user_message, assistant_response, token_count, duration_ms), "
  "SaveChatResponse, ContextData (elevation, habitat, timestamp, metadata), "
  "and stream event types (StreamEventStart, StreamEventToken, StreamEventComplete, StreamEventError).")

h1("Chapter 22: MLOps and Active Learning Routes")
p("File: backend/routes/mlops.py")
h2("22.1 Review Queue")
p("GET /mlops/review-queue returns predictions flagged with needs_review=1, sorted by lowest confidence first.")
h2("22.2 Human Review (approve/reject/correct)")
p("POST /mlops/review/{pred_id} accepts an action (approve, reject, correct). "
  "On 'correct', the image is copied to dataset_hard_negatives/{species}/ with an 'hn_' prefix — "
  "this is active learning: hard negatives are accumulated for the next training cycle.")
h2("22.3 MLOps Analytics")
p("GET /mlops/analytics returns total_predictions, total_rejected, total_needs_review, rejection_rate, "
  "hard_negatives_mined count, and average_confidence_by_species.")
page_break()

# ─── Chapter 23-26 ────────────────────────────────────────────────
h1("Chapter 23: Frontend Architecture Overview")
p("The frontend is a React 18 single-page application built with Vite 5. It uses:")
bullets([
    "React Router 6 for client-side routing with 13 named routes",
    "Three Context providers: ThemeContext (theme + dark mode), AuthContext (user + JWT), AppStateContext (upload state + chat state)",
    "Axios HTTP client wrapped in a service layer (api.js) with JWT interceptor and auto-logout on 401",
    "Framer Motion for page transitions, hover effects, staggered reveals, and layout animations",
    "Tailwind CSS 3 with token-based custom properties for multi-theme dark-mode support",
    "Recharts for pie charts, bar charts, line charts, and radar charts",
    "Leaflet + react-leaflet for interactive map visualization",
    "react-webcam for camera capture on mobile devices",
    "react-syntax-highlighter for code blocks in chat",
    "Progressive Web App (PWA) support via vite-plugin-pwa",
])

h1("Chapter 24: App Entry Point and Routing")
p("File: frontend/src/main.jsx — Wraps App in React.StrictMode and ThemeProvider.")
p("File: frontend/src/App.jsx — Wraps everything in ErrorBoundary > Router > AuthProvider > AppStateProvider > Layout. "
  "Defines 13 routes, all wrapped in ProtectedRoute except /login. Unknown routes redirect to /.")

h1("Chapter 25: Context Providers")
h2("25.1 ThemeContext")
p("Manages 6 themes (sunset/safari, ocean, forest, lavender, rose, midnight) — each with 11 CSS token values "
  "(primary, secondary, accent, bg, bgSecondary, surface1, surface2, text, gradient, glow). "
  "Persists theme choice and dark/light mode in localStorage. Injects CSS custom properties into document.documentElement.")
h2("25.2 AuthContext")
p("Manages user state, login, register, logout, and refreshUser functions. On mount, validates the stored JWT "
  "by calling GET /api/auth/me — if invalid, clears localStorage. Resolves relative avatar URLs to absolute.")
h2("25.3 AppStateContext")
p("Provides shared upload state (file, preview, result, loading, error, showHeatmap) and chat state (isOpen, messages, sessionId) "
  "across components. Used by Upload.jsx and other pages that need to share prediction context.")

h1("Chapter 26: API Service Layer (api.js)")
p("File: frontend/src/services/api.js")
p("Creates an Axios instance with: smart baseURL fallback (localhost for dev, Render URL for prod), "
  "120-second timeout, JWT Authorization header interceptor, and auto-logout on 401 responses.")
p("Exposes 30+ API methods organized by domain: auth (register, login, getMe, updateProfile, changePassword, uploadAvatar, "
  "updateNotifications, deleteAccount), predictions (predict, predictBatch), species (getSpecies, getSpeciesDetail, searchSpecies), "
  "history (getHistory), analytics (getAnalytics, getModelMetrics, getSystemStatus), "
  "chat (streamChat, saveStreamedChat, createChatSession, listChatSessions, getChatSession, deleteChatSession), "
  "and MLOps (getReviewQueue, submitReview, getMlopsAnalytics).")
page_break()

# ─── Chapters 27-39: Pages ────────────────────────────────────────
h1("Chapter 27: Page — Home (Landing Page)")
p("File: frontend/src/pages/Home.jsx (~130 lines)")
p("Fetches analytics + model metrics on mount via Promise.all. Renders: animated gradient hero title, "
  "4 stat cards (total predictions, species tracked, model accuracy, confidence), 6 feature cards, "
  "5 species cards with conservation status, 4-step how-it-works flow, and CTA banner.")
p("Uses animate-text-shimmer CSS for hero title gradient animation. All cards have whileHover scale on motion.div.")

h1("Chapter 28: Page — Upload (Core Prediction Interface)")
p("File: frontend/src/pages/Upload.jsx (~860 lines)")
p("The largest functional page. Manages drag-and-drop file selection, camera capture toggle, "
  "calls api.predict(), and renders an extensive results interface.")
h2("28.1 State Management")
p("Uses AppStateContext for shared state. Local state: dragActive (drag highlight), location (GPS coords via navigator.geolocation).")
h2("28.2 Track Morphology Panel")
p("Defines TRACK_MORPHOLOGY constant with per-species data: toeCount, clawMarks, heelPad, symmetry, family, "
  "trackWidth, gait, distinguishing. Renders a labeled grid of these traits for the predicted species.")
h2("28.3 Analysis Animation")
p("During prediction loading, shows a 4-step progressive animation: Preprocessing, Feature Extraction, "
  "Classification, Calibration — each with its own gradient background and animated progress indicators.")
h2("28.4 Species Background Portal")
p("Uses ReactDOM.createPortal to render a full-page animated gradient background (behind all content) "
  "themed to the predicted species. CSS keyframes animate the gradient position in a continuous cycle.")
h2("28.5 Results Display")
p("Renders ConfidenceRing (SVG gauge), species name + confidence, model/TTA badges, "
  "reliability verdict (4-tier), confidence bar with gradient fill, top-3 predictions list, "
  "ResultInsight panel, and image quality warnings. Unknown species get amber-themed special styling.")
h2("28.6 Heatmap Toggle")
p("Toggles between original image preview and base64-decoded Grad-CAM heatmap overlay.")

h1("Chapter 29: Page — Dashboard (Analytics)")
p("File: frontend/src/pages/Dashboard.jsx (~200 lines)")
p("Fetches analytics + model metrics on mount. Renders 6 stat cards with AnimatedCounter (using requestAnimationFrame), "
  "a PieChart for species distribution, a BarChart for confidence distribution, "
  "a LineChart for 30-day prediction trends, per-class F1 score bars, and a system status panel "
  "with color-coded health indicators (healthy/warning/critical).")

h1("Chapter 30: Page — Chat (AI Assistant)")
p("File: frontend/src/pages/Chat.jsx (~1200 lines) — the largest file in the project")
h2("30.1 Session Management")
p("Supports multiple chat sessions with create, switch, delete, and clear-all operations. "
  "Sessions are stored in both localStorage (immediate) and backend database (deferred via saveStreamedChat). "
  "On mount, backend sessions are loaded and merged with any localStorage data.")
h2("30.2 NDJSON Streaming")
p("Uses fetch() (not Axios) for streaming. Reads response.body with TextDecoder line by line. "
  "Each JSON object is parsed and token content is accumulated in a ref. "
  "requestAnimationFrame batching prevents excessive re-renders during fast token streaming.")
h2("30.3 Rich Content Rendering")
p("Inline sub-components: WaveformThinking (loading), CodeBlock (syntax highlighting with copy), "
  "RichText (full markdown parser: headers, bold, italic, code blocks, tables, lists, blockquotes, links), "
  "TypewriterText (character-by-character reveal for newest message only).")
h2("30.4 Image Prediction in Chat")
p("Users can attach an image, which triggers api.predict() before the chat request. "
  "The prediction result is included as context for the Gemini response and displayed inline as a ConfidenceBar.")
h2("30.5 Research Mode")
p("Toggles extended output formatting with EntropyGauge (visual entropy/uncertainty with bars for entropy ratio, "
  "temperature, and max entropy values).")
h2("30.6 Export")
p("Export all sessions as JSON or Markdown file download.")

h1("Chapter 31: Page — History (Prediction Browser)")
p("File: frontend/src/pages/History.jsx (~140 lines)")
p("Paginated prediction history with species filter buttons (All + 5 species). "
  "Fetches api.getHistory(pageSize, offset, filter). Renders cards with image thumbnail, species, "
  "color-coded confidence badge (green/blue/orange/red), and timestamp. "
  "Keyboard navigation: ArrowLeft/ArrowRight for pagination.")

h1("Chapter 32: Page — Species Explorer")
p("File: frontend/src/pages/SpeciesExplorer.jsx (~650 lines)")
p("Two modes: species grid (fetches species details) and AI search (api.getAnimalInfo). "
  "Renders KnowledgePanel (Google-style: taxonomy sidebar + main content) for AI search results. "
  "Compare mode: multi-select species using a Set, renders side-by-side comparison table.")

h1("Chapter 33: Page — Batch Process")
p("File: frontend/src/pages/BatchProcess.jsx (~120 lines)")
p("Multi-file upload with sequential api.predict() calls per file and progress tracking. "
  "Renders results table and CSV export function with columns: filename, species, confidence, top2, top3.")

h1("Chapter 34: Page — Compare (Side-by-Side Analysis)")
p("File: frontend/src/pages/Compare.jsx (~280 lines)")
p("Two image upload slots. Parallel api.predict() via Promise.all. "
  "Computes cosine similarity from embeddings (fallback: 100% same species, 30% different). "
  "MorphologicalContrast sub-component shows per-trait comparison with match indicators and alignment percentage.")

h1("Chapter 35: Page — Map Viewer (Leaflet + GBIF)")
p("File: frontend/src/pages/MapViewer.jsx (~300 lines)")
p("Leaflet map with 3 switchable tile layers (CARTO dark, ESRI satellite, OpenTopoMap). "
  "Fetches GBIF occurrence data for 5 species using taxon keys. Fetches local prediction history. "
  "Color-coded custom markers with MarkerClusterGroup for performance. "
  "Popup actions: Open-Meteo weather fetch and Wikipedia article fetch.")

h1("Chapter 36: Page — MLOps Dashboard")
p("File: frontend/src/pages/MLOps.jsx (~580 lines)")
p("Three-tab interface: Overview (stats, BarChart, RadarChart), Review (human-in-the-loop cards with approve/reject/correct), "
  "Pipeline (5-stage inference visualization and active learning loop diagram).")

h1("Chapter 37: Page — Settings")
p("File: frontend/src/pages/Settings.jsx (~400 lines)")
p("Five-tab interface: Profile (name/email/avatar), Security (password change), "
  "Notifications (toggle switches), Behavior (confidence threshold slider, prediction mode, animation toggle), "
  "Privacy (data export as JSON, account deletion with confirmation).")

h1("Chapter 38: Page — Login/Register")
p("File: frontend/src/pages/LoginPage.jsx (~250 lines)")
p("Animated login/register form with Cloudinary-hosted background video (elephants), "
  "glassmorphism card, layoutId animation for mode switching, show/hide password toggle, "
  "auto-redirect when already authenticated.")

h1("Chapter 39: Page — About")
p("File: frontend/src/pages/About.jsx (~100 lines)")
p("Static page: mission statement, 6-item tech stack grid, 5-species grid, 5-step workflow, "
  "and hardcoded model specs card. No state, no API calls, no side effects.")
page_break()

# ─── Chapters 40-45: Components ───────────────────────────────────
h1("Chapter 40: UI Components — Layout and Sidebar")
h2("40.1 Layout.jsx")
p("Root wrapper: shows PageLoader during auth loading. For authenticated users, renders Sidebar + AnimatedBackground + "
  "page content with AnimatePresence page transitions keyed by pathname.")
h2("40.2 Sidebar.jsx (~160 lines)")
p("Fixed 256px sidebar with: GiPawPrint brand logo with breathing animation, 10 primary nav items and 2 secondary, "
  "layoutId sliding active indicator, ThemeSelector component, logout button. "
  "Mobile: hamburger toggle with backdrop overlay and slide-in animation.")

h1("Chapter 41: UI Components — ProtectedRoute and ErrorBoundary")
h2("41.1 ProtectedRoute.jsx")
p("Simple auth guard: loading -> PageLoader, unauthenticated -> Navigate to /login with state.from, authenticated -> Outlet.")
h2("41.2 ErrorBoundary.jsx")
p("React class component: getDerivedStateFromError + componentDidCatch for error logging. "
  "Fallback UI: warning icon with pulse animation, error message, Try Again (reload) and Go Home buttons.")

h1("Chapter 42: UI Components — Visual Primitives")
h2("42.1 GlassCard.jsx")
p("Reusable glass-morphism container with optional glow (gradient border) and hover animation (y:-2, scale:1.01).")
h2("42.2 ConfidenceRing.jsx (~130 lines)")
p("SVG circular gauge: background circle, animated progress arc (stroke-dasharray), glow filter, "
  "tip dot at arc endpoint, center percentage text. 4 color tiers: green (>=80%), blue (>=60%), orange (>=50%), red (<50%). "
  "Unknown mode: amber color. Spring animation with 1.5s duration.")
h2("42.3 CameraCapture.jsx")
p("react-webcam with front/rear camera toggle. Capture function: getScreenshot -> fetch(base64).blob() -> File object -> onCapture callback. "
  "Viewfinder overlay with 4 corner bracket lines.")
h2("42.4 AnimatedBackground.jsx")
p("Fixed full-screen ambient layer: subtle grid pattern, two floating gradient blobs with animate-blob keyframes "
  "(20s and 25s durations), radial vignette overlay. Respects prefers-reduced-motion.")
h2("42.5 BrandLoader.jsx")
p("Full-screen branded splash: gradient backdrop, rotating ring, pulsing circle, bouncing GiPawPrint logo, "
  "WildTrack AI text, and 3 staggered loading dots.")

h1("Chapter 43: UI Components — Loading, Skeleton, EmptyState")
h2("43.1 Loading.jsx")
p("Three components: Loading (spinner + text), SkeletonLoader (pulsing placeholder lines), PageLoader (full-page branded).")
h2("43.2 Skeleton.jsx")
p("Shimmer skeleton with 4 variants: line (randomized width), circle (40px), card (128px), bar (randomized width). "
  "Uses animate-pulse with bg-white/5.")
h2("43.3 EmptyState.jsx")
p("Configurable empty state with preset support (inbox, search, history, chat). "
  "Each preset provides default icon, title, and description. Optional action button with callback.")

h1("Chapter 44: UI Components — Toast and Notifications")
h2("44.1 Toast.jsx")
p("Toast component: success (green), error (red), info (blue). Auto-dismiss via setTimeout. "
  "ToastContainer: fixed bottom-right stacking. useToast hook: manages array state with addToast and removeToast.")
h2("44.2 Notifications.jsx")
p("useNotifications hook: manages notification array, auto-dismiss after 5s. "
  "NotificationContainer: fixed top-right, slide-in from right. "
  "Types: success, error, warning, info with color coding and close button.")

h1("Chapter 45: UI Components — ThemeSelector and ValidatedInput")
h2("45.1 ThemeSelector.jsx")
p("Expandable theme picker: dark/light toggle (sun/moon icon), current theme color swatch, "
  "expandable grid of 6+ themed circular gradient preview swatches.")
h2("45.2 ValidatedInput.jsx")
p("ValidatedInput: input field with error/success border color, icon support, validation message display. "
  "ValidatedForm: form wrapper with spinner-enabled submit button and general error message area.")
page_break()

# ─── Chapter 46-47: Design System and Build ──────────────────────
h1("Chapter 46: Design System — global.css (~680 lines)")
p("The CSS design system uses token-based theming with CSS custom properties:")
bullets([
    "100+ CSS custom properties for colors, backgrounds, borders, shadows, and text colors",
    "Token utility classes: surface-card, surface-card-lg, surface-inset, surface-hover, t-primary, t-secondary, etc.",
    "Custom thin scrollbar with themed track and thumb",
    "15+ keyframe animations: blob, text-shimmer, logo-breathe, glow-pulse, gradient-shift, shimmer, typewriter-cursor, pulse-ring, float-particle, message-entrance, slide-up-fade, page-enter, progress-indeterminate, glow-breathe, orb-float",
    "Leaflet z-index fixes for proper map layer ordering",
    "Neon heading: gradient text with primary-to-accent using background-clip: text",
    "Glass and card effects: glass-card (backdrop-filter blur), glass-blur, glass-glow (mask-composite gradient border)",
    "5 confidence-coded glow classes (green/blue/orange/amber/red) with animated gradient border pseudo-elements",
    "Accessibility: @media (prefers-reduced-motion: reduce) kills all animations and transitions",
    "44px minimum touch targets for mobile accessibility",
])

h1("Chapter 47: Build Configuration")
h2("47.1 Vite Config (vite.config.js)")
p("Plugins: @vitejs/plugin-react, vite-plugin-pwa (autoUpdate, manifest with WildTrackAI Field Assistant name, #FF6B35 theme). "
  "Dev server: port 3000, proxy /api to http://localhost:8000. Build target: es2015, chunk size warning limit: 2000 KB.")
h2("47.2 Tailwind Config (tailwind.config.cjs)")
p("darkMode: 'class'. Custom colors: primary (#FF6B35), secondary (#F7B32B). Custom animations: pulse-slow (3s), bounce-slow (2s).")
h2("47.3 PostCSS Config (postcss.config.cjs)")
p("Standard setup: tailwindcss + autoprefixer plugins.")
h2("47.4 package.json")
p("13 runtime dependencies (React, Axios, Framer Motion, Leaflet, Recharts, react-webcam, react-syntax-highlighter, zustand). "
  "7 dev dependencies (Vite, Tailwind, ESLint, PostCSS). Scripts: dev, build, preview, lint.")
page_break()

# ─── Chapter 48 ───────────────────────────────────────────────────
h1("Chapter 48: Technology Stack — Complete Reference")
h2("48.1 Backend Technologies")
table(["Technology", "Purpose", "Version"],
      [["Python", "Runtime", "3.12.2"],
       ["FastAPI", "Web framework", "0.134.0"],
       ["Uvicorn", "ASGI server", "0.41.0"],
       ["TensorFlow", "Deep learning", "2.20.0"],
       ["Keras", "High-level DL API", "3.13.2"],
       ["OpenCV", "Image processing", "4.13.0"],
       ["Pillow", "Image I/O", "12.1.1"],
       ["NumPy", "Numerical computing", "2.4.2"],
       ["Scikit-learn", "ML metrics", "1.8.0"],
       ["SQLAlchemy", "ORM/database", "2.0.47"],
       ["SQLite", "Database engine", "Built-in"],
       ["bcrypt", "Password hashing", "4.3.0"],
       ["python-jose", "JWT tokens", "3.5.0"],
       ["google-generativeai", "Gemini AI", "0.8.6"],
       ["Cloudinary", "Image storage", "1.44.1"],
       ["ImageHash", "Perceptual hashing", "4.3.2"],
       ["Matplotlib", "Plotting", "3.10.8"],
       ["Seaborn", "Statistical plots", "0.13.2"],
       ["ReportLab", "PDF generation", "4.4.10"]],
      col_widths=[140, 200, 170])
h2("48.2 Frontend Technologies")
table(["Technology", "Purpose", "Version"],
      [["React", "UI framework", "18.2"],
       ["Vite", "Build tool", "5.0"],
       ["Tailwind CSS", "Utility-first CSS", "3.3"],
       ["Framer Motion", "Animations", "10.16"],
       ["Recharts", "Charts", "2.10"],
       ["React Router", "Client routing", "6.18"],
       ["Axios", "HTTP client", "1.6"],
       ["Leaflet", "Maps", "1.9"],
       ["react-leaflet", "React map bindings", "4.2"],
       ["react-webcam", "Camera capture", "7.2"],
       ["react-syntax-highlighter", "Code blocks", "15.5"],
       ["React Icons", "Icon library", "4.12"],
       ["zustand", "State (available)", "4.x"],
       ["vite-plugin-pwa", "PWA support", "0.17"]],
      col_widths=[160, 180, 170])
page_break()

# ─── Chapter 49 ───────────────────────────────────────────────────
h1("Chapter 49: Deployment Architecture")
h2("49.1 Backend Deployment (Render)")
p("render.yaml in the project root defines the backend service. "
  "The start command is: uvicorn main:app --host 0.0.0.0 --port $PORT. "
  "Environment variables: GEMINI_API_KEY, NINJA_API_KEY, CLOUDINARY_URL, JWT_SECRET. "
  "Models are auto-downloaded from GitHub Releases on first startup with retry logic and exponential backoff.")
h2("49.2 Frontend Deployment (Vercel/Netlify)")
p("Vite builds to static files (npm run build). Can be deployed to any static hosting service. "
  "VITE_API_URL environment variable points to the backend URL.")
h2("49.3 Model Distribution")
p("Model files (wildtrack_v4_cpu.keras at ~45 MB) are stored as GitHub Release assets. "
  "The download_models_if_missing function checks for local files, downloads missing ones, "
  "and reports status through the /health endpoint.")
h2("49.4 Health and Readiness Probes")
p("GET /health returns comprehensive status: model loaded, GradCAM available, database exists, "
  "Gemini initialized, API Ninjas available, model download status, and diagnostics. "
  "GET /ready returns 200 only when the model is loaded — Render uses this to know when to route traffic.")
page_break()

# ─── Chapter 50 ───────────────────────────────────────────────────
h1("Chapter 50: Challenges, Solutions, and Innovation")
h2("50.1 Challenges and Solutions")
table(["Challenge", "Solution"],
      [["Small dataset (2,528 images)", "Transfer learning, MixUp, CutMix, TTA, progressive resizing"],
       ["Class imbalance (Wolf=350 vs Tiger=702)", "Focal loss with class-frequency alpha weights"],
       ["Overconfident wrong predictions", "Label smoothing (0.1) + temperature scaling (T=1.2)"],
       ["Noisy web-scraped images", "Multi-stage cleaning: auto, strict filter, quarantine, review"],
       ["AI trust / black-box problem", "Grad-CAM heatmaps showing what the model 'sees'"],
       ["Single model unreliability", "Dual-path consensus validation (TTA vs single-pass)"],
       ["Snow tracks losing claw detail", "Snow brightness heuristic with wolf correction"],
       ["Deployment without GPU", "CPU-optimized .keras format with quantized operations"],
       ["Model too large for Git", "GitHub Releases hosting with auto-download on startup"],
       ["Frontend-backend data sync", "Dual persistence (localStorage + SQLite) for chat"]],
      col_widths=[200, 310])
h2("50.2 Key Innovation Points")
numbered([
    "Footprint classification (not generic animal photo classification) — a niche conservation application.",
    "Multi-stage inference pipeline with quality gates, detection, classification, and calibration.",
    "Dual-path consensus validation without requiring a second trained model.",
    "MixUp + CutMix augmentation on footprint images — state-of-the-art for small datasets.",
    "Domain-specific heuristic corrections (snow track detection).",
    "Full-stack production system with explainability, analytics, authentication, and chat.",
    "Human-in-the-loop active learning with hard negative mining for model improvement.",
    "NDJSON streaming chat with requestAnimationFrame batching for smooth UX.",
    "6-theme dark-mode design system with CSS custom property tokens.",
    "PWA support with offline installation capability.",
])
page_break()

# ─── Chapter 51 ───────────────────────────────────────────────────
h1("Chapter 51: Limitations and Future Scope")
h2("51.1 Current Limitations")
bullets([
    "Only 5 species are currently supported (closed-set classification).",
    "Prediction accuracy varies with image quality, lighting, and substrate type.",
    "Similar species (leopard vs tiger, wolf vs dog) remain challenging.",
    "Dataset diversity could be improved with more geographic and seasonal variety.",
    "Real-world field validation with conservation biologists has not been conducted.",
    "YOLO footprint detector is not yet trained on custom footprint data.",
    "Mobile experience is responsive but not a native app.",
])
h2("51.2 Future Scope")
numbered([
    "Expand to 15+ species including lion, bear, fox, hyena, rhino, and more.",
    "Train a dedicated YOLO model on footprint bounding boxes for better cropping.",
    "Build a mobile app (React Native) for offline field use by forest rangers.",
    "Add GPS-tagged predictions for real-time poaching hotspot mapping.",
    "Implement federated learning across ranger stations for privacy-preserving model updates.",
    "Integrate with government wildlife databases (Project Tiger, CITES).",
    "Fine-tune Gemini on wildlife-specific conservation domain knowledge.",
    "Add individual animal identification from unique pad patterns.",
    "Implement open-set recognition (detect unseen species rather than misclassifying).",
    "Add drone image support for aerial track surveys.",
])
page_break()

# ─── Chapter 52 ───────────────────────────────────────────────────
h1("Chapter 52: Conclusion and Viva Summary")
h2("52.1 Conclusion")
p("WildTrack AI is a comprehensive full-stack AI project that integrates deep learning, computer vision, "
  "explainable AI, backend engineering, frontend design, authentication, analytics, deployment infrastructure, "
  "and AI-assisted interaction into a single wildlife conservation platform. "
  "It demonstrates end-to-end engineering from data collection and cleaning through model training, "
  "multi-stage inference, database persistence, REST API design, modern UI development, "
  "and production deployment readiness.")
p("The project is not a model training exercise alone — it is a practical AI product prototype "
  "designed for real-world conservation support, with professional features like Grad-CAM explainability, "
  "consensus validation, active learning, human-in-the-loop review, and multi-theme responsive design.")
h2("52.2 Short Viva Summary")
p("<b>If you need to explain the project in a few lines during review:</b>")
p("WildTrack AI is a deep learning-based web application that identifies animal species from footprint images. "
  "It uses an EfficientNetB3 transfer learning model trained on 2,528 footprint images across 5 species. "
  "The system provides Grad-CAM heatmap explainability, dual-path consensus validation, "
  "a multi-stage inference pipeline with quality checks and confidence calibration, "
  "a FastAPI backend with SQLite database, JWT authentication, and a React frontend "
  "with real-time analytics dashboards and an AI chatbot powered by Google Gemini. "
  "The goal is to support wildlife monitoring with a faster, more explainable, and more scalable digital solution.")

# ─── End ──────────────────────────────────────────────────────────
sp(40)
story.append(Paragraph("— End of Document —", styles["CoverSub"]))

# ═══════════════════════════════════════════════════════════════════
#  BUILD PDF
# ═══════════════════════════════════════════════════════════════════

def add_page(canvas, doc):
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(colors.HexColor("#d1d5db"))
    canvas.line(42, PAGE_H - 28, PAGE_W - 42, PAGE_H - 28)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(42, PAGE_H - 24, "WildTrack AI — Exhaustive Project Review")
    # Page number
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#4b5563"))
    canvas.drawRightString(PAGE_W - 42, 18, f"Page {doc.page}")
    # Footer line
    canvas.line(42, 32, PAGE_W - 42, 32)
    canvas.restoreState()

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    rightMargin=42, leftMargin=42,
    topMargin=38, bottomMargin=36,
    title="WildTrack AI — Exhaustive Project Review",
    author="WildTrack AI Team",
)
doc.build(story, onFirstPage=add_page, onLaterPages=add_page)

size_mb = OUT.stat().st_size / (1024 * 1024)
print(f"\n{'='*60}")
print(f"PDF generated: {OUT}")
print(f"Size: {size_mb:.2f} MB")
print(f"{'='*60}")
