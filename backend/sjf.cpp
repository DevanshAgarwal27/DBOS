#include <iostream>
using namespace std;

struct Process {
    int pid, ev_id;
    char model[50];
    double at, bt, ct, tat, wt;
    bool done;
};

int main() {
    int n;
    if (!(cin >> n) || n <= 0) {
        cout << "\nNo waiting charging requests found in the database queue.\n\n";
        return 0;
    }

    Process p[100];
    for (int i = 0; i < n; i++) {
        p[i].done = false;
        double dummy;
        cin >> p[i].pid >> p[i].ev_id >> p[i].model >> p[i].at >> p[i].bt >> dummy;
    }

    double time = 0;
    int completed = 0;
    int order[100];
    double total_tat = 0, total_wt = 0;

    while (completed < n) {
        int idx = -1;

        for (int i = 0; i < n; i++) {
            if (!p[i].done && p[i].at <= time) {
                if (idx == -1 || p[i].bt < p[idx].bt ||
                   (p[i].bt == p[idx].bt && p[i].at < p[idx].at))
                    idx = i;
            }
        }

        if (idx == -1) {
            double next_at = 1e9;
            for (int i = 0; i < n; i++) {
                if (!p[i].done && p[i].at < next_at)
                    next_at = p[i].at;
            }
            if (next_at > time && next_at < 1e9)
                time = next_at;
            else
                time += 0.1;
            continue;
        }

        time += p[idx].bt;
        p[idx].ct  = time;
        p[idx].tat = p[idx].ct - p[idx].at;
        p[idx].wt  = p[idx].tat - p[idx].bt;
        p[idx].done = true;
        order[completed] = idx;
        completed++;

        total_tat += p[idx].tat;
        total_wt  += p[idx].wt;
    }

    cout << "\nProcess ID\tEV ID\tEV Model\tAT\tBT\tCT\tTAT\tWT\n";
    cout << "--------------------------------------------------------------------------------\n";
    for (int i = 0; i < n; i++) {
        int k = order[i];
        cout << "P" << p[k].pid << "\t\t" << p[k].ev_id << "\t" << p[k].model << "\t"
             << p[k].at << "\t" << p[k].bt << "\t"
             << p[k].ct << "\t" << p[k].tat << "\t" << p[k].wt << "\n";
    }
    cout << "--------------------------------------------------------------------------------\n";

    cout << "\nSelected Algorithm    : Non-Preemptive Shortest Job First (SJF)\n";
    cout << "Actual Execution Order: ";
    for (int i = 0; i < n; i++) {
        cout << "P" << p[order[i]].pid << (i + 1 < n ? " -> " : "");
    }
    cout << "\nAverage Turnaround Time (TAT): " << (total_tat / n) << " hours\n";
    cout << "Average Waiting Time    (WT) : " << (total_wt / n) << " hours\n\n";

    return 0;
}
