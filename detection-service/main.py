# detection-service/main.py
# FastAPI app that wraps our Ray + YOLO detection

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from detector import analyze_parking_lot
import json

app = FastAPI(
    title="Vehicle Detection Service",
    description="Detects vehicles in parking lot images using YOLOv8 + Ray",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default parking lot layout (can be customized)
# This simulates a parking lot with 2 zones, 4 slots each
DEFAULT_ZONES_CONFIG = [
    {
        "zone_id": 1,
        "slot_coords": [
            [10, 10, 150, 100],
            [160, 10, 300, 100],
            [310, 10, 450, 100],
            [460, 10, 600, 100],
        ]
    },
    {
        "zone_id": 2,
        "slot_coords": [
            [10, 110, 150, 200],
            [160, 110, 300, 200],
            [310, 110, 450, 200],
            [460, 110, 600, 200],
        ]
    }
]


@app.get("/")
def root():
    return {"message": "Detection Service is running", "status": "healthy"}


@app.post("/detect")
async def detect_parking(
    image: UploadFile = File(...),
    zones_config: str = None
):
    """
    Upload a parking lot image.
    Returns which slots are occupied and which are free.
    Uses YOLOv8 for AI detection + Ray for parallel processing.
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    image_bytes = await image.read()
    
    # Use custom zones config if provided, else use default
    zones = json.loads(zones_config) if zones_config else DEFAULT_ZONES_CONFIG
    
    # Run detection (Ray processes all zones in parallel)
    slots = analyze_parking_lot(image_bytes, zones)
    
    total = len(slots)
    occupied = sum(1 for s in slots if s["occupied"])
    free = total - occupied
    
    return {
        "total_slots": total,
        "occupied": occupied,
        "free": free,
        "occupancy_percent": round((occupied / total) * 100, 1) if total > 0 else 0,
        "slots": slots
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "detection"}
