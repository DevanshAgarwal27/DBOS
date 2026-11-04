"""
OS Process Management & Scheduling Interface Module
Connects MySQL database operations to the compiled C++ executables:
- process_manager.exe (View waiting queue)
- fcfs.exe (First Come, First Served)
- sjf.exe (Shortest Job First)
- priority.exe (Priority Scheduling)
"""

import os
import subprocess
from db import get_waiting_requests

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


def run_program(exe_name, input_data):
    """Runs a compiled C++ executable with input_data passed via stdin."""
    exe_path = os.path.join(BACKEND_DIR, f"{exe_name}.exe")
    if not os.path.exists(exe_path):
        print(f"\n[ERROR] Executable {exe_name}.exe not found. Please compile {exe_name}.cpp first.\n")
        return
    subprocess.run([exe_path], input=input_data, text=True)


def format_for_process_manager(requests):
    """Formats waiting requests for process_manager.cpp."""
    if not requests:
        return "0\n"

    earliest = requests[0]["arrival_time"]
    lines = [str(len(requests))]
    for r in requests:
        pid = r["request_id"]
        ev_id = r["ev_id"]
        model = str(r["ev_model"]).replace(" ", "_")
        at = round((r["arrival_time"] - earliest).total_seconds() / 3600.0, 2)
        energy = float(r["required_energy"])
        power = float(r["requested_power"])
        state = str(r.get("process_state", "WAITING"))
        lines.append(f"{pid} {ev_id} {model} {at:.2f} {energy:.2f} {power:.2f} {state}")

    return "\n".join(lines) + "\n"


def format_for_scheduler(requests):
    """Formats waiting requests for fcfs.cpp, sjf.cpp, and priority.cpp."""
    if not requests:
        return "0\n"

    earliest = requests[0]["arrival_time"]
    lines = [str(len(requests))]
    for r in requests:
        pid = r["request_id"]
        ev_id = r["ev_id"]
        model = str(r["ev_model"]).replace(" ", "_")
        at = round((r["arrival_time"] - earliest).total_seconds() / 3600.0, 2)
        power = float(r["requested_power"])
        bt = round(float(r["required_energy"]) / power, 2) if power > 0 else 0.0
        
        soc = float(r.get("soc_at_request", 50.0))
        is_reserved = bool(r.get("is_reserved", False))

        # OS Two-Tier Priority Score (Lower Score = Higher Priority):
        # Tier 1 (< 100): Pre-booked reservations & Critical Emergencies (SoC <= 20%)
        # Tier 2 (>= 100): Standard Walk-in requests
        if is_reserved:
            pr = round(soc * 0.5, 1)       # Pre-booked reservation priority boost (Score 0-50)
        elif soc <= 20.0:
            pr = round(soc, 1)             # Emergency low battery (Score 0-20)
        else:
            pr = round(100.0 + soc, 1)     # Standard walk-in (Score 120-200)

        lines.append(f"{pid} {ev_id} {model} {at:.2f} {bt:.2f} {pr:.1f}")

    return "\n".join(lines) + "\n"


def display_waiting_processes():
    """Option [6]: View Waiting Processes"""
    requests = get_waiting_requests()
    run_program("process_manager", format_for_process_manager(requests))


def run_fcfs_scheduling():
    """Option [8]: Run FCFS Scheduling"""
    requests = get_waiting_requests()
    run_program("fcfs", format_for_scheduler(requests))


def run_sjf_scheduling():
    """Option [9]: Run Non-Preemptive SJF Scheduling"""
    requests = get_waiting_requests()
    run_program("sjf", format_for_scheduler(requests))


def run_priority_scheduling():
    """Option [10]: Run Non-Preemptive Priority Scheduling"""
    requests = get_waiting_requests()
    run_program("priority", format_for_scheduler(requests))


def run_intelligent_auto_scheduler():
    """
    Option [7]: Intelligent Adaptive Scheduler.
    Automatically decides whether to use Priority, SJF, or FCFS:
      - Prior Reservations or Critical Battery (SoC <= 20%): Priority Scheduling
      - High congestion (>= 3 waiting): SJF
      - Normal load: FCFS
    """
    requests = get_waiting_requests()
    if not requests:
        print("\nNo waiting charging requests found in the database queue.\n")
        return

    reserved = [r for r in requests if bool(r.get("is_reserved", False))]
    critical = [r for r in requests if float(r.get("soc_at_request", 100)) <= 20]

    if reserved or critical:
        selected = "priority"
        algo_name = "Non-Preemptive Priority Scheduling"
        if reserved and critical:
            reason = f"Priority Override: {len(reserved)} pre-booked reservation(s) and {len(critical)} critical battery emergency(ies) in queue."
        elif reserved:
            reason = f"Reservation Priority: {len(reserved)} pre-booked charger slot(s) must be honored."
        else:
            reason = "Emergency Alert: One or more EVs have critical battery (SoC <= 20%)."
    elif len(requests) >= 3:
        selected = "sjf"
        algo_name = "Non-Preemptive Shortest Job First (SJF)"
        reason = f"High congestion ({len(requests)} EVs waiting). SJF minimizes waiting time."
    else:
        selected = "fcfs"
        algo_name = "First Come, First Served (FCFS)"
        reason = "Normal queue load. FCFS ensures fair FIFO service."

    print("\n" + "=" * 65)
    print("           INTELLIGENT ADAPTIVE SCHEDULER")
    print("=" * 65)
    print(f"  Waiting Requests       : {len(requests)}")
    print(f"  Auto-Selected Algorithm: {algo_name}")
    print(f"  Decision Reason        : {reason}")
    print("=" * 65 + "\n")

    run_program(selected, format_for_scheduler(requests))


if __name__ == "__main__":
    display_waiting_processes()
