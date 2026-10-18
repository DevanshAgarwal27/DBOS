"""
Step 7: Charging Sessions and OS Performance Metrics Module
A clean, beginner-friendly Python bridge between MySQL and C++ OS engines:
1. Manages EV Charging Session lifecycle (START -> IN_PROGRESS -> COMPLETED).
2. Atomically releases resources (frees charger and restores station power).
3. Calculates OS Performance Metrics (AT, BT, CT, TAT, WT across FCFS, SJF, Priority).
"""

import os
import sys
import subprocess

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from db import (
    get_all_charging_sessions,
    get_allocations_without_session,
    start_charging_session_atomic,
    get_in_progress_sessions,
    complete_charging_session_atomic,
    get_all_requests_for_metrics
)


def ensure_executable(cpp_name, exe_name):
    exe_path = os.path.join(backend_dir, exe_name)
    cpp_path = os.path.join(backend_dir, cpp_name)

    if not os.path.exists(exe_path) and os.path.exists(cpp_path):
        try:
            subprocess.run(["g++", "-o", exe_path, cpp_path], check=True)
        except Exception as e:
            print(f"[WARNING] Could not auto-compile {cpp_name}: {e}")
    return exe_path


def display_charging_sessions():
    sessions = get_all_charging_sessions()
    print("\n" + "=" * 95)
    print(f"{'Sess ID':<8} | {'Alloc ID':<9} | {'Req ID':<7} | {'EV Model':<22} | {'Charger':<8} | {'Start Time':<19} | {'Energy(kWh)':<11} | {'Status':<11}")
    print("=" * 95)
    
    if not sessions:
        print("No charging sessions found in the database.")
    else:
        for s in sessions:
            st_time = s["start_time"].strftime("%Y-%m-%d %H:%M") if s["start_time"] else "N/A"
            energy = float(s["energy_consumed"])
            print(f"{s['session_id']:<8} | {s['allocation_id']:<9} | {s['request_id']:<7} | {s['ev_model']:<22} | "
                  f"#{s['charger_id']:<7} | {st_time:<19} | {energy:<11.2f} | {s['status']:<11}")
    print("=" * 95 + "\n")


def start_new_session_interactive():
    print("\n--- Start New Charging Session ---")
    allocations = get_allocations_without_session()
    if not allocations:
        print("[INFO] No active allocations waiting to start a session.")
        print("       Run Step 5 (Resource Allocation) first to allocate requests.\n")
        return

    print("Active Allocations Ready to Start Charging:")
    for a in allocations:
        print(f"  [Alloc #{a['allocation_id']}] Request P{a['request_id']} ({a['ev_model']}) | Charger #{a['charger_id']} | Power: {float(a['allocated_power']):.2f} kW")

    try:
        alloc_id_input = input("\nEnter Allocation ID to start session: ").strip()
        alloc_id = int(alloc_id_input)
    except ValueError:
        print("[ERROR] Please enter a valid number.\n")
        return

    selected = next((a for a in allocations if a["allocation_id"] == alloc_id), None)
    if not selected:
        print(f"[ERROR] Allocation #{alloc_id} is not valid to start.\n")
        return

    exe_path = ensure_executable("charging_session.cpp", "charging_session.exe")
    if os.path.exists(exe_path):
        model_name = str(selected["ev_model"]).replace(" ", "_")
        cpp_input = f"START {alloc_id} {selected['request_id']} {selected['charger_id']} {model_name} {float(selected['allocated_power']):.2f}\n"
        proc = subprocess.run([exe_path], input=cpp_input, text=True, capture_output=True)
        print(proc.stdout)

    session_id, error = start_charging_session_atomic(alloc_id)
    if error is None:
        print(f"[SUCCESS] Charging Session #{session_id} is now IN_PROGRESS!")
        print(f"          EV '{selected['ev_model']}' is actively charging.\n")
    else:
        print(f"[FAILED] Could not start session: {error}\n")


