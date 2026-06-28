// frontend/src/App.js
// React frontend dashboard — Lecture 3

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./App.css";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";
const NOTIFY_BASE = process.env.REACT_APP_NOTIFY_URL || "http://localhost:3001";

function App() {
  const [slots, setSlots] = useState([]);
  const [summary, setSummary] = useState({ total: 0, occupied: 0, free: 0 });
  const [events, setEvents] = useState([]);
  const [vehiclePlate, setVehiclePlate] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");

  // Fetch current slot status from backend
  const fetchSlots = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/slots`);
      setSlots(res.data.slots);
      setSummary({
        total: res.data.total,
        occupied: res.data.occupied,
        free: res.data.free,
      });
    } catch (err) {
      console.error("Failed to fetch slots:", err);
    }
  }, []);

  // Fetch notification events
  const fetchEvents = useCallback(async () => {
    try {
      const res = await axios.get(`${NOTIFY_BASE}/events`);
      setEvents(res.data.events.reverse());
    } catch (err) {
      console.error("Failed to fetch events:", err);
    }
  }, []);

  // Initialize slots on first load
  const initializeSlots = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/slots/initialize`);
      await fetchSlots();
      setMessage("✅ Parking lot initialized with 8 slots (2 zones × 4 slots)");
    } catch (err) {
      setMessage("❌ Failed to initialize slots");
    }
    setLoading(false);
    setTimeout(() => setMessage(""), 3000);
  };

  // Vehicle enters parking
  const handleVehicleEnter = async () => {
    if (!vehiclePlate.trim()) {
      setMessage("⚠️ Please enter a vehicle plate number");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/vehicle/enter`, {
        vehicle_plate: vehiclePlate.toUpperCase(),
        vehicle_type: "car",
      });
      setMessage(`✅ ${res.data.instructions}`);
      setVehiclePlate("");
      await fetchSlots();
      await fetchEvents();
    } catch (err) {
      const detail = err.response?.data?.detail || "Error assigning slot";
      setMessage(`❌ ${detail}`);
    }
    setLoading(false);
    setTimeout(() => setMessage(""), 4000);
  };

  // Vehicle exits parking
  const handleVehicleExit = async () => {
    if (!vehiclePlate.trim()) {
      setMessage("⚠️ Please enter a vehicle plate number");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/vehicle/exit`, {
        vehicle_plate: vehiclePlate.toUpperCase(),
      });
      setMessage(`✅ ${res.data.message} — Freed slot: ${res.data.freed_slot}`);
      setVehiclePlate("");
      await fetchSlots();
      await fetchEvents();
    } catch (err) {
      const detail = err.response?.data?.detail || "Error processing exit";
      setMessage(`❌ ${detail}`);
    }
    setLoading(false);
    setTimeout(() => setMessage(""), 4000);
  };

  // Auto-refresh every 5 seconds
  useEffect(() => {
    fetchSlots();
    fetchEvents();
    const interval = setInterval(() => {
      fetchSlots();
      fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchSlots, fetchEvents]);

  // Group slots by zone
  const slotsByZone = slots.reduce((acc, slot) => {
    const zone = slot.zone || "Unknown";
    if (!acc[zone]) acc[zone] = [];
    acc[zone].push(slot);
    return acc;
  }, {});

  return (
    <div className="app">
      <header className="header">
        <h1>🅿️ Smart Parking Management System</h1>
        <p>AI-Powered Vehicle Detection & Slot Management</p>
      </header>

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="card card-total">
          <h2>{summary.total}</h2>
          <p>Total Slots</p>
        </div>
        <div className="card card-free">
          <h2>{summary.free}</h2>
          <p>Available</p>
        </div>
        <div className="card card-occupied">
          <h2>{summary.occupied}</h2>
          <p>Occupied</p>
        </div>
        <div className="card card-percent">
          <h2>
            {summary.total > 0
              ? Math.round((summary.free / summary.total) * 100)
              : 0}
            %
          </h2>
          <p>Free</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={activeTab === "dashboard" ? "tab active" : "tab"}
          onClick={() => setActiveTab("dashboard")}
        >
          📊 Dashboard
        </button>
        <button
          className={activeTab === "vehicle" ? "tab active" : "tab"}
          onClick={() => setActiveTab("vehicle")}
        >
          🚗 Vehicle Control
        </button>
        <button
          className={activeTab === "events" ? "tab active" : "tab"}
          onClick={() => setActiveTab("events")}
        >
          📋 Event Log
        </button>
      </div>

      {/* Message Banner */}
      {message && <div className="message-banner">{message}</div>}

      {/* Dashboard Tab */}
      {activeTab === "dashboard" && (
        <div className="tab-content">
          <div className="actions-bar">
            <button className="btn btn-primary" onClick={initializeSlots} disabled={loading}>
              🔄 Initialize Parking Lot
            </button>
            <button className="btn btn-secondary" onClick={() => { fetchSlots(); fetchEvents(); }}>
              ♻️ Refresh
            </button>
          </div>

          {Object.keys(slotsByZone).length === 0 ? (
            <div className="empty-state">
              <p>No slots loaded. Click "Initialize Parking Lot" to start.</p>
            </div>
          ) : (
            Object.entries(slotsByZone).map(([zone, zoneSlots]) => (
              <div key={zone} className="zone">
                <h3 className="zone-title">{zone}</h3>
                <div className="slots-grid">
                  {zoneSlots.map((slot) => (
                    <div
                      key={slot.slot_id}
                      className={`slot ${slot.occupied ? "occupied" : "free"}`}
                    >
                      <div className="slot-icon">{slot.occupied ? "🚗" : "✅"}</div>
                      <div className="slot-id">{slot.slot_id}</div>
                      <div className="slot-status">
                        {slot.occupied ? "Occupied" : "Free"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Vehicle Control Tab */}
      {activeTab === "vehicle" && (
        <div className="tab-content">
          <div className="vehicle-control">
            <h3>Vehicle Plate Number</h3>
            <input
              type="text"
              placeholder="e.g. PB10AB1234"
              value={vehiclePlate}
              onChange={(e) => setVehiclePlate(e.target.value.toUpperCase())}
              className="plate-input"
              onKeyDown={(e) => e.key === "Enter" && handleVehicleEnter()}
            />
            <div className="vehicle-buttons">
              <button
                className="btn btn-enter"
                onClick={handleVehicleEnter}
                disabled={loading}
              >
                🚗 Vehicle Enter — Assign Optimal Slot
              </button>
              <button
                className="btn btn-exit"
                onClick={handleVehicleExit}
                disabled={loading}
              >
                🚪 Vehicle Exit — Free Slot
              </button>
            </div>
            <p className="hint">
              💡 The system uses OR-Tools optimization to assign the best
              available slot automatically.
            </p>
          </div>
        </div>
      )}

      {/* Events Tab */}
      {activeTab === "events" && (
        <div className="tab-content">
          <h3>Notification Event Log (from Express Service)</h3>
          {events.length === 0 ? (
            <p className="empty-state">No events yet. Try entering a vehicle.</p>
          ) : (
            <div className="events-list">
              {events.map((event) => (
                <div
                  key={event.id}
                  className={`event-item ${event.type === "VEHICLE_ENTERED" ? "event-enter" : "event-exit"}`}
                >
                  <span className="event-icon">
                    {event.type === "VEHICLE_ENTERED" ? "🚗" : "🚪"}
                  </span>
                  <div className="event-details">
                    <strong>{event.vehicle_plate}</strong> — {event.type}
                    <br />
                    Slot: {event.slot_id} | {event.zone}
                    <br />
                    <small>{new Date(event.timestamp).toLocaleString()}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <footer className="footer">
        <p>
          Built with React · FastAPI · Ray · OR-Tools · YOLOv8 · Docker ·
          Kubernetes
        </p>
        <p>AI212 Project — Smart Parking Management System</p>
      </footer>
    </div>
  );
}

export default App;
