"""
=============================================================================
DBOS EV Charging Control Plane - Backend API Server
=============================================================================
A clean, beginner-friendly Python server that bridges the Frontend Dashboard
to our MySQL Database and MinGW C++ Operating System engines.

Designed for college project evaluation:
- Easy to explain line-by-line during viva.
- Uses Python's built-in standard library (no pip packages needed).
- Direct connection to existing services (ev_service, request_service, db.py).
- Safe multi-threaded request handling.
=============================================================================
"""

import os
import sys
import json
import decimal
import subprocess
import contextlib
import io
import socket
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.parse

# ---------------------------------------------------------------------------
# Setup Paths & Import Existing Backend Services
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Import existing backend modules (preserving business logic)
from db import (
    execute_select,
    execute_modify,
    get_waiting_requests,
    get_resource_allocation_inputs,
    get_all_charging_sessions,
    get_in_progress_sessions,
    get_allocations_without_session,
    start_charging_session_atomic
)
from ev_service import EV_CATALOGUE, get_all_evs, get_locations, register_ev
from user_service import register_user
from request_service import get_all_requests, create_charging_request, is_reservation_active
from process_manager import format_for_scheduler, compute_effective_priority, select_scheduling_strategy
from session_manager import auto_simulate_and_release_all
from resource_allocator import run_resource_allocation


# ===========================================================================
# 1. HELPER: Safe JSON Encoder for MySQL Data
# ===========================================================================
class DBOSJsonEncoder(json.JSONEncoder):
    """
    MySQL returns Decimal and datetime objects which Python's default json
    cannot convert. This helper converts them into floats and strings cleanly.
    """
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)


def send_json(handler, status_code, payload):
    """Sends a formatted JSON response with CORS headers to the browser."""
    response_bytes = json.dumps(payload, cls=DBOSJsonEncoder).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(response_bytes)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(response_bytes)


# ===========================================================================
# 2. GET API HANDLERS (Fetching Data from MySQL)
# ===========================================================================

def handle_get_health():
    """
    Checks if server and MySQL database are alive and responding.
    Used by the top-right green status indicator.
    """
    try:
        test = execute_select("SELECT 1 AS ok;")
        db_connected = (test and test[0]["ok"] == 1)
        db_status = "connected" if db_connected else "disconnected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return 200, {
        "success": True,
        "status": "online",
        "database": db_status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def handle_get_catalogue():
    """
    Returns EV types and battery capacities (kWh).
    Starts from the verified 8-vehicle EV_CATALOGUE and appends any distinct custom
    models registered in EV without owner or SoC details.
    """
    catalogue = [dict(item) for item in EV_CATALOGUE]
    seen_models = {item["model"].strip().lower() for item in catalogue}
    try:
        extra_models = execute_select(
            "SELECT model, MAX(battery_capacity) AS battery_capacity FROM EV GROUP BY model ORDER BY model ASC;"
        ) or []
        for row in extra_models:
            m = str(row.get("model", "")).strip()
            if m and m.lower() not in seen_models:
                catalogue.append({
                    "model": m,
                    "battery_capacity": float(row["battery_capacity"])
                })
                seen_models.add(m.lower())
    except Exception:
        pass

    return 200, {
        "success": True,
        "catalogue": catalogue
    }


def handle_get_users():
    """
    Returns registered drivers/owners from APP_USER ordered newest-first,
    so Tab 3 can assign a charging request to the exact owner without ambiguity.
    """
    query = "SELECT user_id, username, email, phone_no FROM APP_USER ORDER BY user_id DESC;"
    users = execute_select(query) or []
    return 200, {
        "success": True,
        "users": users
    }


def handle_get_locations():
    """
    Returns available charging hub locations from the LOCATION table.
    Used by Tab 2 (Registration) location dropdown.
    """
    locations = get_locations()
    return 200, {
        "success": True,
        "locations": locations or []
    }


