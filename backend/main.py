"""
Main Application Module
Provides an interactive terminal menu for backend operations:
users, electric vehicles, charging requests, OS process management,
Intelligent Auto-Scheduler, resource allocation, synchronization,
and session management.
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from user_service import display_users
from ev_service import create_ev_interactive, display_evs
from request_service import create_request_interactive, display_requests
from process_manager import (
    display_waiting_processes,
    run_intelligent_auto_scheduler
)
from resource_allocator import run_resource_allocation
from deadlock_handler import run_step6_synchronization_and_deadlock
from session_manager import run_step7_menu, auto_simulate_and_release_all


def show_menu():
    print("=" * 65)
    print("      DBOS EV CHARGING QUEUE & RESOURCE MANAGEMENT SYSTEM")
    print("       Backend Operations Menu")
    print("=" * 65)


    print("  [1]  Register New User & Electric Vehicle (EV)")
    print("  [2]  View All Users")
    print("  [3]  View All Registered EVs")
    print("  [4]  Create New Charging Request (OS Process)")
    print("  [5]  View All Charging Requests")
    print("  [6]  View Waiting Processes (OS Process Management)")
    print("  [7]  Run Intelligent Auto-Scheduler (Automatic Selection)")
    print("  [8]  Run Resource Allocation")
    print("  [9]  Run Synchronization & Deadlock Prevention")
    print("  [10] Charging Sessions & OS Performance Metrics")
    print("  [11] Auto-Simulate & Release All Charging Sessions")
    print("  [12] Exit")

    
    print("=" * 65)


def main():
    while True:
        show_menu()
        choice = input("Enter your choice (1-12): ").strip()

        if choice == "1":
            create_ev_interactive()
        elif choice == "2":
            display_users()
        elif choice == "3":
            display_evs()
        elif choice == "4":
            create_request_interactive()
        elif choice == "5":
            display_requests()
        elif choice == "6":
            display_waiting_processes()
        elif choice == "7":
            run_intelligent_auto_scheduler()
        elif choice == "8":
            run_resource_allocation()
        elif choice == "9":
            run_step6_synchronization_and_deadlock()
        elif choice == "10":
            run_step7_menu()
        elif choice == "11":
            auto_simulate_and_release_all()
        elif choice == "12":
            print("\nThank you for using DBOS EV Charging System. Goodbye!\n")
            break
        else:
            print("\n[INVALID CHOICE] Please enter a valid number from 1 to 12.\n")

        input("Press Enter to continue...")
        print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting.")
        sys.exit(0)
