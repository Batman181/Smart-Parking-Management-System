#!/bin/bash
echo "=== Setting up Smart Parking System ==="

echo "[1/4] Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

echo "[2/4] Setting up detection service..."
cd detection-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

echo "[3/4] Setting up Express notification service..."
cd express-notification
npm install
cd ..

echo "[4/4] Setting up React frontend..."
cd frontend
npm install
cd ..

echo "=== Setup Complete! ==="
