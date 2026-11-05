"""
Charging Request Service Module
Handles creation and retrieval of charging requests (OS Processes) from the CHARGING_REQUEST table.
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from datetime import datetime, timedelta
from db import execute_select, execute_modify

GRACE_PERIOD_MINUTES = 15


def is_reservation_active(request):
    """
    Checks if a reservation is active within its designated window + 15 min grace period.
    """
    if not request.get("is_reserved"):
        return False
    slot_time = request.get("reserved_slot_time")
    if not slot_time:
        return True
    if isinstance(slot_time, str):
        try:
            slot_time = datetime.strptime(slot_time, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return True
    return datetime.now() <= (slot_time + timedelta(minutes=GRACE_PERIOD_MINUTES))


def get_all_requests():
    """
    Fetches all charging requests with EV model, owner information, and reservation status.
    """
    query = """
        SELECT 
            r.request_id,
            r.ev_id,
            e.model,
            u.username,
            r.arrival_time,
            r.required_energy,
            r.requested_power,
            r.soc_at_request,
            r.is_reserved,
            r.reserved_slot_time,
            r.process_state
        FROM CHARGING_REQUEST r
        JOIN EV e ON r.ev_id = e.ev_id
        JOIN APP_USER u ON e.user_id = u.user_id
        ORDER BY r.request_id ASC;
    """
    try:
        return execute_select(query)
    except Exception:
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
                r.is_reserved,
                r.process_state
            FROM CHARGING_REQUEST r
            JOIN EV e ON r.ev_id = e.ev_id
            JOIN APP_USER u ON e.user_id = u.user_id
            ORDER BY r.request_id ASC;
        """
        rows = execute_select(fallback_query)
        if rows:
            for row in rows:
                row["reserved_slot_time"] = None
        return rows


def display_requests():
    """
    Displays all charging requests in a cleanly formatted table with exact column widths.
    Prevents long usernames or models from misaligning the table.
    """
    requests = get_all_requests()
    width = 118
    print("\n" + "=" * width)
    print(f"{'Req ID':<7} | {'EV Model':<18} | {'Owner':<12} | {'Energy':>7} | {'Power':>7} | {'SoC':>6} | {'Burst':>6} | {'Booking Type':<16} | {'State':<10}")
    print("=" * width)
    if not requests:
        print("No charging requests found in the database.")
    else:
        for r in requests:
            req_id_str = f"P{r['request_id']}"
            model = str(r["model"])[:18]
            owner = str(r["username"])[:12]
            req_energy = float(r["required_energy"])
            req_power = float(r["requested_power"])
            soc = float(r["soc_at_request"])
            burst_time = req_energy / req_power if req_power > 0 else 0.0
            is_res = bool(r.get("is_reserved", False))
            if is_res:
                active = is_reservation_active(r)
                booking_type = "RESERVED (Active)" if active else "EXPIRED (Late)"
            else:
                booking_type = "WALK-IN"

            state = str(r["process_state"])[:10]

            print(
                f"{req_id_str:<7} | "
                f"{model:<18} | "
                f"{owner:<12} | "
                f"{req_energy:>5.1f}kW | "
                f"{req_power:>5.1f}kW | "
                f"{soc:>5.1f}% | "
                f"{burst_time:>5.2f}h | "
                f"{booking_type:<16} | "
                f"{state:<10}"
            )
    print("=" * width + "\n")


def create_charging_request(ev_id, required_energy, requested_power, soc_at_request, is_reserved=False, reserved_slot_time=None):
    """
    Inserts a new charging request process into CHARGING_REQUEST table with default state 'WAITING'.
    Supports is_reserved flag and designated reserved_slot_time.
    Returns True on success, False on failure.
    """
    query_full = """
        INSERT INTO CHARGING_REQUEST (ev_id, required_energy, requested_power, soc_at_request, is_reserved, reserved_slot_time, process_state)
        VALUES (%s, %s, %s, %s, %s, %s, 'WAITING');
    """
    try:
        execute_modify(query_full, (ev_id, required_energy, requested_power, soc_at_request, is_reserved, reserved_slot_time))
        return True
    except Exception:
        fallback_query = """
            INSERT INTO CHARGING_REQUEST (ev_id, required_energy, requested_power, soc_at_request, is_reserved, process_state)
            VALUES (%s, %s, %s, %s, %s, 'WAITING');
        """
        try:
            execute_modify(fallback_query, (ev_id, required_energy, requested_power, soc_at_request, is_reserved))
            return True
        except Exception as e:
            print(f"[ERROR] Could not create charging request: {e}")
            return False