def handle_get_fleet():
    """
    Returns all registered electric vehicles and their owners,
    along with their real-time operational status:
      - 'WAITING': Currently queued in the OS Ready Queue
      - 'RUNNING': Currently charging on an allocated station socket
      - 'IDLE': Parked / Available to submit new requests
    """
    query = """
        SELECT 
            e.ev_id, 
            e.user_id, 
            u.username, 
            e.model, 
            e.battery_capacity, 
            e.current_soc, 
            l.location_name,
            COALESCE((
                SELECT r.process_state 
                FROM CHARGING_REQUEST r 
                WHERE r.ev_id = e.ev_id AND r.process_state IN ('WAITING', 'READY', 'RUNNING')
                ORDER BY r.request_id DESC 
                LIMIT 1
            ), 'IDLE') AS active_status
        FROM EV e
        JOIN APP_USER u ON e.user_id = u.user_id
        JOIN LOCATION l ON e.current_location_id = l.location_id
        ORDER BY e.ev_id ASC;
    """
    try:
        fleet = execute_select(query)
    except Exception:
        fleet = get_all_evs()
        for f in fleet:
            f["active_status"] = "IDLE"

    return 200, {
        "success": True,
        "fleet": fleet or []
    }


def handle_get_requests():
    """
    Returns all master charging requests from the CHARGING_REQUEST table.
    Enriches each record with reservation grace-period validity.
    """
    try:
        requests = get_all_requests()
    except Exception:
        # Defensive fallback if live MySQL table does not yet have is_reserved column
        fallback_query = """
            SELECT 
                r.request_id,
                r.ev_id,
                e.model,
                u.username,
                r.arrival_time,
                r.required_energy,
                r.requested_power,
                r.soc_at_request,
                r.process_state
            FROM CHARGING_REQUEST r
            JOIN EV e ON r.ev_id = e.ev_id
            JOIN APP_USER u ON e.user_id = u.user_id
            ORDER BY r.request_id DESC;
        """
        requests = execute_select(fallback_query) or []
        for r in requests:
            r["is_reserved"] = False
            r["reserved_slot_time"] = None

    for r in requests:
        is_res = bool(r.get("is_reserved", False))
        r["reservation_active"] = is_reservation_active(r) if is_res else False

    return 200, {
        "success": True,
        "requests": requests or []
    }


def _compute_target_soc(soc_at_request, required_energy, battery_capacity):
    """Derives exact target SoC% from initial SoC, required kWh energy, and pack capacity."""
    soc = float(soc_at_request or 0.0)
    energy = float(required_energy or 0.0)
    cap = float(battery_capacity or 0.0)
    if cap <= 0.0:
        return 100.0 if soc >= 80.0 else 80.0
    raw_target = soc + (energy / cap) * 100.0
    clamped = min(100.0, max(soc, raw_target))
    nearest_int = round(clamped)
    if abs(clamped - nearest_int) <= 0.2:
        return float(nearest_int)
    return round(clamped, 1)


