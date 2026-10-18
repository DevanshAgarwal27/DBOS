#include <iostream>
#include <string>

using namespace std;

struct Request {
    int request_id;
    int ev_id;
    string model;
    double requested_power;
    double required_energy;
    double soc;
    int location_id;
    int assigned_charger;
    int assigned_station;
    bool is_allocated;
    bool is_rejected;
};

struct Station {
    int station_id;
    string name;
    int location_id;
    double total_power;
    double used_power;
    double remaining_power;
    string status;
};

struct Charger {
    int charger_id;
    int station_id;
    string connector_type;
    double power_capacity;
    string status;
    bool is_allocated;
};

int main() {
    int num_requests;
    if (!(cin >> num_requests) || num_requests <= 0) {
        cout << "\nNo waiting charging requests found to allocate.\n\n";
        return 0;
    }

    Request requests[50];
    for (int i = 0; i < num_requests; i++) {
        cin >> requests[i].request_id
            >> requests[i].ev_id
            >> requests[i].model
            >> requests[i].requested_power
            >> requests[i].required_energy
            >> requests[i].soc
            >> requests[i].location_id;

        requests[i].is_allocated = false;
        requests[i].is_rejected = false;
        requests[i].assigned_charger = -1;
        requests[i].assigned_station = -1;
    }

    int num_stations;
    cin >> num_stations;

    Station stations[20];
    for (int i = 0; i < num_stations; i++) {
        cin >> stations[i].station_id
            >> stations[i].name
            >> stations[i].location_id
            >> stations[i].total_power
            >> stations[i].used_power
            >> stations[i].status;

        stations[i].remaining_power = stations[i].total_power - stations[i].used_power;
        if (stations[i].remaining_power < 0.0)
            stations[i].remaining_power = 0.0;
    }

    int num_chargers;
    cin >> num_chargers;

    Charger chargers[50];
    for (int i = 0; i < num_chargers; i++) {
        cin >> chargers[i].charger_id
            >> chargers[i].station_id
            >> chargers[i].connector_type
            >> chargers[i].power_capacity
            >> chargers[i].status;

        chargers[i].is_allocated = false;
    }

    cout << "\n========================================================================\n";
    cout << "            DBOS RESOURCE ALLOCATOR (C++ DISPATCH ENGINE)\n";
    cout << "========================================================================\n\n";

    cout << "--- ACTIVE STATIONS ---\n";
    for (int i = 0; i < num_stations; i++) {
        cout << "Station #" << stations[i].station_id << ": " << stations[i].name
             << " | Total: " << stations[i].total_power << " kW"
             << " | Used: " << stations[i].used_power << " kW"
             << " | Remaining: " << stations[i].remaining_power << " kW\n";
    }

    cout << "\n--- AVAILABLE CHARGERS ---\n";
    for (int i = 0; i < num_chargers; i++) {
        cout << "Charger #" << chargers[i].charger_id 
             << " (Station #" << chargers[i].station_id << ", "
             << chargers[i].connector_type << ", "
             << chargers[i].power_capacity << " kW)\n";
    }

    cout << "\n------------------------------------------------------------------------\n";
    cout << "                     ALLOCATION DECISION TRACE\n";
    cout << "------------------------------------------------------------------------\n";

    int allocated_count = 0;
    int rejected_count = 0;

    double max_system_charger_capacity = 0.0;
    for (int c = 0; c < num_chargers; c++) {
        if (chargers[c].power_capacity > max_system_charger_capacity)
            max_system_charger_capacity = chargers[c].power_capacity;
    }

    for (int i = 0; i < num_requests; i++) {
        if (requests[i].requested_power > max_system_charger_capacity) {
            requests[i].is_rejected = true;
            rejected_count++;
            cout << "[REJECTED] Request P" << requests[i].request_id 
                 << " (" << requests[i].model << ", " << requests[i].requested_power << " kW)\n";
            cout << "          -> Requested power exceeds maximum station hardware limit ("
                 << max_system_charger_capacity << " kW). Transaction rolled back.\n";
            cout << "          -> Process State transitioned to: 'REJECTED'\n\n";
            continue;
        }

        int best_charger_idx = -1;
        int best_station_idx = -1;

        for (int c = 0; c < num_chargers; c++) {
            if (chargers[c].is_allocated || chargers[c].status != "AVAILABLE")
                continue;

            int s_idx = -1;
            for (int s = 0; s < num_stations; s++) {
                if (stations[s].station_id == chargers[c].station_id) {
                    s_idx = s;
                    break;
                }
            }

            if (s_idx == -1 || stations[s_idx].status != "ACTIVE")
                continue;

            if (requests[i].requested_power > chargers[c].power_capacity)
                continue;

            if (requests[i].requested_power > stations[s_idx].remaining_power)
                continue;

            if (stations[s_idx].location_id == requests[i].location_id) {
                best_charger_idx = c;
                best_station_idx = s_idx;
                break;
            }

            if (best_charger_idx == -1) {
                best_charger_idx = c;
                best_station_idx = s_idx;
            }
        }

        if (best_charger_idx != -1 && best_station_idx != -1) {
            chargers[best_charger_idx].is_allocated = true;
            stations[best_station_idx].remaining_power -= requests[i].requested_power;
            stations[best_station_idx].used_power += requests[i].requested_power;

            requests[i].is_allocated = true;
            requests[i].assigned_charger = chargers[best_charger_idx].charger_id;
            requests[i].assigned_station = stations[best_station_idx].station_id;
            allocated_count++;

            cout << "[SUCCESS] Request P" << requests[i].request_id 
                 << " (" << requests[i].model << ", " << requests[i].requested_power << " kW)\n";
            cout << "          -> Assigned to Charger #" << chargers[best_charger_idx].charger_id
                 << " at Station #" << stations[best_station_idx].station_id << " (" << stations[best_station_idx].name << ")\n";
            cout << "          -> Station Remaining Power is now: " << stations[best_station_idx].remaining_power << " kW\n\n";
        } else {
            cout << "[WAITING] Request P" << requests[i].request_id 
                 << " (" << requests[i].model << ", " << requests[i].requested_power << " kW)\n";
            cout << "          -> Power/charger temporarily busy. Process remains in WAITING queue.\n\n";
        }
    }

    cout << "========================================================================\n";
    cout << "Summary: Allocated " << allocated_count << ", Rejected " << rejected_count 
         << ", Waiting " << (num_requests - allocated_count - rejected_count) 
         << " out of " << num_requests << " request(s).\n";
    cout << "========================================================================\n\n";

    cout << "--- ALLOCATION PROPOSALS ---\n";
    for (int i = 0; i < num_requests; i++) {
        if (requests[i].is_allocated) {
            cout << "PROPOSAL " 
                 << requests[i].request_id << " "
                 << requests[i].assigned_charger << " "
                 << requests[i].assigned_station << " "
                 << requests[i].requested_power << "\n";
        } else if (requests[i].is_rejected) {
            cout << "REJECT " 
                 << requests[i].request_id << " "
                 << requests[i].requested_power << "\n";
        }
    }
    cout << "--- END PROPOSALS ---\n";

    return 0;
}
