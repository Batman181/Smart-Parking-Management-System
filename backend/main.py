# backend/main.py
# Main FastAPI backend — the central API of the system
# Connects detection service, optimizer, and notification service

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import json
from optimizer import find_optimal_slot

app = FastAPI(
    title="Smart Parking Backend API",
    description="""
    Central REST API for Smart Parking Management System.
    
    Features:
    - Get real-time parking slot status
    - Assign optimal slot to incoming vehicle
    - Integration with AI detection service
    - OR-Tools based optimization
    """,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DETECTION_SERVICE_URL = "http://detection-service:8001"
NOTIFICATION_SERVICE_URL = "http://express-notification:3001"

# In-memory database (for simplicity)
# In production, this would be a real database like PostgreSQL
parking_slots_db = {}
assignments_db = {}  # vehicle_plate -> slot_id


# ── Pydantic models (request/response schemas) ────────────────────────────
class VehicleEntry(BaseModel):
    vehicle_plate: str
    vehicle_type: str = "car"  # car, motorcycle, bus, truck

class VehicleExit(BaseModel):
    vehicle_plate: str

class SlotUpdateRequest(BaseModel):
    slot_id: str
    occupied: bool


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "Smart Parking Management System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/slots")
def get_all_slots():
    """
    GET /slots
    Returns current status of ALL parking slots.
    This is a standard RESTful GET endpoint — Lecture 4.
    """
    return {
        "slots": list(parking_slots_db.values()),
        "total": len(parking_slots_db),
        "occupied": sum(1 for s in parking_slots_db.values() if s["occupied"]),
        "free": sum(1 for s in parking_slots_db.values() if not s["occupied"])
    }


@app.get("/slots/{slot_id}")
def get_slot(slot_id: str):
    """
    GET /slots/{slot_id}
    Get details of a specific slot. RESTful resource endpoint — Lecture 4.
    """
    if slot_id not in parking_slots_db:
        raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
    return parking_slots_db[slot_id]


@app.post("/detect-and-update")
async def detect_and_update(image: UploadFile = File(...)):
    """
    POST /detect-and-update
    Upload a parking lot image → sends to detection service → updates our DB.
    This ties together: Detection Service (Ray+YOLO) + our backend.
    """
    image_bytes = await image.read()
    
    try:
        # Call the Detection Service (another microservice)
        response = requests.post(
            f"{DETECTION_SERVICE_URL}/detect",
            files={"image": (image.filename, image_bytes, image.content_type)},
            timeout=30
        )
        response.raise_for_status()
        detection_result = response.json()
    except requests.exceptions.ConnectionError:
        # If detection service is down, use mock data for demo
        detection_result = _generate_mock_slots()
    
    # Update our in-memory DB with detection results
    for slot in detection_result["slots"]:
        slot_id = slot["slot_id"]
        # Don't change status if slot is assigned to a vehicle
        if slot_id not in assignments_db.values():
            parking_slots_db[slot_id] = slot
    
    return {
        "message": "Parking lot updated",
        "detection_result": detection_result
    }


@app.post("/vehicle/enter")
def vehicle_enter(vehicle: VehicleEntry):
    """
    POST /vehicle/enter
    When a vehicle arrives, assign the OPTIMAL free slot using OR-Tools.
    Sends notification to Express service after assignment.
    """
    # Check if vehicle already has a slot
    if vehicle.vehicle_plate in assignments_db:
        slot_id = assignments_db[vehicle.vehicle_plate]
        return {
            "message": "Vehicle already has an assigned slot",
            "slot_id": slot_id
        }
    
    # Find all free slots
    free_slots = [s for s in parking_slots_db.values() if not s["occupied"]]
    
    if not free_slots:
        raise HTTPException(status_code=409, detail="No parking slots available")
    
    # Use OR-Tools to find the BEST slot (Lecture 12)
    optimal_slot = find_optimal_slot(free_slots, vehicle.vehicle_type)
    
    if not optimal_slot:
        raise HTTPException(status_code=409, detail="Could not find suitable slot")
    
    # Mark slot as occupied
    slot_id = optimal_slot["slot_id"]
    parking_slots_db[slot_id]["occupied"] = True
    assignments_db[vehicle.vehicle_plate] = slot_id
    
    # Send notification to Express service (Lecture 5)
    try:
        requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notify",
            json={
                "type": "VEHICLE_ENTERED",
                "vehicle_plate": vehicle.vehicle_plate,
                "slot_id": slot_id,
                "zone": optimal_slot["zone"]
            },
            timeout=5
        )
    except Exception:
        pass  # Don't fail if notification service is down
    
    return {
        "message": "Slot assigned successfully",
        "vehicle_plate": vehicle.vehicle_plate,
        "assigned_slot": slot_id,
        "zone": optimal_slot["zone"],
        "instructions": f"Please go to {optimal_slot['zone']}, Slot {slot_id}"
    }


@app.post("/vehicle/exit")
def vehicle_exit(vehicle: VehicleExit):
    """
    POST /vehicle/exit
    When vehicle leaves, free up the slot.
    """
    if vehicle.vehicle_plate not in assignments_db:
        raise HTTPException(
            status_code=404,
            detail=f"No slot assigned to vehicle {vehicle.vehicle_plate}"
        )
    
    slot_id = assignments_db.pop(vehicle.vehicle_plate)
    if slot_id in parking_slots_db:
        parking_slots_db[slot_id]["occupied"] = False
    
    # Notify Express service
    try:
        requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notify",
            json={
                "type": "VEHICLE_EXITED",
                "vehicle_plate": vehicle.vehicle_plate,
                "slot_id": slot_id
            },
            timeout=5
        )
    except Exception:
        pass
    
    return {
        "message": "Vehicle exited, slot freed",
        "vehicle_plate": vehicle.vehicle_plate,
        "freed_slot": slot_id
    }


@app.get("/assignments")
def get_assignments():
    """GET /assignments — see all current vehicle-to-slot assignments."""
    return {"assignments": assignments_db}


@app.post("/slots/initialize")
def initialize_slots():
    """
    POST /slots/initialize
    Initialize the parking lot with default empty slots.
    Useful for demo/testing without a camera image.
    """
    global parking_slots_db
    parking_slots_db = {}
    
    for zone_num in range(1, 3):
        zone_letter = chr(64 + zone_num)  # A, B
        for slot_num in range(1, 5):
            slot_id = f"Z{zone_num}-S{slot_num}"
            parking_slots_db[slot_id] = {
                "slot_id": slot_id,
                "zone": f"Zone-{zone_letter}",
                "occupied": False,
                "coordinates": [0, 0, 100, 100]
            }
    
    return {"message": "Slots initialized", "total": len(parking_slots_db)}


def _generate_mock_slots():
    """Generate mock detection data when detection service is unavailable."""
    import random
    slots = []
    for z in range(1, 3):
        for s in range(1, 5):
            slots.append({
                "slot_id": f"Z{z}-S{s}",
                "zone": f"Zone-{chr(64+z)}",
                "occupied": random.choice([True, False]),
                "coordinates": [0, 0, 100, 100]
            })
    return {
        "total_slots": len(slots),
        "occupied": sum(1 for s in slots if s["occupied"]),
        "free": sum(1 for s in slots if not s["occupied"]),
        "slots": slots
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "backend"}