def handle_get_queue():
    """
    Fetches WAITING requests and formats them as Process Control Blocks (PCBs).
    Calculates:
      1. Burst Time = Required Energy / Requested Power
      2. Two-Tier Priority Score (with Anti-Starvation Aging)
      3. Target Battery SoC% derived from energy and pack capacity
    """
    waiting = get_waiting_requests()
    pcb_queue = []
    earliest = waiting[0]["arrival_time"] if waiting else None
    now = datetime.now()

    for r in waiting:
        pid = r["request_id"]
        ev_id = r["ev_id"]
        model = r["ev_model"]
        username = r.get("username", "")
        battery_cap = float(r.get("battery_capacity") or 0.0)
        req_energy = float(r["required_energy"])
        req_power = float(r["requested_power"])
        soc = float(r.get("soc_at_request", 50.0))
        target_soc = _compute_target_soc(soc, req_energy, battery_cap)

        # CPU Burst Time formula: Time = Energy / Power
        burst_time = round(req_energy / req_power, 2) if req_power > 0 else 0.0

        # Arrival offset from the first waiting job
        at_hours = 0.0
        if earliest and r.get("arrival_time"):
            at_hours = round((r["arrival_time"] - earliest).total_seconds() / 3600.0, 2)

        is_res = bool(r.get("is_reserved", False))
        res_active = is_reservation_active(r) if is_res else False

        priority_score, tier, tier_reason, aging_bonus = compute_effective_priority(r, now=now)

        pcb_queue.append({
            "request_id": pid,
            "ev_id": ev_id,
            "ev_model": model,
            "battery_capacity": battery_cap,
            "username": username,
            "arrival_time": r["arrival_time"],
            "arrival_offset_hours": at_hours,
            "required_energy": req_energy,
            "requested_power": req_power,
            "burst_time": burst_time,
            "soc_at_request": soc,
            "target_soc": target_soc,
            "is_reserved": is_res,
            "reserved_slot_time": r.get("reserved_slot_time"),
            "is_reservation_active": res_active,
            "priority_score": priority_score,
            "tier": tier,
            "tier_reason": tier_reason,
            "aging_bonus": aging_bonus,
            "process_state": r.get("process_state", "WAITING")
        })

    # Fetch currently active in-progress charging sessions
    active_in_progress = get_in_progress_sessions()
    active_charging = []
    for s in active_in_progress:
        req_power = float(s.get("allocated_power", 50.0))
        req_energy = float(s.get("required_energy", 20.0))
        init_soc = float(s.get("soc_at_request", 20.0))
        battery_cap = float(s.get("battery_capacity") or 0.0)
        target_soc = _compute_target_soc(init_soc, req_energy, battery_cap)
        bt = round(req_energy / req_power, 2) if req_power > 0 else 0.0
        active_charging.append({
            "session_id": s["session_id"],
            "allocation_id": s["allocation_id"],
            "request_id": s["request_id"],
            "ev_id": s.get("ev_id"),
            "ev_model": s["ev_model"],
            "battery_capacity": battery_cap,
            "username": s.get("username", ""),
            "charger_id": s["charger_id"],
            "station_id": s["station_id"],
            "station_name": s["station_name"],
            "allocated_power": req_power,
            "required_energy": req_energy,
            "soc_at_request": init_soc,
            "target_soc": target_soc,
            "burst_time": bt,
            "start_time": s.get("start_time"),
            "process_state": "RUNNING"
        })

    return 200, {
        "success": True,
        "count": len(pcb_queue),
        "queue": pcb_queue,
        "active_charging": active_charging
    }


def handle_get_telemetry():
    """
    Computes real-time hardware telemetry:
      - Total Station Capacity (kW)
      - Allocated Power & Remaining Power Headroom
      - Available vs Occupied Charger Ports
      - Waiting Queue count & Active Sessions count
    Used by the top KPI banner.
    """
    requests, stations, chargers = get_resource_allocation_inputs()
    sessions = get_all_charging_sessions()

    total_power = sum(float(s["total_power"]) for s in stations)
    used_power = sum(float(s["used_power"]) for s in stations)
    remaining_power = max(0.0, total_power - used_power)

    occupied_chargers = len([c for c in chargers if c.get("status") == "OCCUPIED"])
    available_chargers = len([c for c in chargers if c.get("status") == "AVAILABLE"])
    active_sessions = len([s for s in sessions if s.get("status") == "IN_PROGRESS"])
    completed_sessions = len([s for s in sessions if s.get("status") == "COMPLETED"])

    utilization_pct = round((used_power / total_power * 100), 1) if total_power > 0 else 0.0

    return 200, {
        "success": True,
        "telemetry": {
            "total_power_kw": round(total_power, 2),
            "used_power_kw": round(used_power, 2),
            "remaining_power_kw": round(remaining_power, 2),
            "power_utilization_pct": utilization_pct,
            "available_chargers": available_chargers,
            "occupied_chargers": occupied_chargers,
            "waiting_requests": len(requests),
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions
        },
        "stations": stations,
        "chargers": chargers,
        "sessions": sessions
    }


# ===========================================================================
# 3. POST API HANDLERS (Executing Actions: Register, Admit, Schedule)
# ===========================================================================

