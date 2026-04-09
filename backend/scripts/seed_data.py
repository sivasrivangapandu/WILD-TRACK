import asyncio
import time
import random
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db, init_db
from models.prediction_model import Prediction
from datetime import datetime, timedelta

async def seed_live_tracking_data():
    init_db()
    db = next(get_db())
    
    # Base coordinates for different species habitats
    habitats = {
        'tiger': [(21.25, 81.62), (26.44, 80.33), (27.17, 78.04), (23.25, 77.41)], # India
        'elephant': [(11.01, 76.95), (10.85, 76.27), (0.02, 37.90), (-2.33, 34.83)], # India/Africa
        'leopard': [(19.07, 72.87), (28.61, 77.20), (13.08, 80.27), (-1.29, 36.82)], # India/Africa
        'wolf': [(44.42, -110.58), (51.04, -114.07), (60.16, 24.93), (55.75, 37.61)], # US/Canada/Europe/Russia
        'deer': [(40.71, -74.00), (34.05, -118.24), (51.50, -0.12), (48.85, 2.35)] # Widespread
    }
    
    print("Planting 50+ live tracking data points...")
    
    now = datetime.utcnow()
    
    count = 0
    for species, locations in habitats.items():
        for base_lat, base_lng in locations:
            # Generate 2-4 footprints per base location to simulate movement/clusters
            for _ in range(random.randint(2, 4)):
                # Randomize slightly around the base location
                lat = base_lat + random.uniform(-2.5, 2.5)
                lng = base_lng + random.uniform(-2.5, 2.5)
                
                # Randomize time within the last 48 hours to look "recent"
                timestamp = now - timedelta(hours=random.uniform(0, 48))
                
                # Randomize confidence
                confidence = random.uniform(0.65, 0.99)
                
                pred = Prediction(
                    filename=f"live_cam_{int(time.time())}_{random.randint(1000,9999)}.jpg",
                    species=species,
                    confidence=confidence,
                    heatmap_generated=True,
                    latitude=lat,
                    longitude=lng,
                    timestamp=timestamp
                )
                db.add(pred)
                count += 1
                
    db.commit()
    print(f"Successfully seeded {count} tracking points across the globe!")

if __name__ == "__main__":
    asyncio.run(seed_live_tracking_data())
