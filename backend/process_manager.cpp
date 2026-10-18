#include <iostream>
using namespace std;

struct Process {
    int pid, ev_id;
    char model[50];
    double at, energy, power, bt;
    char state[20];
};

int main() {
    int n;
    if (!(cin >> n) || n <= 0) {
        cout << "\nNo waiting charging requests found in the database queue.\n\n";
        return 0;
    }

    Process p[100];
    
    for (int i = 0; i < n; i++) {
        cin >> p[i].pid >> p[i].ev_id >> p[i].model >> p[i].at >> p[i].energy >> p[i].power >> p[i].state;
        if (p[i].power > 0)
            p[i].bt = p[i].energy / p[i].power;
        else
            p[i].bt = 0;
    }

    cout << "\nProcess ID\tEV ID\tEV Model\tAT\tEnergy\tPower\tBurst Time\tState\n";
    cout << "------------------------------------------------------------------------------------------------\n";
    for (int i = 0; i < n; i++) {
        cout << "P" << p[i].pid << "\t\t" << p[i].ev_id << "\t" << p[i].model << "\t"
             << p[i].at << "\t" << p[i].energy << "\t" << p[i].power << "\t"
             << p[i].bt << "\t\t" << p[i].state << "\n";
    }
    cout << "------------------------------------------------------------------------------------------------\n";
    cout << "Total Waiting Processes: " << n << "\n\n";

    return 0;
}