def handle_post_register_ev(data):
    """
    Tab 2 Action: Registers a new user and EV in MySQL.
    Validates user contact info, EV model, battery capacity, and SoC.
    """
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()
    model = str(data.get("model", "")).strip()
    battery_capacity = data.get("battery_capacity")
    current_soc = data.get("current_soc")
    location_id = data.get("location_id")

    # Step 1: Basic validation
    if not username or not email or not phone:
        return 400, {"success": False, "error": "Username, email, and phone number are required."}

    if not model:
        return 400, {"success": False, "error": "EV model selection or entry is required."}

    # Step 2: Validate against EV catalogue or enforce custom limits
    catalogue_item = next((item for item in EV_CATALOGUE if item["model"].lower() == model.lower()), None)
    if catalogue_item:
        battery_capacity = catalogue_item["battery_capacity"]
    else:
        try:
            battery_capacity = float(battery_capacity)
            if not (5.0 <= battery_capacity <= 250.0):
                return 400, {"success": False, "error": "Battery capacity must be between 5.0 and 250.0 kWh."}
        except (ValueError, TypeError):
            return 400, {"success": False, "error": "Battery capacity must be a valid number."}

    # Step 3: Validate SoC percentage
    try:
        current_soc = float(current_soc)
        if not (0.0 <= current_soc <= 100.0):
            return 400, {"success": False, "error": "Current SoC must be between 0.0% and 100.0%."}
    except (ValueError, TypeError):
        return 400, {"success": False, "error": "Current SoC must be a valid number."}

    # Step 4: Validate Location ID
    try:
        location_id = int(location_id)
    except (ValueError, TypeError):
        return 400, {"success": False, "error": "Valid location_id is required."}

    # Step 5: Save User and EV in Database
    user_id = register_user(username, email, phone)
    if not user_id:
        return 500, {"success": False, "error": "Could not register user in database."}

    success = register_ev(user_id, model, battery_capacity, current_soc, location_id)
    if success:
        ev_rows = execute_select("SELECT ev_id FROM EV WHERE user_id = %s ORDER BY ev_id DESC LIMIT 1;", (user_id,))
        ev_id = ev_rows[0]["ev_id"] if ev_rows else None
        return 201, {
            "success": True,
            "message": f"EV '{model}' successfully registered for user '{username}'.",
            "user_id": user_id,
            "ev_id": ev_id,
            "username": username,
            "model": model,
            "battery_capacity": battery_capacity,
            "current_soc": current_soc
        }
    else:
        return 500, {"success": False, "error": "Database error while inserting EV record."}


def _resolve_or_create_user(user_id, username):
    """Resolves an existing APP_USER by user_id or username, or creates a walk-in profile."""
    if user_id is not None and str(user_id).strip() != "":
        try:
            uid = int(user_id)
            rows = execute_select("SELECT user_id, username FROM APP_USER WHERE user_id = %s LIMIT 1;", (uid,))
            if rows:
                return rows[0]["user_id"], rows[0]["username"]
        except (ValueError, TypeError):
            pass

    if username:
        rows = execute_select(
            "SELECT user_id, username FROM APP_USER WHERE LOWER(username) = LOWER(%s) ORDER BY user_id DESC LIMIT 1;",
            (username,)
        )
        if rows:
            return rows[0]["user_id"], rows[0]["username"]

        clean_name = username[:50]
        slug = "".join(ch if ch.isalnum() else "_" for ch in clean_name.lower()).strip("_")[:30] or "driver"
        unique_email = f"{slug}_{int(datetime.now().timestamp() * 1000)}@walkin.dbos"
        new_uid = register_user(clean_name, unique_email, "9000000000")
        if new_uid:
            return new_uid, clean_name

    return None, None


