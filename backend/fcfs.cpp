#include <iostream>
#include <algorithm>
using namespace std;

struct Process {
    int pid, ev_id;
    char model[50];
    double at, bt, ct, tat, wt;
};
bool compare(Process a, Process b) {
    if (a.at != b.at)
        return a.at < b.at;
    return a.pid < b.pid;
}

int main() {
    int n;
    if (!(cin >> n) || n <= 0) {
        cout << "\nNo waiting charging requests found in the database queue.\n\n";
        return 0;
    }

    Process p[100];
    for (int i = 0; i < n; i++) {
        double dummy;
        cin >> p[i].pid >> p[i].ev_id >> p[i].model >> p[i].at >> p[i].bt >> dummy;
    }

    sort(p, p + n, compare);

    double time = 0;
    double total_tat = 0, total_wt = 0;

    for (int i = 0; i < n; i++) {
        if (time < p[i].at)
            time = p[i].at;

        time += p[i].bt;
        p[i].ct  = time;
        p[i].tat = p[i].ct - p[i].at;
        p[i].wt  = p[i].tat - p[i].bt;

        total_tat += p[i].tat;
        total_wt  += p[i].wt;
    }

    cout << "\nProcess ID\tEV ID\tEV Model\tAT\tBT\tCT\tTAT\tWT\n";
    cout << "--------------------------------------------------------------------------------\n";
    for (int i = 0; i < n; i++) {
        cout << "P" << p[i].pid << "\t\t" << p[i].ev_id << "\t" << p[i].model << "\t"
             << p[i].at << "\t" << p[i].bt << "\t"
             << p[i].ct << "\t" << p[i].tat << "\t" << p[i].wt << "\n";
    }
    cout << "--------------------------------------------------------------------------------\n";

    cout << "\nSelected Algorithm    : First Come, First Served (FCFS)\n";
    cout << "Actual Execution Order: ";
    for (int i = 0; i < n; i++) {
        cout << "P" << p[i].pid << (i + 1 < n ? " -> " : "");
    }
    cout << "\nAverage Turnaround Time (TAT): " << (total_tat / n) << " hours\n";
    cout << "Average Waiting Time    (WT) : " << (total_wt / n) << " hours\n\n";

    return 0;
}
