#include <iostream>
#include <string>

using namespace std;

int main() {
    string command;
    
    if (!(cin >> command)) {
        cout << "[C++ Session Engine] No command provided.\n";
        return 0;
    }

    if (command == "START") {
        int allocation_id, request_id, charger_id;
        string model;
        double power;

        cin >> allocation_id >> request_id >> charger_id >> model >> power;

        cout << "\n============================================================\n";
        cout << "       OS PROCESS DISPATCH: START CHARGING SESSION\n";
        cout << "============================================================\n";
        cout << "  State Transition : [ALLOCATED] -> [RUNNING]\n";
        cout << "  Process ID       : P" << request_id << " (" << model << ")\n";
        cout << "  Allocation ID    : #" << allocation_id << "\n";
        cout << "  Assigned Charger : #" << charger_id << " (" << power << " kW)\n";
        cout << "  Session Status   : 'IN_PROGRESS'\n";
        cout << "============================================================\n\n";
        
        cout << "VALID_START\n";
    }
    else if (command == "COMPLETE") {
        int session_id, allocation_id, request_id, charger_id, station_id;
        string model;
        double energy_consumed, power;

        cin >> session_id >> allocation_id >> request_id >> charger_id >> station_id >> model >> energy_consumed >> power;

        double duration_hours = (power > 0) ? (energy_consumed / power) : 0.0;
        double duration_mins = duration_hours * 60.0;

        cout << "\n============================================================\n";
        cout << "     OS PROCESS TERMINATION: COMPLETE CHARGING SESSION\n";
        cout << "============================================================\n";
        cout << "  State Transition : [RUNNING] -> [COMPLETED]\n";
        cout << "  Session ID       : #" << session_id << "\n";
        cout << "  Process ID       : P" << request_id << " (" << model << ")\n";
        cout << "  Energy Consumed  : " << energy_consumed << " kWh\n";
        cout << "  Session Duration : " << duration_hours << " hrs (" << duration_mins << " mins)\n";
        cout << "\n  OS Resource Deallocation:\n";
        cout << "   - Resource Allocation #" << allocation_id << " -> 'RELEASED'\n";
        cout << "   - Charger Port #" << charger_id << "        -> 'AVAILABLE' (Returned to pool)\n";
        cout << "   - Station #" << station_id << " Capacity     -> Restored +" << power << " kW\n";
        cout << "============================================================\n\n";

        cout << "VALID_COMPLETE\n";
    }
    else {
        cout << "[ERROR] Unknown command: " << command << "\n";
    }

    return 0;
}