def _resolve_or_create_user_ev(user_id, model, battery_capacity, current_soc):
    """
    Finds an EV owned STRICTLY by user_id matching the requested model, or creates
    a new EV record for that user so requests are never misattributed to another owner.
    """
    match = execute_select(
        "SELECT ev_id FROM EV WHERE user_id = %s AND LOWER(model) = LOWER(%s) ORDER BY ev_id DESC LIMIT 1;",
        (user_id, model)
    )
    if not match:
        match = execute_select(
            "SELECT ev_id FROM EV WHERE user_id = %s AND LOWER(model) LIKE LOWER(%s) ORDER BY ev_id DESC LIMIT 1;",
            (user_id, f"%{model}%")
        )

    if match:
        ev_id = match[0]["ev_id"]
        if current_soc is not None:
            try:
                execute_modify("UPDATE EV SET current_soc = %s WHERE ev_id = %s;", (float(current_soc), ev_id))
            except Exception:
                pass
        return ev_id

    user_loc = execute_select("SELECT current_location_id FROM EV WHERE user_id = %s ORDER BY ev_id DESC LIMIT 1;", (user_id,))
    if user_loc:
        lid = user_loc[0]["current_location_id"]
    else:
        loc_rows = execute_select("SELECT location_id FROM LOCATION ORDER BY location_id ASC LIMIT 1;")
        lid = loc_rows[0]["location_id"] if loc_rows else 1

    cat_item = next((c for c in EV_CATALOGUE if c["model"].lower() == model.lower()), None)
    cap = float(cat_item["battery_capacity"]) if cat_item else float(battery_capacity or 50.0)
    soc = float(current_soc if current_soc is not None else 20.0)
    return execute_modify(
        "INSERT INTO EV (user_id, model, battery_capacity, current_soc, current_location_id) VALUES (%s, %s, %s, %s, %s);",
        (user_id, model, cap, soc, lid)
    )


def handle_post_admit_request(data):
    """
    Tab 3 Action: Admits a charging request into the OS Ready Queue (process_state = 'WAITING').
    Resolves owner + EV strictly per person so requests are never assigned to another owner.
    """
    user_id = data.get("user_id")
    username = str(data.get("username", "")).strip()
    ev_id = data.get("ev_id")
    model = str(data.get("model", "")).strip()
    battery_capacity = data.get("battery_capacity")
    required_energy = data.get("required_energy")
    requested_power = data.get("requested_power")
    soc_at_request = data.get("soc_at_request")
    is_reserved = bool(data.get("is_reserved", False))
    reserved_slot_time = data.get("reserved_slot_time")

    resolved_uid, resolved_username = _resolve_or_create_user(user_id, username)

    # Guard against mismatched ev_id when an explicit owner was provided
    if ev_id and resolved_uid:
        owner_check = execute_select("SELECT ev_id FROM EV WHERE ev_id = %s AND user_id = %s;", (int(ev_id), resolved_uid))
        if not owner_check:
            ev_id = None

    if not ev_id:
        if not resolved_uid:
            return 400, {"success": False, "error": "Driver / Owner (user_id or username) is required so the request is assigned to the correct person."}
        if not model:
            return 400, {"success": False, "error": "EV model selection is required."}
        try:
            ev_id = _resolve_or_create_user_ev(resolved_uid, model, battery_capacity, soc_at_request)
        except Exception as e:
            return 500, {"success": False, "error": f"Failed to resolve vehicle for '{resolved_username}': {str(e)}"}

    if not ev_id or required_energy is None or requested_power is None or soc_at_request is None:
        return 400, {"success": False, "error": "Owner, EV model, required_energy, requested_power, and soc_at_request are required."}

    try:
        ev_id = int(ev_id)
        required_energy = float(required_energy)
        requested_power = float(requested_power)
        soc_at_request = float(soc_at_request)
    except (ValueError, TypeError):
        return 400, {"success": False, "error": "Numeric values are required for energy, power, and SoC."}

    if required_energy <= 0 or requested_power <= 0:
        return 400, {"success": False, "error": "Required energy and power must be greater than zero."}

    # Try inserting via request_service
    res_id = create_charging_request(
        ev_id=ev_id,
        required_energy=required_energy,
        requested_power=requested_power,
        soc_at_request=soc_at_request,
        is_reserved=is_reserved,
        reserved_slot_time=reserved_slot_time
    )

    # Defensive fallback if live database table lacks is_reserved/reserved_slot_time columns
    if not res_id:
        try:
            basic_sql = """
                INSERT INTO CHARGING_REQUEST (ev_id, required_energy, requested_power, soc_at_request, process_state)
                VALUES (%s, %s, %s, %s, 'WAITING');
            """
            res_id = execute_modify(basic_sql, (ev_id, required_energy, requested_power, soc_at_request))
        except Exception as e:
            return 500, {"success": False, "error": f"Failed to insert request into queue: {str(e)}"}

    burst_time = round(required_energy / requested_power, 2)
    pid_str = f"P{res_id}" if isinstance(res_id, (int, str)) and int(res_id) > 1 else f"EV #{ev_id}"
    owner_note = f" for {resolved_username}" if resolved_username else ""
    return 201, {
        "success": True,
        "message": f"Charging request {pid_str}{owner_note} successfully admitted into WAITING queue.",
        "request_id": int(res_id) if isinstance(res_id, (int, str)) and int(res_id) > 1 else None,
        "ev_id": ev_id,
        "user_id": resolved_uid,
        "username": resolved_username,
        "burst_time_hours": burst_time
    }


