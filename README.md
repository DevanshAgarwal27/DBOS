# DBOS: EV Charging Queue & Resource Management System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![C++](https://img.shields.io/badge/C%2B%2B-17-00599C.svg)](https://isocpp.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-orange.svg)](https://www.mysql.com/)
[![Frontend](https://img.shields.io/badge/Frontend-HTML5%20%7C%20CSS3%20%7C%20ES6%20JS%20%7C%20SVG-yellow.svg)](#)
[![OS Concepts](https://img.shields.io/badge/OS-Process%20Scheduling%20%7C%20Deadlock%20Prevention%20%7C%20Mutex-success.svg)](#)

A hybrid **Database Operating System (DBOS)** that bridges Operating System principles (CPU scheduling, Process Control Blocks, concurrency synchronization, and deadlock prevention) with Database Management System guarantees (3NF relational modeling, ACID transactions, pessimistic row locking with `SELECT ... FOR UPDATE`, and audit logging) to resolve electric vehicle (EV) charging congestion, charger socket contention, and grid power limits.

---

## Architecture Overview

![DBOS System Architecture](dbos_system_architecture.jpg)

```mermaid
flowchart TD
    subgraph UI ["0. Web Control Plane & CLI"]
        WEB["Station Manager Web UI<br>(frontend/ -> server.py :8000)"]
        CLI["Interactive CLI<br>(backend/main.py)"]
    end

    subgraph Ingestion ["1. Entity & Process Ingestion"]
        U["User & EV Registration<br>(user_service, ev_service)"]
        R["Process Creation / Admission Control<br>(request_service)"]
        WEB --> U
        WEB --> R
        CLI --> U
        CLI --> R
        U --> R
    end

    subgraph OS_Scheduler ["2. OS Process Management & Scheduling"]
        Q["Ready Queue (PCB State: WAITING)<br>(process_manager)"]
        R --> Q
        Q --> S1["FCFS (fcfs.cpp)"]
        Q --> S2["SJF (sjf.cpp)"]
        Q --> S3["Priority Scheduling (priority.cpp)"]
        Q --> S4["Intelligent Auto-Scheduler"]
    end

    subgraph Dispatch ["3. Hardware Dispatch & Deadlock Prevention"]
        RA["Resource Allocator (resource_allocator.cpp)"]
        DP["Deadlock Prevention (deadlock_handler.cpp)"]
        SYNC["Mutex Synchronization (synchronization.cpp)"]
        S1 & S2 & S3 & S4 --> RA
        RA --> DP
        DP --> SYNC
    end

    subgraph Database ["4. Database Transaction Layer"]
        DB[("MySQL 3NF Database<br>(schema.sql)")]
        TX["ACID Transaction (db.py)<br>SELECT ... FOR UPDATE<br>Atomic Commit / Rollback"]
        SYNC --> TX
        TX <--> DB
    end

    subgraph Execution ["5. Execution & OS Metrics"]
        SM["Session Manager (session_manager.py)"]
        CS["State Transitions (charging_session.cpp)"]
        MET["OS Performance Metrics (performance_metrics.cpp)"]
        TX --> SM
        SM --> CS
        CS --> MET
    end
```

---

## Team Roles & Contributions

### 1. Devansh Agarwal (Team Lead)
* **DBOS System Architecture & Schema:** Designed the end-to-end architecture and normalized 9-table Third Normal Form (3NF) relational data model with primary/foreign key constraints and validation checks.
* **Process Control Block (PCB) & CPU Scheduling:** Modeled the OS Process structure, four-stage lifecycle (`WAITING`, `READY`, `RUNNING`, `COMPLETED`), and OS Burst Time estimation formula ($BT = \frac{\text{Required Energy}}{\text{Requested Power}}$). Implemented FCFS, Non-Preemptive SJF, and battery SoC-based Priority Scheduling in C++, alongside the adaptive auto-scheduler and metrics evaluation.
* **Web Control Plane, REST Bridge & System Dashboard (Phase 3 Lead):** Built the multi-threaded Python HTTP/REST server (`backend/server.py`), 3-tab Web Control Plane (`frontend/`), central API client (`api.js`) and app router (`app.js`), System Dashboard (`dashboard.js`) with PCB inspector, live animated battery gauge and SVG charging curve, Hardware Telemetry KPI widgets, Driver/EV registration UI & live fleet directory, and end-to-end integration.

### 2. Aarushi Malik
* **ACID Transaction Protocols:** Implemented strict transactional execution controls (`BEGIN`, `COMMIT`, `ROLLBACK`) across all database state transitions.
* **Pessimistic Concurrency Control:** Designed row-level pessimistic locking via `SELECT ... FOR UPDATE` on `CHARGING_REQUEST`, `CHARGER`, `STATION`, `RESOURCE_ALLOCATION`, and `CHARGING_SESSION` to prevent race conditions during concurrent allocations.
* **Contention & Deadlock Management:** Implemented atomic rollback handlers on hardware contention and transactional-layer Hold-and-Wait deadlock elimination.
* **Charging Request Admission & Master Requests UI (Phase 3):** Built the Charging Request Admission interface (`admission.js`), owner autocomplete, pure EV model selector, Current/Target SoC dual sliders with validation, 15-minute reservation grace period leases, and the filterable Master Charging Requests Directory.

### 3. Nitin Chauhan
* **Physical Resource Modeling:** Modeled physical constraints for charging stations (grid total power capacity, dynamic remaining power), discrete charging ports (connector types, kW capacity), and coordinate-based GPS location mapping.
* **Concurrency & Synchronization:** Implemented OS `std::mutex` locks to guard shared station power and Counting Semaphore mechanics for charger port sockets in C++.
* **Spatial Compatibility & Audit Logging:** Formulated hardware connector compatibility filtering (`CCS2`, `Type 2`), resource deadlock prevention (Linear Resource Ordering & All-or-Nothing policy), and structured event auditing in the `SYSTEM_LOG` table.

---

## Key Features & OS / DBMS Implementations

### 1. Process Control Block (PCB) & Process Lifecycle
Every incoming EV charging request is treated as an OS Process:
* **PID:** Unique `request_id`.
* **State Transition Lifecycle:**
  $$\text{WAITING} \longrightarrow \text{READY} \longrightarrow \text{RUNNING} \longrightarrow \text{COMPLETED}$$
  *(or $\text{REJECTED}$ if power exceeds maximum station hardware limits).*
* **Arrival Time ($AT$):** Timestamp when request entered the queue.
* **Burst Time ($BT$):** Estimated service duration calculated dynamically:
  $$\text{Burst Time (hours)} = \frac{\text{Required Energy (kWh)}}{\text{Charger Power (kW)}}$$

### 2. CPU Scheduling Algorithms & Anti-Starvation
* **First-Come, First-Served (FCFS):** Dispatches processes strictly by Arrival Time ($AT$).
* **Non-Preemptive Shortest Job First (SJF):** Dispatches the request with the smallest service duration ($BT$), minimizing system average waiting time.
* **Non-Preemptive Priority Scheduling (Two-Tier + Aging):**
  * **Tier 1 (High SLA, Score $< 100$):** Active pre-booked reservations within their 15-minute grace window ($\text{SoC} \times 0.5$) and critical emergencies ($\text{SoC} \le 20\%$, score $= \text{SoC}$).
  * **Tier 2 (Standard, Score $\ge 100$):** Walk-in vehicles and expired reservations ($100 + \text{SoC}$).
  * **Anti-Starvation Aging:** Processes waiting longer than 10 minutes earn `-5.0` priority points per extra minute waited and promote automatically to Tier 1 once their score drops below `100`, preventing indefinite starvation in both the C++ scheduler and hardware dispatcher (`resource_allocator.py`).
* **Intelligent Adaptive Auto-Scheduler (`select_scheduling_strategy`):** Evaluates queue telemetry in real time:
  * **Priority Mode:** Automatically triggered if any waiting EV has an active reservation, critical battery ($\text{SoC} \le 20\%$), or an Anti-Starvation Aging promotion.
  * **SJF Congestion Mode:** If waiting queue size $\ge 3$ vehicles without Tier-1 triggers.
  * **FCFS Normal Mode:** Under light load without emergencies or reservations.

### 3. Concurrency, Mutexes & Deadlock Prevention
* **Mutual Exclusion (`std::mutex`):** Protects critical sections to prevent race conditions where multiple requests attempt to claim the same charger or exceed station remaining power.
* **Elimination of Circular Wait:** Imposes a strict global linear resource ordering:
  $$\text{Station Power (Resource Class 1)} \prec \text{Charger Port (Resource Class 2)}$$
  Requests acquire station power before claiming the port, rendering graph cycles impossible.
* **Elimination of Hold and Wait:** Enforces an **All-or-Nothing** atomic allocation policy: if both the charger and sufficient station power are available, both are locked together; otherwise, zero resources are held and the process remains in `WAITING`.

### 4. ACID Transactions & Row-Level Locking
* Every hardware allocation executes inside an isolated transaction with `SELECT ... FOR UPDATE`.
* If a station or charger becomes occupied during verification, the transaction executes an immediate `ROLLBACK`, logs `TRANSACTION_ROLLBACK` in `SYSTEM_LOG`, and retains the process in `WAITING` without corrupting state.

### 5. Web Control Plane (Station Manager Dashboard)
A dark-themed 3-tab browser interface served via [`backend/server.py`](backend/server.py) on `http://localhost:8000` with strict `no-store` caching headers:
* **System Dashboard (`OS & Telemetry`):** Live KPI telemetry, Grid & Charger Socket load bar, PCB Ready Queue table (showing owner, burst time, SoC, Two-Tier SLA & Aging badges), step-by-step Battery Gauge & SVG charging trajectory curve ($SoC(t)$ scaled to exact requested target SoC), and C++ Auto-Scheduler / Charger Dispatch / Release controls.
* **User & EV Registration (`Workload Injection`):** Registers users (`APP_USER`) and EVs (`EV`) with verified catalogue capacities or custom entries, hub location mapping, live Fleet Directory (`IDLE`, `QUEUED`, `CHARGING`), and automatic pre-sync to the Admission tab.
* **Charging Request Admission (`Process Admission`):** Direct driver/owner name entry with autocomplete (strict per-user EV ownership resolution via `_resolve_or_create_user` and `_resolve_or_create_user_ev`), pure EV type + kWh selector, Arrival & Target SoC sliders, charger rating, 15-minute grace-period reservations, live Energy & Burst Time calculation, and filterable Master Requests Directory (`All`, `Waiting Queue`, `Completed History`).

### 6. OS Performance Metrics
Compares algorithms side-by-side using standard operating system turnaround and waiting metrics:
* **Turnaround Time ($TAT$):**
  $$TAT = CT - AT$$
* **Waiting Time ($WT$):**
  $$WT = TAT - BT$$
* Outputs Average Waiting Time and Average Turnaround Time across FCFS, SJF, and Priority.

---

## Relational Data Model (3NF)

The database schema (`dbos_ev`) is normalized to Third Normal Form (3NF) across 9 tables:

1. **`APP_USER`**: EV owners (User ID, username, email, phone).
2. **`LOCATION`**: Geographic coordinates (`latitude`, `longitude`, location name).
3. **`EV`**: Electric vehicles (Model, battery capacity, current SoC %, location FK).
4. **`STATION`**: Charging stations (Total grid power, location FK, status).
5. **`CHARGER`**: Ports/sockets (Connector type, power capacity, status, station FK).
6. **`CHARGING_REQUEST`**: OS Process records (Arrival time, energy, power, SoC, is_reserved flag, process state).
7. **`RESOURCE_ALLOCATION`**: Active hardware claims (Allocated power, timestamps, status).
8. **`CHARGING_SESSION`**: Real-time session execution (Energy consumed, duration, status).
9. **`SYSTEM_LOG`**: Immutable system audit trail (Event types: `PROCESS_CREATED`, `SCHEDULING`, `ALLOCATION_SUCCESS`, `CHARGING_STARTED`, `CHARGING_COMPLETED`, `RESOURCE_RELEASED`, `TRANSACTION_ROLLBACK`).

---

## Project Structure

```text
DBOS_EV PROJECT/
│
├── database/
│   ├── schema.sql                   # 9-table 3NF schema with foreign keys and checks
│   └── sample_data.sql              # Realistic seed data for stations, chargers, and EVs
│
├── backend/
│   ├── server.py                    # Multi-threaded HTTP API + static control-plane server (port 8000)
│   ├── config.py                    # MySQL connection parameters
│   ├── db.py                        # Database access layer, ACID transactions & SELECT ... FOR UPDATE locks
│   ├── test_connection.py           # Database connection & schema verification script
│   ├── main.py                      # Interactive terminal CLI menu (12 options)
│   │
│   ├── user_service.py              # User registration and query operations
│   ├── ev_service.py                # EV registration, verified catalogue & location mapping
│   ├── request_service.py           # Admission control, 15-min grace leases & burst time calc
│   │
│   ├── process_manager.py           # Scheduler bridge, Adaptive Scheduler & Anti-Starvation Aging
│   ├── process_manager.cpp          # C++ Ready Queue / PCB display engine
│   ├── fcfs.cpp                     # C++ First-Come, First-Served engine
│   ├── sjf.cpp                      # C++ Shortest Job First engine
│   ├── priority.cpp                 # C++ Two-Tier Priority Scheduling engine
│   │
│   ├── resource_allocator.py        # Strategy-aligned dispatch bridge & atomic commit handler
│   ├── resource_allocator.cpp       # C++ hardware feasibility check & power deduction
│   │
│   ├── deadlock_handler.py          # Python deadlock prevention bridge
│   ├── deadlock_handler.cpp         # C++ Deadlock Prevention engine (Resource Ordering)
│   ├── synchronization.cpp          # C++ Mutex & multi-threaded concurrency simulation
│   │
│   ├── session_manager.py           # Charging session lifecycle & auto-simulation engine
│   ├── charging_session.cpp         # C++ session state machine validator
│   └── performance_metrics.cpp      # C++ OS comparative metrics calculation (TAT, WT)
│
├── frontend/
│   ├── index.html                   # 3-tab DBOS Station Manager UI
│   ├── css/style.css                # Dark slate-blue engineering control-plane theme
│   └── js/
│       ├── api.js                   # Fetch wrapper for backend REST endpoints
│       ├── app.js                   # Navigation, KPI polling & toast notifications
│       ├── dashboard.js             # Tab 1: PCB Ready Queue, Battery Gauge/SVG Curve & C++ Scheduler
│       ├── registration.js          # Tab 2: User & EV Workload Injection & Live Fleet Directory
│       └── admission.js             # Tab 3: Owner Entry, EV Model Selector & Master Requests Table
│
├── dbos_system_architecture.jpg     # System Architecture Diagram (Phase 3)
├── requirements.txt                 # Python dependencies
└── README.md                        # Project documentation
```

---

## Getting Started

### Prerequisites
* **Python 3.10+**
* **MySQL Server 8.0+**
* **C++ Compiler (`g++` / MinGW)**

### 1. Clone the Repository
```bash
git clone https://github.com/DevanshAgarwal27/DBOS.git
cd DBOS
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup the Database
1. Open your MySQL client and run the schema and seed scripts:
   ```sql
   SOURCE database/schema.sql;
   SOURCE database/sample_data.sql;
   ```
2. Configure credentials in `.env` (or set environment variables):
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=dbos_ev
   ```
3. Test connection:
   ```bash
   python backend/test_connection.py
   ```

### 4. Compile C++ Modules
```bash
cd backend
g++ fcfs.cpp -o fcfs.exe
g++ sjf.cpp -o sjf.exe
g++ priority.cpp -o priority.exe
g++ process_manager.cpp -o process_manager.exe
g++ resource_allocator.cpp -o resource_allocator.exe
g++ deadlock_handler.cpp -o deadlock_handler.exe
g++ synchronization.cpp -o synchronization.exe
g++ charging_session.cpp -o charging_session.exe
g++ performance_metrics.cpp -o performance_metrics.exe
cd ..
```

### 5. Launch the System

#### Option A: Web Control Plane (Recommended)
```bash
python backend/server.py
```
Then open **http://localhost:8000** in your browser.
*(Pass an optional port argument if needed: `python backend/server.py 8080`.)*

#### Option B: Interactive Terminal CLI
```bash
python backend/main.py
```

---

## Web Control Plane REST API (`backend/server.py`)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Checks HTTP bridge and MySQL database connectivity |
| `GET` | `/api/ev-catalogue` | Returns verified EV models and registered battery capacities (kWh) |
| `GET` | `/api/users` | Lists registered owners from `APP_USER` newest-first |
| `GET` | `/api/locations` | Lists available station hub locations from `LOCATION` |
| `GET` | `/api/fleet` | Lists registered EVs with owner, location, and operational status |
| `GET` | `/api/requests` | Returns master charging requests with reservation grace-window state |
| `GET` | `/api/queue` | Returns `WAITING`/`READY` PCBs (with Two-Tier Priority, Aging & `target_soc`) and active `RUNNING` sessions |
| `GET` | `/api/telemetry` | Returns live station power headroom, charger availability, and session counts |
| `POST` | `/api/register-ev` | Registers a user (`APP_USER`) and EV (`EV`) in MySQL |
| `POST` | `/api/admit-request` | Resolves/creates owner + EV strictly per person and admits request into `WAITING` |
| `POST` | `/api/scheduler/auto` | Runs the Intelligent Auto-Scheduler (`priority.exe`, `sjf.exe`, or `fcfs.exe`) |
| `POST` | `/api/allocate` | Runs `resource_allocator.exe`, locks chargers (`WAITING -> RUNNING`), and starts `IN_PROGRESS` sessions |
| `POST` | `/api/sessions/simulate-release` | Completes active sessions (`COMPLETED`), releases chargers (`AVAILABLE`), and advances the queue |

---

## Interactive CLI Menu Options (`backend/main.py`)

```text
=================================================================
      DBOS EV CHARGING QUEUE & RESOURCE MANAGEMENT SYSTEM
       Backend Operations Menu
=================================================================
  [1]  Register New User & Electric Vehicle (EV)
  [2]  View All Users
  [3]  View All Registered EVs
  [4]  Create New Charging Request (OS Process)
  [5]  View All Charging Requests
  [6]  View Waiting Processes (OS Process Management)
  [7]  Run Intelligent Auto-Scheduler (Automatic Selection)
  [8]  Run Resource Allocation
  [9]  Run Synchronization & Deadlock Prevention
  [10] Charging Sessions & OS Performance Metrics
  [11] Auto-Simulate & Release All Charging Sessions
  [12] Exit
=================================================================
```

---

## License
This project is developed for academic and educational purposes under the MIT License.

