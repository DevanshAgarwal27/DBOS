USE dbos_ev;

-- 1. APP_USER Records
INSERT INTO APP_USER (user_id, username, email, phone_no) VALUES
(1, 'arjun_verma',  'arjun.verma@example.com',  '+919876543210'),
(2, 'priya_sharma', 'priya.sharma@example.com', '+919876543211'),
(3, 'rohit_kumar',  'rohit.kumar@example.com',  '+919876543212'),
(4, 'ananya_iyer',  'ananya.iyer@example.com',  '+919876543213'),
(5, 'vikram_singh', 'vikram.singh@example.com', '+919876543214'),
(6, 'neha_patel',   'neha.patel@example.com',   '+919876543215');

-- 2. LOCATION Records
INSERT INTO LOCATION (location_id, location_name, latitude, longitude) VALUES
(1, 'Indiranagar Hub, Bengaluru',         12.978369, 77.640836),
(2, 'Electronic City Phase 1, Bengaluru', 12.839939, 77.677003),
(3, 'Whitefield IT Corridor, Bengaluru',  12.969800, 77.749900),
(4, 'Koramangala 4th Block, Bengaluru',   12.934500, 77.626500);

-- 3. EV Records
INSERT INTO EV (ev_id, user_id, model, battery_capacity, current_soc, current_location_id) VALUES
(1, 1, 'Tata Nexon EV Max',     40.50, 45.00, 1),
(2, 2, 'MG ZS EV',              50.30, 18.00, 1),
(3, 3, 'Hyundai Kona Electric', 39.20, 70.00, 2),
(4, 4, 'Mahindra XUV400',       34.50, 30.00, 1),
(5, 5, 'BYD Atto 3',            60.48, 15.00, 2),
(6, 6, 'Tata Tiago EV',         24.00, 55.00, 3);

-- 4. STATION Records
INSERT INTO STATION (station_id, station_name, location_id, total_power, status) VALUES
(1, 'Indiranagar Fast Charging Hub',    1, 150.00, 'ACTIVE'),
(2, 'Electronic City Green Power Hub',  2, 120.00, 'ACTIVE'),
(3, 'Whitefield Tech Charge Station',   3,  90.00, 'ACTIVE'),
(4, 'Koramangala Eco Station',          4,  60.00, 'MAINTENANCE');

-- 5. CHARGER Records
INSERT INTO CHARGER (charger_id, station_id, connector_type, power_capacity, status) VALUES
(1, 1, 'CCS2',   60.00, 'OCCUPIED'),
(2, 1, 'CCS2',   60.00, 'OCCUPIED'),
(3, 1, 'Type 2', 22.00, 'AVAILABLE'),
(4, 2, 'CCS2',   50.00, 'OCCUPIED'),
(5, 2, 'CCS2',   50.00, 'AVAILABLE'),
(6, 2, 'Type 2', 22.00, 'AVAILABLE'),
(7, 3, 'CCS2',   50.00, 'AVAILABLE'),
(8, 3, 'Type 2', 22.00, 'FAULTY'),
(9, 4, 'Type 2', 22.00, 'AVAILABLE');

-- 6. CHARGING_REQUEST Records
INSERT INTO CHARGING_REQUEST (request_id, ev_id, arrival_time, required_energy, requested_power, soc_at_request, is_reserved, process_state) VALUES
(1, 1, '2026-10-12 18:00:00', 20.00,  50.00, 20.00, FALSE, 'COMPLETED'),
(2, 2, '2026-10-12 19:30:00', 35.00,  50.00, 18.00, TRUE,  'RUNNING'),
(3, 4, '2026-10-12 19:45:00', 20.00,  50.00, 30.00, FALSE, 'RUNNING'),
(4, 5, '2026-10-12 20:00:00', 40.00,  40.00, 15.00, FALSE, 'RUNNING'),
(5, 3, '2026-10-12 20:15:00', 10.00,  22.00, 70.00, TRUE,  'READY'),
(6, 6, '2026-10-12 20:20:00', 12.00,  50.00, 55.00, FALSE, 'WAITING'),
(7, 1, '2026-10-12 17:00:00', 50.00, 100.00, 10.00, FALSE, 'REJECTED');