def handle_post_auto_scheduler():
    """
    Tab 1 Action: Executes the Intelligent Auto-Scheduler (with Anti-Starvation Aging).
    Runs the compiled C++ executable (priority.exe, sjf.exe, or fcfs.exe)
    with captured stdout and returns the real scheduling results.
    """
    requests = get_waiting_requests()
    if not requests:
        return 200, {
            "success": False,
            "message": "No waiting charging requests found in the database queue.",
            "waiting_count": 0
        }

    selected_exe, algo_name, reason = select_scheduling_strategy(requests)

    # Format input for C++ scheduler via stdin
    input_text = format_for_scheduler(requests)

    # Locate executable
    exe_path = os.path.join(BACKEND_DIR, f"{selected_exe}.exe")
    if not os.path.exists(exe_path):
        return 500, {
            "success": False,
            "error": f"C++ Executable '{selected_exe}.exe' not found in backend directory."
        }

    # Execute C++ binary with direct stdout capture
    try:
        proc = subprocess.run([exe_path], input=input_text, text=True, capture_output=True, check=True)
        cpp_output = proc.stdout
    except subprocess.CalledProcessError as e:
        cpp_output = e.output or str(e)
    except Exception as e:
        return 500, {"success": False, "error": f"Failed running C++ scheduler: {str(e)}"}

    # Format complete console display
    banner = [
        "=" * 65,
        "           INTELLIGENT ADAPTIVE SCHEDULER (C++ ENGINE)",
        "=" * 65,
        f"  Waiting Requests       : {len(requests)}",
        f"  Auto-Selected Algorithm: {algo_name}",
        f"  Decision Reason        : {reason}",
        "=" * 65,
        ""
    ]
    full_output = "\n".join(banner) + cpp_output

    return 200, {
        "success": True,
        "algorithm": algo_name,
        "selected_executable": selected_exe,
        "reason": reason,
        "waiting_count": len(requests),
        "console_output": full_output
    }


def handle_post_allocate():
    """
    Tab 1 Action: Executes the C++ Resource Allocator & Charger Dispatcher.
    Applies proposals and rejections atomically to MySQL using
    commit_resource_allocations_atomic(). Transitions requests WAITING -> RUNNING.
    Automatically initializes the charging session in IN_PROGRESS state.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        run_resource_allocation()
        # Automatically initialize charging session for newly dispatched requests
        pending = get_allocations_without_session()
        for p in pending:
            sess_id, err = start_charging_session_atomic(p["allocation_id"])
            if sess_id:
                print(f"[ACTIVE] Charging Session #{sess_id} started for Request P{p['request_id']} on Charger #{p['charger_id']}.")
    output_log = buffer.getvalue()

    return 200, {
        "success": True,
        "message": "Resource allocation and hardware dispatch completed.",
        "console_output": output_log
    }


def handle_post_simulate_release():
    """
    Tab 1 Action: Simulates charging session completion and releases hardware resources.
    Marks sessions COMPLETED, frees chargers to AVAILABLE, and restores station power.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        auto_simulate_and_release_all()
    output_log = buffer.getvalue()

    return 200, {
        "success": True,
        "message": "Session simulation and atomic resource release completed.",
        "console_output": output_log
    }


