/**
 * DBOS API Client Service
 * Encapsulates all REST calls to the backend/server.py Python bridge.
 */

const API_BASE =
  typeof window !== "undefined" && window.location.port !== "8000" && window.location.protocol.startsWith("http")
    ? `http://${window.location.hostname || "localhost"}:8000`
    : "";

async function apiRequest(endpoint, method = "GET", payload = null) {
  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (payload && (method === "POST" || method === "PUT")) {
    options.body = JSON.stringify(payload);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    const data = await response.json();
    return { status: response.status, ok: response.ok, data };
  } catch (error) {
    console.error(`API Error on ${method} ${endpoint}:`, error);
    return {
      status: 500,
      ok: false,
      data: { success: false, error: "Network connection to DBOS server failed." },
    };
  }
}

export const DBOSApi = {
  // Health
  getHealth: () => apiRequest("/api/health"),

  // Hardware Telemetry & KPIs
  getTelemetry: () => apiRequest("/api/telemetry"),

  // EV Catalogue, Users & Locations
  getEveCatalogue: () => apiRequest("/api/ev-catalogue"),
  getUsers: () => apiRequest("/api/users"),
  getLocations: () => apiRequest("/api/locations"),

  // Fleet Directory
  getFleet: () => apiRequest("/api/fleet"),
  registerEV: (payload) => apiRequest("/api/register-ev", "POST", payload),

  // Master Requests & Ready Queue PCBs
  getRequests: () => apiRequest("/api/requests"),
  getQueue: () => apiRequest("/api/queue"),
  admitRequest: (payload) => apiRequest("/api/admit-request", "POST", payload),

  // C++ Auto-Scheduler & Hardware Dispatch
  runAutoScheduler: () => apiRequest("/api/scheduler/auto", "POST", {}),
  allocateResources: () => apiRequest("/api/allocate", "POST", {}),

  // Session Simulation & Hardware Release
  simulateAndRelease: () => apiRequest("/api/sessions/simulate-release", "POST", {}),
};

