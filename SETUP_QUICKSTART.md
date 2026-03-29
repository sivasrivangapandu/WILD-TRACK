# WildTrack AI - Quick Setup Guide

## Prerequisites
- Python 3.8+
- Node.js 14+
- Git

## Installation

### 1. Clone and Setup
```bash
git clone https://github.com/sivasrivangapandu/WILD-TRACK.git
cd WILD-TRACK
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate
```

### 2. Install Python Dependencies
```bash
pip install -r backend/requirements.txt
```

If you get OpenCV or python-jose errors, install individually:
```bash
pip install opencv-python python-jose
```

### 3. Environment Configuration
```bash
# Copy example to actual config
cp .env.example .env

# Edit .env with your settings (at minimum, change JWT_SECRET)
```

### 4. Download Models
- Download model files from: https://github.com/sivasrivangapandu/WILD-TRACK/releases
- Extract to backend/models/
- Required: wildtrack_v4_cpu.keras or similar

### 5. Frontend Setup
```bash
cd frontend
npm install
```

## Running the Application

### Start Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend
```bash
cd frontend
npm run dev
```

### Access Application
- Frontend: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs
- Backend Redoc: http://localhost:8000/redoc

## Troubleshooting

### UnicodeEncodeError on Windows
This has been fixed in the latest version. If you encounter Unicode errors:
1. Ensure you're using the latest code with git pull
2. Set environment variable: set PYTHONIOENCODING=utf-8

### Missing OpenCV or python-jose
```bash
pip install opencv-python python-jose
```

### Model not loading
1. Verify model file exists in backend/models/
2. Check available disk space
3. Try regenerating: python backend/train_model.py

### Database errors
```bash
cd backend
python -c "from database import init_db; init_db()"
```

### Port already in use
- Backend (8000): netstat -ano | find ":8000" (Windows)
- Frontend (3000): netstat -ano | find ":3000" (Windows)

Change ports in config or kill existing process.

## Project Structure

```
WildTrack AI/
|--- backend/          (FastAPI server, models, ML pipeline)
|--- frontend/         (React UI with Vite)
|--- .env              (Configuration - git-ignored)
|--- requirements.txt  (Python dependencies)
|--- README.md         (Full documentation)
```

## Next Steps
1. Read Multi_Theme_Auth_Guide.md for authentication
2. Review Pro_Features_Guide.md for advanced features
3. Check DEPLOYMENT.md for production setup

## Support
- Documentation: See *.md files in project root
- Issues: GitHub Issues tracker
- Questions: Check existing issues first
