# Smart Parking Management System

A college project that uses AI to detect free and occupied parking slots from a camera image, automatically assigns the best slot to a vehicle when it enters, and shows everything live on a web dashboard. The whole system is split into 4 services and runs together using Docker.

---

## What This Project Does

The problem this project solves is simple. When someone drives into a parking lot, they usually have to drive around looking for a free spot. This system removes that problem completely.

Here is the step by step flow of how it works:

- A camera image of the parking lot is uploaded to the system
- A YOLOv8 AI model looks at the image and figures out which slots have cars parked in them and which ones are empty
- When a vehicle arrives, the driver enters their vehicle plate number on the dashboard
- The backend uses Google OR-Tools (an optimization library) to calculate which free slot is the most convenient for that vehicle based on distance from the entrance and which zone it is in
- That slot gets assigned to the vehicle and the dashboard updates instantly
- When the vehicle leaves, the slot is freed up and becomes available again
- Every entry and exit is logged and visible in the event history tab

---

## Tech Stack

| Part | Technology |
|---|---|
| Frontend Dashboard | React |
| Backend API | FastAPI (Python) |
| AI Vehicle Detection | YOLOv8, OpenCV |
| Parallel Processing | Ray |
| Slot Optimization | Google OR-Tools |
| Notification Service | Express.js (Node.js) |
| Containerization | Docker, Docker Compose |
| Kubernetes Configs | Minikube |

---

## Project Structure

```
Smart-Parking-Management-System/
│
├── backend/
│   ├── main.py
│   ├── optimizer.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── detection-service/
│   ├── main.py
│   ├── detector.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── express-notification/
│   ├── server.js
│   ├── package.json
│   ├── package-lock.json
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.css
│   ├── public/
│   │   ├── index.html
│   │   ├── favicon.ico
│   │   ├── manifest.json
│   │   └── robots.txt
│   ├── package.json
│   ├── package-lock.json
│   └── Dockerfile
│
├── k8s/
│   ├── backend-deployment.yaml
│   ├── detection-deployment.yaml
│   ├── frontend-deployment.yaml
│   └── notification-deployment.yaml
│
├── scripts/
│   ├── setup.sh
│   ├── start.sh
│   └── stop.sh
│
├── docker-compose.yml
├── LICENSE
└── README.md
```

---

## How Each Part Works

**backend**
This is the main brain of the system. It handles all the API routes, keeps track of which slots are free or occupied, manages vehicle entry and exit, and talks to both the detection service and the notification service. The `optimizer.py` file inside it uses Google OR-Tools to pick the best slot whenever a new vehicle comes in. It prefers Zone A over Zone B since Zone A is closer to the exit, and within a zone it picks the slot with the lowest number since that is closest to the entrance.

**detection-service**
This service takes a parking lot image and tells the backend which slots are occupied. It uses YOLOv8 to detect vehicles in the image. The parking lot is divided into zones and each zone has predefined slot coordinates. For each slot it checks if a detected vehicle's bounding box overlaps with that slot's position. The cool part is that it uses Ray to process all zones at the same time in parallel instead of one by one, which makes it faster. The vehicle types it can detect are car, motorcycle, bus, and truck.

**express-notification**
This is a small Node.js service that acts as an event logger. Every time the backend processes a vehicle entry or exit, it sends a notification to this service. The service stores those events in memory and makes them available for the frontend to display. In a real world version of this project, this service would be the place where you would add SMS or push notification logic.

**frontend**
This is the React dashboard that users interact with. It has three tabs. The dashboard tab shows all parking slots in a grid view grouped by zone with green for free and red for occupied. The vehicle control tab is where you type in a plate number and either enter or exit a vehicle. The event log tab shows the last 20 parking events with timestamps. The frontend refreshes automatically every 5 seconds so the slot status stays up to date without needing to manually refresh the page.

**k8s**
These are the Kubernetes YAML files if you want to deploy the project on a cluster instead of locally with Docker. The backend is set to run 2 replicas so it stays up even if one instance crashes.

**scripts**
Three helper shell scripts. `setup.sh` installs all dependencies for all four services at once. `start.sh` starts all services. `stop.sh` stops everything.

---

## How to Run the Project

### Option 1 — Docker Compose (recommended)

