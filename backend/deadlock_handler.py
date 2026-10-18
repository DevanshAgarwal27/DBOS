"""
Step 6: Synchronization and Deadlock Prevention Module
Connects the C++ Synchronization Engine (synchronization.exe) and
Deadlock Prevention Engine (deadlock_handler.exe) with the MySQL database.
"""

import os
import sys
import subprocess

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from db import get_resource_allocation_inputs, commit_resource_allocations_atomic


def run_synchronization_demo():
    print("\n" + "=" * 65)
    print("      PART 1: MULTI-THREADED OS MUTEX SYNCHRONIZATION")
    print("=" * 65)

    exe_path = os.path.join(backend_dir, "synchronization.exe")
    if not os.path.exists(exe_path):
        print(f"[ERROR] Executable not found at {exe_path}. Please compile synchronization.cpp first.\n")
        return

    result = subprocess.run([exe_path], text=True, capture_output=True)
    print(result.stdout)


def run_deadlock_prevention():
    print("\n" + "=" * 65)
    print("      PART 2: OS DEADLOCK PREVENTION ALLOCATOR")
    print("=" * 65)

    requests, stations, chargers = get_resource_allocation_inputs()

    if not requests:
        print("\n[INFO] No WAITING charging requests found in the database.")
        print("       All requests have either been allocated or none exist.\n")
        return

    print(f"-> Found {len(requests)} waiting request(s), {len(stations)} active station(s), {len(chargers)} available charger(s).\n")

    lines = []
    lines.append(str(len(requests)))
    for r in requests:
        model = str(r["ev_model"]).replace(" ", "_")
        lines.append(f"{r['request_id']} {r['ev_id']} {model} {r['requested_power']} {r['required_energy']} {r['soc_at_request']} {r['location_id']}")

    lines.append(str(len(stations)))
    for s in stations:
        name = str(s["station_name"]).replace(" ", "_")
        lines.append(f"{s['station_id']} {name} {s['location_id']} {s['total_power']} {s['used_power']} {s['status']}")

    lines.append(str(len(chargers)))
    for c in chargers:
        ctype = str(c["connector_type"]).replace(" ", "_")
        lines.append(f"{c['charger_id']} {c['station_id']} {ctype} {c['power_capacity']} {c['status']}")

    input_text = "\n".join(lines) + "\n"

    exe_path = os.path.join(backend_dir, "deadlock_handler.exe")
    if not os.path.exists(exe_path):
        print(f"[ERROR] Executable not found at {exe_path}. Please compile deadlock_handler.cpp first.\n")
        return

    result = subprocess.run([exe_path], input=input_text, text=True, capture_output=True)
    full_output = result.stdout

    for line in full_output.splitlines():
        if line.startswith("--- ALLOCATION PROPOSALS ---") or line.startswith("--- END PROPOSALS ---") or line.startswith("PROPOSAL "):
            continue
        print(line)

    proposals = []
    rejections = []
    for line in full_output.splitlines():
        if line.startswith("PROPOSAL "):
            parts = line.split()
            proposals.append({
                "request_id": int(parts[1]),
                "charger_id": int(parts[2]),
                "station_id": int(parts[3]),
                "allocated_power": float(parts[4])
            })
        elif line.startswith("REJECT "):
            parts = line.split()
            rejections.append({
                "request_id": int(parts[1]),
                "requested_power": float(parts[2])
            })

    if not proposals and not rejections:
        print("[NOTICE] No requests could acquire all required resources safely.")
        print("         Held resources = 0. Hold-and-Wait condition prevented.\n")
        return

    print("-" * 65)
    print(f"Applying {len(proposals)} allocation(s) and {len(rejections)} rejection(s) atomically to MySQL...")
    print("-" * 65)

    saved_count, rejected_count, error = commit_resource_allocations_atomic(proposals, rejections)

    if error is None:
        if saved_count > 0:
            print(f"\n[SUCCESS] Successfully committed {saved_count} allocation(s) atomically in MySQL!")
            print("  - Saved records in RESOURCE_ALLOCATION table")
            print("  - Updated CHARGER status to 'OCCUPIED'")
            print("  - Changed request process state from 'WAITING' to 'RUNNING'")
            print("  - Recorded 'ALLOCATION_SUCCESS' events in SYSTEM_LOG")
        if rejected_count > 0:
            print(f"\n[REJECTED] Successfully processed {rejected_count} impossible request(s) in MySQL!")
            print("  - Changed request process state from 'WAITING' to 'REJECTED'")
            print("  - Removed impossible requests from the Waiting Queue")
            print("  - Recorded 'TRANSACTION_ROLLBACK' events in SYSTEM_LOG\n")
    else:
        print(f"\n[FAILED] Transaction rolled back due to error: {error}\n")


def run_step6_synchronization_and_deadlock():
    """
    Main Entry Point for Step 6 menu:
    Allows user to run the Mutex Synchronization Demo, Deadlock Prevention Engine, or both.
    """
    print("\n" + "=" * 65)
    print("   STEP 6: SYNCHRONIZATION AND DEADLOCK PREVENTION (DBOS)")
    print("=" * 65)
    print("  [1] Run Multi-Threaded Mutex Synchronization (C++ Demo)")
    print("  [2] Run Deadlock Prevention Allocation (Live Database)")
    print("  [3] Run Complete Step 6 Demonstration (Both)")
    print("  [4] Back to Main Menu")
    print("=" * 65)

    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        run_synchronization_demo()
    elif choice == "2":
        run_deadlock_prevention()
    elif choice == "3":
        run_synchronization_demo()
        run_deadlock_prevention()
    elif choice == "4":
        return
    else:
        print("\n[INVALID CHOICE] Returning to main menu.\n")


if __name__ == "__main__":
    run_step6_synchronization_and_deadlock()

