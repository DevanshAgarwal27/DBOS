#include <iostream>
#include <string>
#include <iomanip>

using namespace std;

struct Process {
    int pid;
    int ev_id;
    string model;
    double at;
    double bt;
    double priority;
    double ct;
    double tat;
    double wt;
    bool done;
};

void print_table(string title, Process p[], int n, int order[], double avg_wt, double avg_tat, bool show_prio) {
    cout << "\n----------------------------------------------------------------------------------------------------\n";
    cout << title << "\n";
    cout << "----------------------------------------------------------------------------------------------------\n";
    
    cout << left << setw(7) << "PID" 
         << setw(8) << "EV ID" 
         << setw(20) << "EV Model";
    if (show_prio) {
        cout << right << setw(12) << "SoC (Prio)";
    }
    cout << right << setw(10) << "AT(hrs)" 
         << setw(10) << "BT(hrs)" 
         << setw(10) << "CT(hrs)" 
         << setw(10) << "TAT(hrs)" 
         << setw(10) << "WT(hrs)" << "\n";
    cout << string(show_prio ? 97 : 85, '-') << "\n";

    for (int i = 0; i < n; i++) {
        int k = order[i];
        cout << left << "P" << setw(6) << p[k].pid
             << setw(8) << p[k].ev_id
             << setw(20) << p[k].model.substr(0, 19);
        if (show_prio) {
            cout << right << setw(10) << p[k].priority << "% ";
        }
        cout << right << setw(10) << p[k].at
             << setw(10) << p[k].bt
             << setw(10) << p[k].ct
             << setw(10) << p[k].tat
             << setw(10) << p[k].wt << "\n";
    }
    cout << string(show_prio ? 97 : 85, '-') << "\n";

    cout << "Execution Order        : ";
    for (int i = 0; i < n; i++) {
        cout << "P" << p[order[i]].pid << (i + 1 < n ? " -> " : "");
    }
    cout << "\nAverage Waiting Time    (WT)  : " << avg_wt << " hours\n";
    cout << "Average Turnaround Time (TAT) : " << avg_tat << " hours\n";
}

void run_fcfs(Process p_in[], int n, double &avg_wt, double &avg_tat) {
    Process p[50];
    int order[50];
    for (int i = 0; i < n; i++) {
        p[i] = p_in[i];
        order[i] = i;
    }

    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (p[j].at > p[j + 1].at) {
                Process temp = p[j]; p[j] = p[j + 1]; p[j + 1] = temp;
            }
        }
    }

    double current_time = 0.0, total_wt = 0.0, total_tat = 0.0;
    for (int i = 0; i < n; i++) {
        if (current_time < p[i].at) current_time = p[i].at;
        current_time += p[i].bt;
        p[i].ct = current_time;
        p[i].tat = p[i].ct - p[i].at;
        p[i].wt = p[i].tat - p[i].bt;
        total_tat += p[i].tat;
        total_wt += p[i].wt;
        order[i] = i;
    }

    avg_wt = total_wt / n;
    avg_tat = total_tat / n;
    print_table("1. FIRST COME, FIRST SERVED (FCFS) SCHEDULING", p, n, order, avg_wt, avg_tat, false);
}

void run_sjf(Process p_in[], int n, double &avg_wt, double &avg_tat) {
    Process p[50];
    int order[50];
    for (int i = 0; i < n; i++) {
        p[i] = p_in[i];
        p[i].done = false;
    }

    double current_time = 0.0, total_wt = 0.0, total_tat = 0.0;
    int completed = 0;

    while (completed < n) {
        int best = -1;
        for (int i = 0; i < n; i++) {
            if (!p[i].done && p[i].at <= current_time) {
                if (best == -1 || p[i].bt < p[best].bt) best = i;
            }
        }

        if (best == -1) {
            current_time += 0.1;
            continue;
        }

        current_time += p[best].bt;
        p[best].ct = current_time;
        p[best].tat = p[best].ct - p[best].at;
        p[best].wt = p[best].tat - p[best].bt;
        p[best].done = true;

        total_tat += p[best].tat;
        total_wt += p[best].wt;
        order[completed++] = best;
    }

    avg_wt = total_wt / n;
    avg_tat = total_tat / n;
    print_table("2. NON-PREEMPTIVE SHORTEST JOB FIRST (SJF) SCHEDULING", p, n, order, avg_wt, avg_tat, false);
}

