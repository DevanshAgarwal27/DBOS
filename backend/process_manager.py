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
from datetime import datetime, timedelta
from db import get_waiting_requests

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
GRACE_PERIOD_MINUTES = 15
AGING_THRESHOLD_MINUTES = 10.0
AGING_RATE_PER_MINUTE = 5.0


def compute_effective_priority(request, now=None):
    """
    Computes the Two-Tier OS Priority Score with Anti-Starvation Aging.
    Lower score = Higher scheduling priority:
      - Tier 1 (< 100): Active pre-booked reservations & Critical Emergencies (SoC <= 20%)
      - Tier 2 (>= 100): Standard Walk-in requests OR Expired Reservations
    Aging prevents starvation for waiting Tier-2/long-burst requests by reducing
    their priority score after AGING_THRESHOLD_MINUTES and promoting them to Tier 1.
    Returns (effective_score, tier, tier_reason, aging_bonus).
    """
    soc = float(request.get("soc_at_request", 50.0))
    is_res = bool(request.get("is_reserved", False))
    res_active = is_reservation_active(request) if is_res else False

    if is_res and res_active:
        base_pr = round(soc * 0.5, 1)
        tier = 1
        tier_reason = "Active Pre-booked Reservation (Grace Period Valid)"
    elif soc <= 20.0:
        base_pr = round(soc, 1)
        tier = 1
        tier_reason = "Critical Battery Emergency (SoC <= 20%)"
    else:
        base_pr = round(100.0 + soc, 1)
        tier = 2
        tier_reason = "Standard Walk-in / Expired Reservation"

    aging_bonus = 0.0
    arrival_time = request.get("arrival_time")
    if arrival_time:
        if isinstance(arrival_time, str):
            try:
                arrival_time = datetime.strptime(arrival_time[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                arrival_time = None
        if arrival_time:
            ref_now = now or datetime.now()
            wait_mins = max(0.0, (ref_now - arrival_time).total_seconds() / 60.0)
            if wait_mins > AGING_THRESHOLD_MINUTES:
                aging_bonus = round((wait_mins - AGING_THRESHOLD_MINUTES) * AGING_RATE_PER_MINUTE, 1)

    effective_pr = max(1.0, round(base_pr - aging_bonus, 1)) if aging_bonus > 0 else base_pr
    if aging_bonus > 0:
        if tier == 2 and effective_pr < 100.0:
            tier = 1
            tier_reason += f" -> Promoted by Anti-Starvation Aging (-{aging_bonus:.1f} pts)"
        else:
            tier_reason += f" (Aging Boost: -{aging_bonus:.1f} pts)"

    return effective_pr, tier, tier_reason, aging_bonus


def is_reservation_active(request):
    """
    Checks if a pre-booked reservation is still valid or has expired.
    A reservation is valid if:
      - is_reserved is True
      - AND current time <= reserved_slot_time + GRACE_PERIOD_MINUTES (15 mins).
    If reserved_slot_time is NULL, assumes immediate valid reservation.
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

    expiry_time = slot_time + timedelta(minutes=GRACE_PERIOD_MINUTES)
    return datetime.now() <= expiry_time


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
    now = datetime.now()
    lines = [str(len(requests))]
    for r in requests:
        pid = r["request_id"]
        ev_id = r["ev_id"]
        model = str(r["ev_model"]).replace(" ", "_")
        at = round((r["arrival_time"] - earliest).total_seconds() / 3600.0, 2)
        power = float(r["requested_power"])
        bt = round(float(r["required_energy"]) / power, 2) if power > 0 else 0.0

        pr, _, _, _ = compute_effective_priority(r, now=now)
        lines.append(f"{pid} {ev_id} {model} {at:.2f} {bt:.2f} {pr:.1f}")

    return "\n".join(lines) + "\n"


def select_scheduling_strategy(requests):
    """
    Determines the adaptive OS scheduling algorithm for the current waiting queue.
    Prevents starvation by checking Anti-Starvation Aging promotions alongside
    active reservations and critical battery emergencies.
    Returns (selected_exe, algo_name, reason).
    """
    now = datetime.now()
    active_reserved = [r for r in requests if is_reservation_active(r)]
    expired_reserved = [r for r in requests if bool(r.get("is_reserved")) and not is_reservation_active(r)]
    critical = [r for r in requests if float(r.get("soc_at_request", 100)) <= 20]
    aged_promoted = [
        r for r in requests
        if compute_effective_priority(r, now=now)[3] > 0 and compute_effective_priority(r, now=now)[1] == 1
    ]

    if active_reserved or critical or aged_promoted:
        selected = "priority"
        algo_name = "Non-Preemptive Priority Scheduling"
        reasons = []
        if active_reserved:
            reasons.append(f"{len(active_reserved)} active pre-booked reservation(s) within grace period")
        if critical:
            reasons.append(f"{len(critical)} critical battery emergency(ies)")
        if aged_promoted:
            reasons.append(f"{len(aged_promoted)} aged waiting request(s) boosted to prevent starvation")
            algo_name = "Non-Preemptive Priority Scheduling (Anti-Starvation Aging)"
        reason = "Priority Mode: " + " & ".join(reasons) + " detected."
        if expired_reserved:
            reason += f" ({len(expired_reserved)} expired reservation(s) downgraded to walk-in)."
    elif len(requests) >= 3:
        selected = "sjf"
        algo_name = "Non-Preemptive Shortest Job First (SJF)"
        reason = f"High congestion ({len(requests)} EVs waiting). SJF minimizes waiting time."
    else:
        selected = "fcfs"
        algo_name = "First Come, First Served (FCFS)"
        reason = "Normal queue load. FCFS ensures fair FIFO service order."

    return selected, algo_name, reason


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
    Automatically decides whether to use Priority (with Aging), SJF, or FCFS.
    """
    requests = get_waiting_requests()
    if not requests:
        print("\nNo waiting charging requests found in the database queue.\n")
        return

    selected, algo_name, reason = select_scheduling_strategy(requests)

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
