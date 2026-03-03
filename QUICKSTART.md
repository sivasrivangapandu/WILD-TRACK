# 🚀 Quick Start Guide

Get WildTrackAI running in 5 minutes!

## Prerequisites Check

Verify you have installed:
- Python 3.10+
- Node.js 18+ (LTS)

```bash
python --version
node --version
npm --version
```

## Step 1: Terminal 1 - Start Backend

```bash
cd "D:\Wild Track AI\backend"

# Activate virtual environment
venv\Scripts\activate

# Start FastAPI server
python main.py
```

Wait for:
```
Starting server at http://localhost:8000
API docs at http://localhost:8000/docs
```

## Step 2: Terminal 2 - Start Frontend

```bash
cd "D:\Wild Track AI\frontend"

# Start React dev server
npm run dev
```

Wait for:
```
  ➜  Local:   http://localhost:5173/
```

## Step 3: Open Browser

Visit: **`http://localhost:3000`** or **`http://localhost:5173`**

## Step 4: Train Model (Optional - First Time Only)

If model not trained:

```bash
cd "D:\Wild Track AI\backend\training"
python train.py
```

Once training completes:
- Model saved to `backend/models/wildtrack_final.h5`
- Restart backend server

## 📸 Usage

1. **Check Website**
   - Home page with features
   - Beautiful hero section

2. **Upload Footprint**
   - Drag & drop an animal footprint image
   - Or click to browse

3. **View Results**
   - Animal prediction with confidence
   - Top 3 predictions
   - Grad-CAM heatmap
   - Detailed animal info

4. **Check Dashboard**
   - Species distribution
   - Prediction stats
   - Model performance

## 🔗 Important Links

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | Web UI |
| Backend API | http://localhost:8000 | Prediction service |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| Dashboard | http://localhost:3000/dashboard | Statistics |

## 📊 Dataset Info

Images collected automatically during setup:
- Tiger: 702 images
- Leopard: 492 images
- Elephant: 484 images
- Deer: 500 images
- Wolf: 350 images
- Total: 2,528 images

## ⚙️ Troubleshooting

### "Module not found" Error
```bash
cd backend
pip install -r requirements.txt
```

### Port Already in Use
```bash
# Kill process on port 8000 (backend)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or use different port
npm run dev -- --port 3001
```

### No Model Loaded
Train the model:
```bash
cd backend/training
python train.py
```

## 📝 Project Structure

```
D:\Wild Track AI\
├── backend/
│   ├── dataset/         ← Footprint images
│   ├── models/          ← Trained model (.h5)
│   ├── training/
│   │   └── train.py     ← Training script
│   ├── main.py          ← API server
│   └── venv/            ← Python env
│
└── frontend/
    ├── src/             ← React components
    ├── package.json
    └── node_modules/
```

## 🎯 Next Steps

1. **Analyze Images**: Upload footprints for predictions
2. **Check Dashboard**: View statistics
3. **Train Better**: Add more images for improved accuracy
4. **Deploy**: See production deployment guide
5. **Customize**: Modify for your own dataset

## 📚 Documentation

- **README.md**: Full project documentation
- **API Docs**: Visit http://localhost:8000/docs
- **Frontend Code**: Well-commented React components

## 💡 Tips

- For best results, upload clear footprint images
- Image should show the full footprint
- Works best with muddy/dusty footprints
- Check API docs for all available endpoints

## 🆘 Need Help?

1. Check README.md for detailed info
2. Review API documentation at `/docs`
3. Check console for error messages
4. Verify both servers are running

---

**Enjoy using WildTrackAI! 🐾**