-- 7. RESOURCE_ALLOCATION Records
INSERT INTO RESOURCE_ALLOCATION (allocation_id, request_id, charger_id, allocated_power, allocation_time, release_time, status) VALUES
(1, 1, 1, 50.00, '2026-10-12 18:05:00', '2026-10-12 18:35:00', 'RELEASED'),
(2, 2, 1, 50.00, '2026-10-12 19:35:00', NULL,                  'ACTIVE'),
(3, 3, 2, 50.00, '2026-10-12 19:50:00', NULL,                  'ACTIVE'),
(4, 4, 4, 40.00, '2026-10-12 20:05:00', NULL,                  'ACTIVE');

-- 8. CHARGING_SESSION Records
INSERT INTO CHARGING_SESSION (session_id, allocation_id, start_time, end_time, energy_consumed, status) VALUES
(1, 1, '2026-10-12 18:05:00', '2026-10-12 18:35:00', 20.00, 'COMPLETED'),
(2, 2, '2026-10-12 19:35:00', NULL,                  14.50, 'IN_PROGRESS'),
(3, 3, '2026-10-12 19:50:00', NULL,                   8.20, 'IN_PROGRESS'),
(4, 4, '2026-10-12 20:05:00', NULL,                   5.10, 'IN_PROGRESS');

-- 9. SYSTEM_LOG Records
INSERT INTO SYSTEM_LOG (log_id, request_id, event_type, timestamp, details) VALUES
(1,  1,    'PROCESS_CREATED',      '2026-10-12 18:00:00', 'Process created for EV 1. Required energy: 20.00 kWh, Requested power: 50.00 kW, Burst time: 0.40 hrs.'),
(2,  1,    'SCHEDULING',           '2026-10-12 18:01:00', 'FCFS scheduler dispatched Request 1 at head of queue.'),
(3,  1,    'STATION_SELECTED',     '2026-10-12 18:02:00', 'Station 1 (Indiranagar) selected with 150.00 kW available capacity.'),
(4,  1,    'ALLOCATION_SUCCESS',   '2026-10-12 18:05:00', 'Charger 1 and 50.00 kW power atomically allocated to Request 1.'),
(5,  1,    'CHARGING_STARTED',     '2026-10-12 18:05:00', 'Charging Session 1 started on Charger 1.'),
(6,  1,    'CHARGING_COMPLETED',   '2026-10-12 18:35:00', 'Charging Session 1 completed. Total energy consumed: 20.00 kWh.'),
(7,  1,    'RESOURCE_RELEASED',    '2026-10-12 18:35:00', 'Charger 1 and 50.00 kW power released back to Station 1 pool.'),
(8,  2,    'PROCESS_CREATED',      '2026-10-12 19:30:00', 'Process created for EV 2. Priority: High (SoC: 18.00%), Burst time: 0.70 hrs.'),
(9,  2,    'ALLOCATION_SUCCESS',   '2026-10-12 19:35:00', 'Charger 1 and 50.00 kW power atomically allocated to Request 2.'),
(10, 2,    'CHARGING_STARTED',     '2026-10-12 19:35:00', 'Charging Session 2 in progress on Charger 1.'),
(11, 3,    'PROCESS_CREATED',      '2026-10-12 19:45:00', 'Process created for EV 4. SoC: 30.00%, Burst time: 0.40 hrs.'),
(12, 3,    'ALLOCATION_SUCCESS',   '2026-10-12 19:50:00', 'Charger 2 and 50.00 kW power allocated to Request 3.'),
(13, 3,    'CHARGING_STARTED',     '2026-10-12 19:50:00', 'Charging Session 3 in progress on Charger 2.'),
(14, 4,    'PROCESS_CREATED',      '2026-10-12 20:00:00', 'Process created for EV 5. SoC: 15.00%, Burst time: 1.00 hr.'),
(15, 4,    'ALLOCATION_SUCCESS',   '2026-10-12 20:05:00', 'Charger 4 and 40.00 kW power allocated to Request 4 at Station 2.'),
(16, 4,    'CHARGING_STARTED',     '2026-10-12 20:05:00', 'Charging Session 4 in progress on Charger 4.'),
(17, 5,    'REQUEST_WAITING',      '2026-10-12 20:15:00', 'Request 5 enqueued in READY state waiting for compatible charger dispatch.'),
(18, 6,    'REQUEST_WAITING',      '2026-10-12 20:20:00', 'Request 6 enqueued in WAITING state.'),
(19, 7,    'TRANSACTION_ROLLBACK', '2026-10-12 17:01:00', 'Request 7 rejected: requested power 100.00 kW exceeds station feasibility limit; transaction rolled back.'),
(20, NULL, 'SCHEDULING',           '2026-10-12 20:25:00', 'System scheduler daemon cycle executed across all stations. Active power monitored.');
