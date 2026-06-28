// express-notification/server.js
// Lecture 5: Express API (Node.js backend microservice)
// This service receives notification events and logs/forwards them

const express = require("express");
const cors = require("cors");
const bodyParser = require("body-parser");

const app = express();
const PORT = 3001;

app.use(cors());
app.use(bodyParser.json());

// In-memory log of all events
const eventLog = [];

app.get("/", (req, res) => {
  res.json({ message: "Notification Service is running", status: "ok" });
});

// POST /notify — receive a parking event notification
app.post("/notify", (req, res) => {
  const { type, vehicle_plate, slot_id, zone } = req.body;

  const event = {
    id: eventLog.length + 1,
    type,
    vehicle_plate,
    slot_id,
    zone: zone || "N/A",
    timestamp: new Date().toISOString(),
  };

  eventLog.push(event);

  // In a real system, you'd send SMS, email, or push notification here
  console.log(`[NOTIFICATION] ${type}: Vehicle ${vehicle_plate} → Slot ${slot_id}`);

  res.json({ message: "Notification received", event });
});

// GET /events — get all notification history
app.get("/events", (req, res) => {
  res.json({
    total: eventLog.length,
    events: eventLog.slice(-20), // last 20 events
  });
});

// GET /health
app.get("/health", (req, res) => {
  res.json({ status: "ok", service: "express-notification" });
});

app.listen(PORT, () => {
  console.log(`Notification Service running on port ${PORT}`);
});