void run_priority(Process p_in[], int n, double &avg_wt, double &avg_tat) {
    Process p[50];
    int order[50];
    for (int i = 0; i < n; i++) {
        p[i] = p_in[i];
        p[i].done = false;
    }

    double current_time = 0.0, total_wt = 0.0, total_tat = 0.0;
    int completed = 0;

    while (completed < n) {
        int best = -1;
        for (int i = 0; i < n; i++) {
            if (!p[i].done && p[i].at <= current_time) {
                if (best == -1 || p[i].priority < p[best].priority) best = i;
            }
        }

        if (best == -1) {
            current_time += 0.1;
            continue;
        }

        current_time += p[best].bt;
        p[best].ct = current_time;
        p[best].tat = p[best].ct - p[best].at;
        p[best].wt = p[best].tat - p[best].bt;
        p[best].done = true;

        total_tat += p[best].tat;
        total_wt += p[best].wt;
        order[completed++] = best;
    }

    avg_wt = total_wt / n;
    avg_tat = total_tat / n;
    print_table("3. NON-PREEMPTIVE PRIORITY SCHEDULING (Lower SoC = Higher Priority)", p, n, order, avg_wt, avg_tat, true);
}

int main() {
    int n;
    if (!(cin >> n) || n <= 0) {
        cout << "\nNo requests available for performance metrics calculation.\n";
        return 0;
    }

    Process p[50];
    for (int i = 0; i < n; i++) {
        cin >> p[i].pid >> p[i].ev_id >> p[i].model >> p[i].at >> p[i].bt >> p[i].priority;
    }

    cout << fixed << setprecision(2);
    cout << "\n====================================================================================================\n";
    cout << "                 DBOS OPERATING SYSTEM PERFORMANCE METRICS REPORT\n";
    cout << "====================================================================================================\n";
    cout << "  Total Processes Evaluated : " << n << "\n";
    cout << "  Time Units                : Hours (AT, BT, CT, TAT, WT)\n";
    cout << "  Formulas Used             : TAT = CT - AT  |  WT = TAT - BT\n";

    double fcfs_wt, fcfs_tat;
    double sjf_wt, sjf_tat;
    double prio_wt, prio_tat;

    run_fcfs(p, n, fcfs_wt, fcfs_tat);
    run_sjf(p, n, sjf_wt, sjf_tat);
    run_priority(p, n, prio_wt, prio_tat);

    cout << "\n====================================================================================================\n";
    cout << "                      COMPARATIVE OS ALGORITHM EVALUATION SUMMARY\n";
    cout << "====================================================================================================\n";
    cout << left << setw(38) << "Algorithm" 
         << right << setw(28) << "Average Waiting Time (WT)" 
         << setw(32) << "Average Turnaround Time (TAT)\n";
    cout << string(98, '-') << "\n";
    cout << left << setw(38) << "First Come, First Served (FCFS)" 
         << right << setw(22) << fcfs_wt << " hrs" 
         << setw(28) << fcfs_tat << " hrs\n";
    cout << left << setw(38) << "Shortest Job First (SJF)" 
         << right << setw(22) << sjf_wt << " hrs" 
         << setw(28) << sjf_tat << " hrs\n";
    cout << left << setw(38) << "Priority Scheduling (by SoC %)" 
         << right << setw(22) << prio_wt << " hrs" 
         << setw(28) << prio_tat << " hrs\n";
    cout << string(98, '=') << "\n\n";

    return 0;
}