def complete_session_interactive():
    """
    Completes a charging session and releases hardware resources:
    - Lists all IN_PROGRESS charging sessions.
    - C++ engine calculates session duration and validates RUNNING -> COMPLETED.
    - MySQL transaction: marks session COMPLETED, releases charger port,
      restores station power, and marks request COMPLETED.
    """
    print("\n--- Complete Charging Session & Release Resources ---")
    sessions = get_in_progress_sessions()
    if not sessions:
        print("[INFO] No charging sessions are currently IN_PROGRESS.\n")
        return

    print("Active Sessions Currently Charging:")
    for s in sessions:
        print(f"  [Session #{s['session_id']}] Request P{s['request_id']} ({s['ev_model']}) | Charger #{s['charger_id']} at Station #{s['station_id']}")

    try:
        sess_id_input = input("\nEnter Session ID to complete: ").strip()
        session_id = int(sess_id_input)
    except ValueError:
        print("[ERROR] Please enter a valid number.\n")
        return

    selected = next((s for s in sessions if s["session_id"] == session_id), None)
    if not selected:
        print(f"[ERROR] Session #{session_id} is not currently IN_PROGRESS.\n")
        return

    exe_path = ensure_executable("charging_session.cpp", "charging_session.exe")
    if os.path.exists(exe_path):
        model_name = str(selected["ev_model"]).replace(" ", "_")
        cpp_input = (f"COMPLETE {session_id} {selected['allocation_id']} {selected['request_id']} "
                     f"{selected['charger_id']} {selected['station_id']} {model_name} "
                     f"{float(selected['required_energy']):.2f} {float(selected['allocated_power']):.2f}\n")
        proc = subprocess.run([exe_path], input=cpp_input, text=True, capture_output=True)
        print(proc.stdout)

    row, error = complete_charging_session_atomic(session_id)
    if error is None:
        print(f"[SUCCESS] Session #{session_id} completed successfully!")
        print(f"  - Released Charger #{selected['charger_id']} back to 'AVAILABLE' state")
        print(f"  - Restored +{float(selected['allocated_power']):.2f} kW power capacity to Station #{selected['station_id']}")
        print(f"  - Request P{selected['request_id']} marked as 'COMPLETED'\n")
    else:
        print(f"[FAILED] Could not complete session: {error}\n")


def auto_simulate_and_release_all():
    print("\n" + "=" * 65)
    print("   AUTOMATED OS CHARGING LIFECYCLE & AUTO-RELEASE ENGINE")
    print("=" * 65)

    pending_allocations = get_allocations_without_session()
    if pending_allocations:
        print(f"-> Auto-starting {len(pending_allocations)} pending allocation(s)...")
        for a in pending_allocations:
            sess_id, err = start_charging_session_atomic(a["allocation_id"])
            if err is None:
                print(f"   [STARTED] Session #{sess_id} for Request P{a['request_id']} ({a['ev_model']}) on Charger #{a['charger_id']}")
            else:
                print(f"   [ERROR] Could not start session for Alloc #{a['allocation_id']}: {err}")
        print()

    active_sessions = get_in_progress_sessions()
    if not active_sessions:
        print("[INFO] No active sessions are currently charging.")
        print("       Run Step 5 (Resource Allocation) first to allocate waiting requests.\n")
        return

    print(f"-> Found {len(active_sessions)} active charging session(s) to simulate and release:\n")

    exe_path = ensure_executable("charging_session.cpp", "charging_session.exe")

    completed_count = 0
    for idx, s in enumerate(active_sessions, 1):
        sess_id = s["session_id"]
        req_id = s["request_id"]
        model = s["ev_model"]
        charger_id = s["charger_id"]
        station_id = s["station_id"]
        station_name = s["station_name"]
        power = float(s["allocated_power"])
        energy = float(s["required_energy"])

        print(f"--- [{idx}/{len(active_sessions)}] Simulating Session #{sess_id} for P{req_id} ({model}) ---")
        print(f"  Charger      : Port #{charger_id} at Station #{station_id} ({station_name})")
        print(f"  Allocated    : {power:.2f} kW | Energy: {energy:.2f} kWh")
        print(f"  Charging...  : [====================] 100% Complete!")

        if os.path.exists(exe_path):
            model_name = str(model).replace(" ", "_")
            cpp_input = f"COMPLETE {sess_id} {s['allocation_id']} {req_id} {charger_id} {station_id} {model_name} {energy:.2f} {power:.2f}\n"
            proc = subprocess.run([exe_path], input=cpp_input, text=True, capture_output=True)
            for line in proc.stdout.splitlines():
                if "Duration" in line or "Deallocation" in line or "Restored" in line or "AVAILABLE" in line:
                    print(f"  {line}")

        row, error = complete_charging_session_atomic(sess_id)
        if error is None:
            print(f"  [RELEASED] Session #{sess_id} completed successfully!")
            print(f"   -> Charger #{charger_id} is now 'AVAILABLE'")
            print(f"   -> Restored +{power:.2f} kW to Station #{station_id}")
            print(f"   -> Request P{req_id} marked as 'COMPLETED'\n")
            completed_count += 1
        else:
            print(f"  [ERROR] Could not auto-complete Session #{sess_id}: {error}\n")

    print("=" * 65)
    print(f"[SUMMARY] Successfully simulated and released {completed_count} session(s)!")
    print("All chargers have been returned to 'AVAILABLE' state.")
    print("All completed processes have been cleared from the Waiting Queue.")
    print("=" * 65 + "\n")