# ===========================================================================
# 4. HTTP REQUEST ROUTER & STATIC ASSET SERVER
# ===========================================================================

class DBOSRequestHandler(SimpleHTTPRequestHandler):
    """
    Standard HTTP Request Handler:
    - Serves static frontend files (HTML, CSS, JS) from the ../frontend folder.
    - Routes /api/* calls to the clean functions defined above.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        """Prevents stale browser caching of ES modules, HTML, CSS, and API responses."""
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        """Allows browser CORS preflight checks."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handles all GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path.startswith("/api"):
            try:
                # Map API URLs to their respective simple handler functions
                get_routes = {
                    "/api/health": handle_get_health,
                    "/api/ev-catalogue": handle_get_catalogue,
                    "/api/users": handle_get_users,
                    "/api/locations": handle_get_locations,
                    "/api/fleet": handle_get_fleet,
                    "/api/requests": handle_get_requests,
                    "/api/queue": handle_get_queue,
                    "/api/telemetry": handle_get_telemetry,
                    "/api/allocate": handle_post_allocate,
                    "/api/allocate-chargers": handle_post_allocate,
                    "/api/resource-allocation": handle_post_allocate,
                    "/api/scheduler/auto": handle_post_auto_scheduler,
                    "/api/sessions/simulate-release": handle_post_simulate_release,
                }

                handler_fn = get_routes.get(path)
                if handler_fn:
                    status_code, payload = handler_fn()
                    send_json(self, status_code, payload)
                else:
                    send_json(self, 404, {"success": False, "error": f"GET Endpoint '{path}' not found."})

            except Exception as e:
                send_json(self, 500, {"success": False, "error": f"Internal Server Error: {str(e)}"})
        else:
            # Fallback to index.html for Single Page Application navigation
            target_path = os.path.join(FRONTEND_DIR, path.lstrip("/"))
            if not os.path.exists(target_path) and not os.path.isdir(target_path):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        """Handles all POST requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/api"):
            try:
                # Read JSON body sent by browser
                content_len = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(content_len) if content_len > 0 else b"{}"
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}

                # Map POST URLs to their respective handler functions with aliases
                if path in ("/api/register-ev", "/api/register"):
                    status_code, payload = handle_post_register_ev(data)
                elif path in ("/api/admit-request", "/api/admit"):
                    status_code, payload = handle_post_admit_request(data)
                elif path in ("/api/scheduler/auto", "/api/scheduler", "/api/schedule"):
                    status_code, payload = handle_post_auto_scheduler()
                elif path in ("/api/allocate", "/api/allocate-chargers", "/api/resource-allocation", "/api/dispatch"):
                    status_code, payload = handle_post_allocate()
                elif path in ("/api/sessions/simulate-release", "/api/simulate-release", "/api/release"):
                    status_code, payload = handle_post_simulate_release()
                else:
                    status_code, payload = 404, {"success": False, "error": f"POST Endpoint '{path}' not found."}

                send_json(self, status_code, payload)

            except json.JSONDecodeError:
                send_json(self, 400, {"success": False, "error": "Invalid JSON payload sent in request."})
            except Exception as e:
                send_json(self, 500, {"success": False, "error": f"Internal Server Error: {str(e)}"})
        else:
            self.send_error(404, "Endpoint not found.")


# ===========================================================================
# 5. SERVER ENTRY POINT
# ===========================================================================

class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    """Prevents silent port stacking on Windows so only one server owns port 8000."""
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def run_server(port=8000):
    """Starts the multi-threaded HTTP server."""
    server_address = ("", port)
    httpd = ExclusiveThreadingHTTPServer(server_address, DBOSRequestHandler)
    print("=" * 60)
    print("  DBOS EV CONTROL PLANE - BACKEND API SERVER RUNNING")
    print("=" * 60)
    print(f"  Access URL : http://localhost:{port}")
    print(f"  Frontend   : {FRONTEND_DIR}")
    print("=" * 60)
    print("  Press Ctrl+C in this terminal window to stop the server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOPPED] Shutting down DBOS Server...")
        httpd.shutdown()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port_arg)