This is the easiest way. You only need Docker installed.

```bash
git clone https://github.com/Batman181/Smart-Parking-Management-System.git
cd Smart-Parking-Management-System
docker compose up --build
```

The first time you run this it might take a few minutes because Docker needs to download the YOLOv8 model. Once everything is up, open these URLs in your browser:

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Detection Service | http://localhost:8001 |
| Notification Service | http://localhost:3001 |

To stop everything:

```bash
docker compose down
```

---

### Option 2 — Running Without Docker

Run the setup script first to install all dependencies:

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Then open 4 separate terminal windows and run each service:

**Terminal 1 — Backend**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Detection Service**
```bash
cd detection-service
source venv/bin/activate
uvicorn main:app --reload --port 8001
```

**Terminal 3 — Notification Service**
```bash
cd express-notification
node server.js
```

**Terminal 4 — Frontend**
```bash
cd frontend
npm start
```

---

## API Endpoints

FastAPI automatically generates interactive documentation for all endpoints. You can test everything visually at `http://localhost:8000/docs` without writing any code.

**Backend — Port 8000**

| Method | Endpoint | Description |
|---|---|---|
| GET | /slots | Get all parking slots and their current status |
| GET | /slots/{slot_id} | Get details of one specific slot |
| POST | /slots/initialize | Set up the parking lot with default slots for testing |
| POST | /vehicle/enter | Enter a vehicle by plate number and get a slot assigned |
| POST | /vehicle/exit | Exit a vehicle by plate number and free up its slot |
| GET | /assignments | See which vehicle is currently assigned to which slot |
| POST | /detect-and-update | Upload an image and run AI detection to update slot status |
| GET | /health | Check if the service is running |

Example of entering a vehicle:

```json
POST /vehicle/enter
{
  "vehicle_plate": "GJ01AB1234",
  "vehicle_type": "car"
}
```

What you get back:

```json
{
  "message": "Slot assigned successfully",
  "vehicle_plate": "GJ01AB1234",
  "assigned_slot": "Z1-S1",
  "zone": "Zone-A",
  "instructions": "Please go to Zone-A, Slot Z1-S1"
}
```

**Detection Service — Port 8001**

| Method | Endpoint | Description |
|---|---|---|
| POST | /detect | Upload a parking lot image and get back which slots are free or occupied |
| GET | /health | Check if the service is running |

**Notification Service — Port 3001**

| Method | Endpoint | Description |
|---|---|---|
| POST | /notify | Receive an event from the backend (used internally, not by users) |
| GET | /events | Get the last 20 parking events with timestamps |
| GET | /health | Check if the service is running |

---

## Kubernetes Deployment

If you want to deploy on Kubernetes using Minikube:

```bash
minikube start
eval $(minikube docker-env)

docker build -t smart-parking-backend:latest ./backend
docker build -t smart-parking-detection:latest ./detection-service
docker build -t smart-parking-notification:latest ./express-notification
docker build -t smart-parking-frontend:latest ./frontend

kubectl apply -f k8s/

minikube service backend-svc
```

---

## Environment Variables

These are already configured inside `docker-compose.yml` so you do not need to change anything for local development. This is just for reference if you ever deploy it somewhere else.

| Variable | Default Value | What it does |
|---|---|---|
| DETECTION_SERVICE_URL | http://detection-service:8001 | Where the backend sends images for detection |
| NOTIFICATION_SERVICE_URL | http://express-notification:3001 | Where the backend sends entry and exit events |
| REACT_APP_API_URL | http://localhost:8000 | Backend URL that the browser uses |
| REACT_APP_NOTIFY_URL | http://localhost:3001 | Notification service URL that the browser uses |

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.

---

## Presentation

The project presentation covering the problem statement, architecture, technology choices, and demo is available in this repository. See [presentation.pptx](presentation.pptx)

---

## Team

This project was made as a group assignment for AI212.

| Name | GitHub |
|---|---|
| Kush Mistry | [@Batman181](https://github.com/Batman181) |
| Rishi Datt Gupta | [@rishidatt2006-gif](https://github.com/rishidatt2006-gif) |

---

Built for AI212 using FastAPI, React, YOLOv8, Ray, OR-Tools, Docker and Kubernetes.
