# detector.py
# Uses YOLOv8 (a real AI model) to detect vehicles in parking lot images
# Ray is used to process multiple parking zones in PARALLEL

import ray
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image
import io
import base64

# Initialize Ray for distributed/parallel computing
# This is Lecture 11 - Ray Distributed Computing
ray.init(ignore_reinit_error=True)

# Load YOLOv8 model once (it stays in memory)
# This is a pre-trained deep learning model - Lecture 13-14 (AI model for images)
model = YOLO("yolov8n.pt")  # 'n' = nano, smallest and fastest version

# Vehicle classes in YOLO's COCO dataset
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@ray.remote
def detect_vehicles_in_zone(zone_id: int, image_bytes: bytes, slot_coords: list):
    """
    This function runs as a RAY REMOTE TASK.
    Each parking zone is processed in PARALLEL using Ray.
    
    zone_id: which parking zone (e.g., Zone A, Zone B)
    image_bytes: raw image bytes
    slot_coords: list of [x1,y1,x2,y2] for each slot in this zone
    """
    # Load the image
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    # Run YOLO detection
    results = model(img, verbose=False)
    
    # Get all detected vehicle bounding boxes
    detected_vehicles = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            if class_id in VEHICLE_CLASSES:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                detected_vehicles.append({
                    "bbox": [x1, y1, x2, y2],
                    "class": VEHICLE_CLASSES[class_id],
                    "confidence": confidence
                })

    # Check each parking slot — is a vehicle inside it?
    slot_results = []
    for i, slot in enumerate(slot_coords):
        sx1, sy1, sx2, sy2 = slot
        slot_center_x = (sx1 + sx2) // 2
        slot_center_y = (sy1 + sy2) // 2
        
        occupied = False
        for vehicle in detected_vehicles:
            vx1, vy1, vx2, vy2 = vehicle["bbox"]
            # Check if slot center is inside any detected vehicle box
            if vx1 <= slot_center_x <= vx2 and vy1 <= slot_center_y <= vy2:
                occupied = True
                break
        
        slot_results.append({
            "slot_id": f"Z{zone_id}-S{i+1}",
            "zone": f"Zone-{chr(64 + zone_id)}",  # Zone-A, Zone-B, etc.
            "occupied": occupied,
            "coordinates": slot
        })
    
    return {
        "zone_id": zone_id,
        "slots": slot_results,
        "vehicles_detected": len(detected_vehicles)
    }


def analyze_parking_lot(image_bytes: bytes, zones_config: list):
    """
    Main function: splits the parking lot into zones
    and processes ALL zones in PARALLEL using Ray.
    
    This is the KEY Ray concept - parallel distributed computing.
    Instead of processing zone 1, then zone 2, then zone 3 (slow),
    we process ALL zones at the same time (fast).
    """
    # Launch all zone detections IN PARALLEL (non-blocking)
    futures = []
    for zone in zones_config:
        future = detect_vehicles_in_zone.remote(
            zone["zone_id"],
            image_bytes,
            zone["slot_coords"]
        )
        futures.append(future)
    
    # Wait for ALL parallel tasks to complete and collect results
    results = ray.get(futures)
    
    # Flatten all slot results
    all_slots = []
    for zone_result in results:
        all_slots.extend(zone_result["slots"])
    
    return all_slots