def display_os_performance_metrics():
    requests = get_all_requests_for_metrics()
    if not requests:
        print("\n[INFO] No charging requests found to calculate metrics.\n")
        return

    earliest = requests[0]["arrival_time"]

    lines = [str(len(requests))]
    for r in requests:
        pid = r["request_id"]
        ev_id = r["ev_id"]
        model = str(r["ev_model"]).replace(" ", "_")
        at = round((r["arrival_time"] - earliest).total_seconds() / 3600.0, 2)
        power = float(r["requested_power"])
        bt = round(float(r["required_energy"]) / power, 2) if power > 0 else 0.0
        priority = round(float(r.get("soc_at_request", 50.0)), 1)
        lines.append(f"{pid} {ev_id} {model} {at:.2f} {bt:.2f} {priority:.1f}")

    cpp_input = "\n".join(lines) + "\n"

    exe_path = ensure_executable("performance_metrics.cpp", "performance_metrics.exe")
    if not os.path.exists(exe_path):
        print(f"[ERROR] Could not find or compile {exe_path}.\n")
        return

    result = subprocess.run([exe_path], input=cpp_input, text=True, capture_output=True)
    print(result.stdout)


def run_step7_menu():
    """Step 7 Main Menu: Charging Sessions and OS Performance Metrics."""
    while True:
        print("\n" + "=" * 65)
        print("  STEP 7: CHARGING SESSIONS & OS PERFORMANCE METRICS (DBOS)")
        print("=" * 65)
        print("  [1] View All Charging Sessions")
        print("  [2] Start Charging Session (Manual)")
        print("  [3] Complete Charging Session & Release Resources (Manual)")
        print("  [4] Auto-Simulate & Release All Charging Sessions (Hands-Free)")
        print("  [5] Display OS Performance Metrics (AT, BT, CT, TAT, WT)")
        print("  [6] Back to Main Menu")
        print("=" * 65)

        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            display_charging_sessions()
        elif choice == "2":
            start_new_session_interactive()
        elif choice == "3":
            complete_session_interactive()
        elif choice == "4":
            auto_simulate_and_release_all()
        elif choice == "5":
            display_os_performance_metrics()
        elif choice == "6":
            break
        else:
            print("\n[INVALID CHOICE] Please enter a number from 1 to 6.\n")


if __name__ == "__main__":
    run_step7_menu()