def create_request_interactive():
    """
    Prompts user for charging request with realistic automotive flow:
    1. Select an EV from registered vehicles.
    2. Input Target Battery % (SoC) - e.g. 80% or 100%.
    3. Formula calculates Required Energy (kWh) = Battery_Capacity * (Target_SoC - Current_SoC) / 100.
    4. Select a Charger from real available options (22 kW, 50 kW, 60 kW).
    5. Formula calculates Duration / Burst Time (hours) = Required_Energy / Selected_Power.
    6. Saves into CHARGING_REQUEST table with state 'WAITING'.
    """
    print("\n=======================================================")
    print("      CREATE NEW EV CHARGING REQUEST (OS PROCESS)")
    print("=======================================================")

    available_evs = execute_select("SELECT ev_id, model, battery_capacity, current_soc FROM EV ORDER BY ev_id ASC;")
    if not available_evs:
        print("[ERROR] No registered EVs found in database. Please register an EV first.\n")
        return

    print("Registered Vehicles:")
    for ev in available_evs:
        print(f"  [EV ID: {ev['ev_id']:<2}] {ev['model']:<22} | Battery: {float(ev['battery_capacity']):.1f} kWh | Current SoC: {float(ev['current_soc']):.1f}%")
    print()

    try:
        ev_id = int(input("Enter EV ID from the list above: ").strip())
    except ValueError:
        print("[ERROR] EV ID must be a valid number. Request cancelled.\n")
        return

    selected_ev = next((e for e in available_evs if e["ev_id"] == ev_id), None)
    if not selected_ev:
        print(f"[ERROR] Vehicle with EV ID {ev_id} not found.\n")
        return

    battery_cap = float(selected_ev["battery_capacity"])
    current_soc = float(selected_ev["current_soc"])

    print(f"\n-> Selected Vehicle: {selected_ev['model']}")
    print(f"   Battery Capacity : {battery_cap:.2f} kWh")
    print(f"   Current Battery  : {current_soc:.1f}%\n")

    if current_soc >= 100.0:
        print("[INFO] This vehicle is already at 100% SoC. No charging needed!\n")
        return

    print("--- Step 1: Target Battery Percentage ---")
    try:
        target_input = input(f"Enter Target Battery % (current is {current_soc:.1f}%, e.g. 80 or 100): ").strip()
        target_soc = float(target_input)
        if target_soc <= current_soc or target_soc > 100.0:
            print(f"[ERROR] Target SoC must be greater than current SoC ({current_soc:.1f}%) and at most 100%.\n")
            return
    except ValueError:
        print("[ERROR] Target SoC must be a valid number.\n")
        return

    delta_soc = target_soc - current_soc
    required_energy = round(battery_cap * (delta_soc / 100.0), 2)

    print(f"\n[FORMULA CALCULATION]")
    print(f"  Delta SoC to charge = {target_soc:.1f}% - {current_soc:.1f}% = +{delta_soc:.1f}%")
    print(f"  Required Energy     = {battery_cap:.2f} kWh * ({delta_soc:.1f} / 100) = {required_energy:.2f} kWh\n")

    print("--- Step 2: Select Charger Type ---")
    chargers_query = """
        SELECT DISTINCT connector_type, power_capacity 
        FROM CHARGER 
        ORDER BY power_capacity ASC;
    """
    available_chargers = execute_select(chargers_query)
    if not available_chargers:
        print("[ERROR] No chargers found in database.\n")
        return

    for idx, c in enumerate(available_chargers, 1):
        c_type = c["connector_type"]
        c_power = float(c["power_capacity"])
        label = "Standard AC" if c_power <= 22 else ("Ultra-Fast DC" if c_power >= 60 else "Fast DC")
        print(f"  [{idx}] {c_type:<8} ({c_power:.1f} kW) - {label}")

    try:
        c_choice = int(input(f"\nSelect Charger Option [1-{len(available_chargers)}]: ").strip())
        if not (1 <= c_choice <= len(available_chargers)):
            print("[ERROR] Invalid charger option selected.\n")
            return
        selected_charger = available_chargers[c_choice - 1]
        requested_power = float(selected_charger["power_capacity"])
        connector_type = selected_charger["connector_type"]
    except ValueError:
        print("[ERROR] Please enter a valid number.\n")
        return

    burst_time = round(required_energy / requested_power, 2)
    burst_mins = round(burst_time * 60.0, 1)

    print("\n--- Step 3: Booking Type & Designated Arrival Time ---")
    booking_input = input("Has this charger slot been pre-booked in advance? (y/N): ").strip().lower()
    is_reserved = booking_input in ["y", "yes", "1", "true"]
    reserved_slot_time = None

    if is_reserved:
        time_input = input(f"Enter designated arrival time (HH:MM) [Press Enter for immediate now]: ").strip()
        if time_input:
            try:
                from datetime import time
                today = datetime.now().date()
                h, m = map(int, time_input.split(":"))
                reserved_slot_time = datetime.combine(today, time(h, m))
            except Exception:
                reserved_slot_time = datetime.now()
        else:
            reserved_slot_time = datetime.now()

        expiry_dt = reserved_slot_time + timedelta(minutes=GRACE_PERIOD_MINUTES)
        booking_label = f"RESERVED (Slot: {reserved_slot_time.strftime('%H:%M')}, Expiry: {expiry_dt.strftime('%H:%M')})"
    else:
        booking_label = "WALK-IN (Standard)"

    print(f"-> Classified as: {booking_label}")

    print(f"\n[CHARGING ESTIMATE]")
    print(f"  Requested Power  : {requested_power:.2f} kW ({connector_type})")
    print(f"  OS Burst Time    : {required_energy:.2f} kWh / {requested_power:.2f} kW = {burst_time:.2f} hrs ({burst_mins:.1f} mins)\n")

    success = create_charging_request(ev_id, required_energy, requested_power, current_soc, is_reserved=is_reserved, reserved_slot_time=reserved_slot_time)
    if success:
        print("=======================================================")
        print("     [SUCCESS] CHARGING REQUEST CREATED SUCCESSFULLY")
        print("=======================================================")
        print(f"  EV Model         : {selected_ev['model']}")
        print(f"  Booking Type     : {booking_label}")
        print(f"  Battery Charge   : {current_soc:.1f}% -> {target_soc:.1f}% (+{delta_soc:.1f}%)")
        print(f"  Energy to Deliver: {required_energy:.2f} kWh")
        print(f"  Selected Charger : {connector_type} ({requested_power:.2f} kW)")
        print(f"  Estimated Time   : {burst_time:.2f} hours ({burst_mins:.1f} minutes)")
        print(f"  Process State    : 'WAITING' (Enqueued in Ready Queue)")
        print("=======================================================\n")
    else:
        print("[FAILED] Could not save charging request to database.\n")

