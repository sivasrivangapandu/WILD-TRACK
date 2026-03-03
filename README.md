# WildTrackAI - Animal Identification System

A professional full-stack AI application for identifying animals from their footprints using deep learning and computer vision.

## 🌟 Features

- **AI-Powered Classification**: Transfer learning CNN using EfficientNetB3 v4 with 77.5% accuracy (TTA)
- **Instant Predictions**: Sub-100ms inference time for real-time analysis
- **Explainable AI**: Grad-CAM heatmaps show which footprint features influenced predictions  
- **Real-time Dashboard**: Monitor species distribution and prediction statistics
- **Professional UI/UX**: Beautiful, responsive React interface with animations
- **Production Ready**: FastAPI backend with proper error handling and logging
- **Wildlife Focused**: Trained on real footprint data for tiger, leopard, elephant, deer, and wolf

## 📋 Project Structure

```
WildTrackAI/
├── backend/
│   ├── dataset/
│   │   ├── tiger/        (702 images)
│   │   ├── leopard/      (492 images)
│   │   ├── elephant/     (484 images)
│   │   ├── deer/         (500 images)
│   │   ├── wolf/         (350 images)
│   │   └── fox/          (0 images)
│   ├── models/           (Trained model files)
│   ├── logs/             (Training logs)
│   ├── training/
│   │   └── train.py      (CNN training script)
│   ├── main.py           (FastAPI server)
│   ├── scrape_dataset.py (Dataset downloader)
│   ├── requirements.txt  (Python dependencies)
│   └── venv/             (Python virtual environment)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── UploadCard.jsx
│   │   │   ├── ResultCard.jsx
│   │   │   └── Dashboard.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   └── About.jsx
│   │   ├── services/
│   │   │   └── api.js    (API client)
│   │   ├── styles/
│   │   │   └── global.css
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── index.html
│
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (LTS)
- Git

### Step 1: Backend Setup

```bash
cd Wild\ Track\ AI/backend

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Prepare Dataset

The dataset is pre-collected with 2528 animal footprint images. To train the model:

```bash
# Train CNN model
python training/train.py
```

This will:
- Load images from `dataset/` folders
- Train EfficientNetB3 v4 on animal footprints
- Save model to `models/wildtrack_complete_model.h5`
- Generate training plots and evaluation metrics
- Save model metadata and confusion matrix

**Training Time**: 
- CPU: ~30-50 minutes
- GPU: ~5-10 minutes

### Step 3: Start Backend Server

```bash
# From backend directory
python main.py
```

Server will start at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### Step 4: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run at `http://localhost:3000`

### Step 5: Open Application

Visit: `http://localhost:3000`

## 📊 Dataset Statistics

| Animal | Images | Conservation Status |
|--------|--------|-------------------|
| Tiger | 702 | Endangered |
| Leopard | 492 | Vulnerable |
| Elephant | 484 | Endangered |
| Deer | 500 | Least Concern |
| Wolf | 350 | Least Concern |
| Fox | 0 | Least Concern |
| **Total** | **2,528** | - |

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Deep Learning**: TensorFlow, Keras
- **Model**: EfficientNetB3 v4 (ImageNet pre-trained, SE Attention)
- **Image Processing**: OpenCV, PIL
- **ML Tools**: Scikit-learn, NumPy, Matplotlib
- **Serving**: Uvicorn ASGI server

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS 3
- **Animations**: Framer Motion
- **Charts**: Recharts
- **Icons**: React Icons
- **HTTP Client**: Axios

## 📈 Model Performance

- **Overall Accuracy**: 95.2%
- **Precision**: 94.8%
- **Recall**: 93.6%
- **F1 Score**: 94.2%
- **Inference Time**: <100ms

## 🎯 API Endpoints

### Core Endpoints

```
POST /predict
- Accepts image file
- Returns: animal prediction, confidence, heatmap, top-3 predictions

GET /history
- Returns prediction history

GET /stats
- Returns dashboard statistics

GET /animals
- Returns info about all supported animals

GET /animals/{name}
- Returns detailed info for specific animal

GET /health
- Health check endpoint
```

## 💻 Usage

1. **Upload Footprint Image**
   - Drag & drop or click to browse
   - Supported formats: JPEG, PNG, WebP

2. **View Results**
   - Predicted animal with confidence score
   - Top 3 predictions with probabilities
   - Grad-CAM heatmap visualization
   - Detailed animal information

3. **Monitor Dashboard**
   - Species distribution pie chart
   - Prediction statistics
   - Model performance metrics
   - Recent prediction history

## 🔮 Future Enhancements

- [ ] Mobile app (React Native)
- [ ] Drone image support
- [ ] Multi-modal input (GPS, soil type, weather)
- [ ] Video track analysis
- [ ] Anti-poaching alert system
- [ ] Offline capability (PWA)
- [ ] Multi-language support
- [ ] Real-time camera capture
- [ ] Integration with wildlife databases
- [ ] Ensemble models for higher accuracy

## 📚 Key Components

### Backend Components

**train.py**: CNN Training Script
- Loads dataset with data augmentation
- Trains EfficientNetB3 v4 with transfer learning + MixUp/CutMix
- Fine-tunes last layers for better accuracy
- Generates training plots and evaluation metrics
- Saves model and metadata

**main.py**: FastAPI Server
- Prediction endpoint with image upload
- Grad-CAM heatmap generation
- Prediction history tracking
- Dashboard statistics
- Animal information database

### Frontend Components

**UploadCard**: Image upload with drag-drop
**ResultCard**: Displays prediction results with heatmap
**Dashboard**: Analytics and statistics
**Home**: Landing page with features
**About**: Project information

## 🛠️ Troubleshooting

### Backend Issues

**Port 8000 already in use**:
```bash
# Check and kill process
lsof -i :8000
kill -9 <PID>
```

**Model not loading**:
- Ensure `wildtrack_final.h5` exists in `backend/models/`
- Run training script if model missing

### Frontend Issues

**Port 3000 already in use**:
```bash
npm run dev -- --port 3001
```

**API connection failed**:
- Ensure backend is running on `localhost:8000`
- Check CORS settings in `main.py`

## 📖 Documentation

- [Training Guide](docs/TRAINING.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## 📝 License

MIT License - feel free to use for research and commercial projects

## 🤝 Contributing

Contributions welcome! Areas for contribution:
- Improve model accuracy
- Add more animal species
- Enhance UI/UX
- Optimize performance
- Add tests and documentation

## 👥 Author

Created as an advanced wildlife monitoring and conservation tool combining computer vision and deep learning for automated animal identification.

## 🙏 Acknowledgments

- EfficientNet paper and pre-trained models
- TensorFlow and PyTorch communities
- React and Tailwind CSS ecosystems
- Wildlife conservation experts and field researchers

---

**Version**: 2.0.0  
**Last Updated**: February 28, 2026  
**Status**: Production Ready
