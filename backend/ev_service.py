"""
EV Service Module
Handles registration and retrieval of electric vehicles from the EV table.
Maintains a predefined catalogue of EV models with their battery capacities.
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from db import execute_select, execute_modify
from user_service import create_user_interactive

EV_CATALOGUE = [
    {"model": "Tata Nexon EV",      "battery_capacity": 40.50},
    {"model": "MG ZS EV",           "battery_capacity": 50.30},
    {"model": "Hyundai IONIQ 5",    "battery_capacity": 72.60},
    {"model": "Tesla Model 3",      "battery_capacity": 60.00},
    {"model": "BMW i4",             "battery_capacity": 83.90},
    {"model": "Mahindra XUV400",    "battery_capacity": 34.50},
    {"model": "BYD Atto 3",         "battery_capacity": 60.48},
    {"model": "Kia EV6",            "battery_capacity": 77.40},
]


def display_ev_catalogue():
    """
    Displays the numbered list of available EV models from the catalogue.
    """
    print("\n--- Available EV Models Catalogue ---")
    for idx, item in enumerate(EV_CATALOGUE, 1):
        print(f"  [{idx}] {item['model']:<20} (Battery: {item['battery_capacity']:.2f} kWh)")


def get_all_evs():
    """
    Fetches all registered EVs along with their owner username and location name.
    """
    query = """
        SELECT 
            e.ev_id, 
            e.user_id, 
            u.username, 
            e.model, 
            e.battery_capacity, 
            e.current_soc, 
            l.location_name
        FROM EV e
        JOIN APP_USER u ON e.user_id = u.user_id
        JOIN LOCATION l ON e.current_location_id = l.location_id
        ORDER BY e.ev_id ASC;
    """
    return execute_select(query)


def display_evs():
    """
    Prints all registered EVs in a clean table format.
    """
    evs = get_all_evs()
    print("\n" + "=" * 90)
    print(f"{'EV ID':<7} | {'Owner':<15} | {'Model':<25} | {'Battery(kWh)':<13} | {'SoC(%)':<8} | {'Location':<20}")
    print("=" * 90)
    if not evs:
        print("No electric vehicles found in the database.")
    else:
        for ev in evs:
            print(
                f"{ev['ev_id']:<7} | "
                f"{ev['username']:<15} | "
                f"{ev['model']:<25} | "
                f"{float(ev['battery_capacity']):<13.2f} | "
                f"{float(ev['current_soc']):<8.1f} | "
                f"{ev['location_name']:<20}"
            )
    print("=" * 90 + "\n")


def get_locations():
    """
    Fetches all available predefined locations from the LOCATION table.
    """
    query = "SELECT location_id, location_name FROM LOCATION ORDER BY location_id ASC;"
    return execute_select(query)


def register_ev(user_id, model, battery_capacity, current_soc, location_id):
    """
    Inserts a new EV record into the EV table using parameterized SQL.
    Returns True on success, False on failure.
    """
    query = """
        INSERT INTO EV (user_id, model, battery_capacity, current_soc, current_location_id)
        VALUES (%s, %s, %s, %s, %s);
    """
    try:
        execute_modify(query, (user_id, model, battery_capacity, current_soc, location_id))
        return True
    except Exception as e:
        print(f"[ERROR] Could not register EV: {e}")
        return False


def create_ev_interactive():
    """
    Interactive EV registration flow:
    1. Enter user details (username, email, phone) and save in APP_USER.
    2. Show numbered list of EV models from catalogue.
    3. User selects EV model (retrieves battery capacity).
    4. Ask for EV's current battery percentage (SoC).
    5. Fetch available locations and let user select current location.
    6. Save EV linked to the newly registered user_id.
    """
    print("\n=======================================================")
    print("               NEW USER & EV REGISTRATION")
    print("=======================================================")

    user_id = create_user_interactive()
    if not user_id:
        print("[CANCELLED] Cannot proceed with EV registration without a valid user.")
        return

    display_ev_catalogue()
    try:
        model_choice = int(input(f"\nSelect EV Model [1-{len(EV_CATALOGUE)}]: ").strip())
        if not (1 <= model_choice <= len(EV_CATALOGUE)):
            print("[ERROR] Invalid catalogue selection. Registration cancelled.")
            return
        selected_item = EV_CATALOGUE[model_choice - 1]
        selected_model = selected_item["model"]
        battery_capacity = selected_item["battery_capacity"]
        print(f"-> Selected Model: {selected_model} (Battery Capacity: {battery_capacity:.2f} kWh)")
    except ValueError:
        print("[ERROR] Please enter a valid number for model selection.")
        return

    try:
        soc_input = input("Enter EV Current Battery Percentage / SoC % (0 - 100): ").strip()
        current_soc = float(soc_input)
        if not (0.0 <= current_soc <= 100.0):
            print("[ERROR] SoC must be between 0 and 100.")
            return
    except ValueError:
        print("[ERROR] SoC must be a valid number.")
        return

    locations = get_locations()
    if not locations:
        print("[ERROR] No locations available in LOCATION table.")
        return

    print("\nAvailable Locations:")
    for idx, loc in enumerate(locations, 1):
        print(f"  [{idx}] {loc['location_name']}")

    try:
        loc_choice = int(input(f"Select Current Location [1-{len(locations)}]: ").strip())
        if not (1 <= loc_choice <= len(locations)):
            print("[ERROR] Invalid location selection.")
            return
        selected_location = locations[loc_choice - 1]
        location_id = selected_location["location_id"]
        print(f"-> Selected Location: {selected_location['location_name']}")
    except ValueError:
        print("[ERROR] Please enter a valid number for location selection.")
        return

    success = register_ev(user_id, selected_model, battery_capacity, current_soc, location_id)
    if success:
        print(f"\n[SUCCESS] EV '{selected_model}' registered successfully for User ID {user_id}!")
        print(f"          Battery: {battery_capacity:.2f} kWh | Current SoC: {current_soc:.1f}% | Location: {selected_location['location_name']}")
    else:
        print("[FAILED] Vehicle registration failed.")

