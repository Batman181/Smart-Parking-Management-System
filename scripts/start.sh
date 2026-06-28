#!/bin/bash
echo "Starting Smart Parking System..."
docker compose up --build -d
echo "All services running!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
