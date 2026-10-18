-- MySQL Dump Backup for Database: dbos_ev
-- Created before user cleanup operation

SET FOREIGN_KEY_CHECKS=0;

-- Table structure for table `app_user`
DROP TABLE IF EXISTS `app_user`;
CREATE TABLE `app_user` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `phone_no` varchar(15) NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `app_user`
INSERT INTO `app_user` (`user_id`, `username`, `email`, `phone_no`) VALUES
  (1, 'arjun_verma', 'arjun.verma@example.com', '+919876543210'),
  (2, 'priya_sharma', 'priya.sharma@example.com', '+919876543211'),
  (3, 'rohit_kumar', 'rohit.kumar@example.com', '+919876543212'),
  (4, 'ananya_iyer', 'ananya.iyer@example.com', '+919876543213'),
  (5, 'vikram_singh', 'vikram.singh@example.com', '+919876543214'),
  (6, 'neha_patel', 'neha.patel@example.com', '+919876543215'),
  (7, 'DEVANSH AGARWAL', 'devansh@gmail.com', '9876543210'),
  (8, 'Mukul', 'mukul@gmail.com', '987654321'),
  (9, 'HARSHIT MALHOTRA', 'harshit@gmail.com', '9216549780'),
  (10, 'JOSEPH CLERK', 'joseph@gmail.com', '9927456789');

-- Table structure for table `charger`
DROP TABLE IF EXISTS `charger`;
CREATE TABLE `charger` (
  `charger_id` int NOT NULL AUTO_INCREMENT,
  `station_id` int NOT NULL,
  `connector_type` varchar(50) NOT NULL,
  `power_capacity` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'AVAILABLE',
  PRIMARY KEY (`charger_id`),
  KEY `station_id` (`station_id`),
  CONSTRAINT `charger_ibfk_1` FOREIGN KEY (`station_id`) REFERENCES `station` (`station_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_charger_power_capacity` CHECK ((`power_capacity` > 0.00)),
  CONSTRAINT `chk_charger_status` CHECK ((`status` in (_cp850'AVAILABLE',_cp850'OCCUPIED',_cp850'FAULTY')))
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `charger`
INSERT INTO `charger` (`charger_id`, `station_id`, `connector_type`, `power_capacity`, `status`) VALUES
  (1, 1, 'CCS2', '60.00', 'OCCUPIED'),
  (2, 1, 'CCS2', '60.00', 'OCCUPIED'),
  (3, 1, 'Type 2', '22.00', 'AVAILABLE'),
  (4, 2, 'CCS2', '50.00', 'OCCUPIED'),
  (5, 2, 'CCS2', '50.00', 'AVAILABLE'),
  (6, 2, 'Type 2', '22.00', 'AVAILABLE'),
  (7, 3, 'CCS2', '50.00', 'AVAILABLE'),
  (8, 3, 'Type 2', '22.00', 'FAULTY'),
  (9, 4, 'Type 2', '22.00', 'AVAILABLE');

-- Table structure for table `charging_request`
DROP TABLE IF EXISTS `charging_request`;
CREATE TABLE `charging_request` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `ev_id` int NOT NULL,
  `arrival_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `required_energy` decimal(10,2) NOT NULL,
  `requested_power` decimal(10,2) NOT NULL,
  `soc_at_request` decimal(5,2) NOT NULL,
  `process_state` varchar(20) NOT NULL DEFAULT 'WAITING',
  PRIMARY KEY (`request_id`),
  KEY `ev_id` (`ev_id`),
  CONSTRAINT `charging_request_ibfk_1` FOREIGN KEY (`ev_id`) REFERENCES `ev` (`ev_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_request_energy` CHECK ((`required_energy` > 0.00)),
  CONSTRAINT `chk_request_power` CHECK ((`requested_power` > 0.00)),
  CONSTRAINT `chk_request_process_state` CHECK ((`process_state` in (_cp850'WAITING',_cp850'READY',_cp850'RUNNING',_cp850'COMPLETED',_cp850'REJECTED'))),
  CONSTRAINT `chk_request_soc` CHECK (((`soc_at_request` >= 0.00) and (`soc_at_request` <= 100.00)))
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `charging_request`
INSERT INTO `charging_request` (`request_id`, `ev_id`, `arrival_time`, `required_energy`, `requested_power`, `soc_at_request`, `process_state`) VALUES
  (1, 1, '2026-10-12 18:00:00', '20.00', '50.00', '20.00', 'COMPLETED'),
  (2, 2, '2026-10-12 19:30:00', '35.00', '50.00', '18.00', 'RUNNING'),
  (3, 4, '2026-10-12 19:45:00', '20.00', '50.00', '30.00', 'RUNNING'),
  (4, 5, '2026-10-12 20:00:00', '40.00', '40.00', '15.00', 'RUNNING'),
  (5, 3, '2026-10-12 20:15:00', '10.00', '22.00', '70.00', 'READY'),
  (6, 6, '2026-10-12 20:20:00', '12.00', '50.00', '55.00', 'WAITING'),
  (7, 1, '2026-10-12 17:00:00', '50.00', '100.00', '10.00', 'REJECTED'),
  (9, 9, '2026-10-14 22:16:44', '24.00', '12.00', '59.00', 'WAITING');

-- Table structure for table `charging_session`
DROP TABLE IF EXISTS `charging_session`;
CREATE TABLE `charging_session` (
  `session_id` int NOT NULL AUTO_INCREMENT,
  `allocation_id` int NOT NULL,
  `start_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `end_time` datetime DEFAULT NULL,
  `energy_consumed` decimal(10,2) NOT NULL DEFAULT '0.00',
  `status` varchar(20) NOT NULL DEFAULT 'IN_PROGRESS',
  PRIMARY KEY (`session_id`),
  UNIQUE KEY `allocation_id` (`allocation_id`),
  CONSTRAINT `charging_session_ibfk_1` FOREIGN KEY (`allocation_id`) REFERENCES `resource_allocation` (`allocation_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_session_end_time` CHECK (((`end_time` is null) or (`end_time` >= `start_time`))),
  CONSTRAINT `chk_session_energy` CHECK ((`energy_consumed` >= 0.00)),
  CONSTRAINT `chk_session_status` CHECK ((`status` in (_cp850'IN_PROGRESS',_cp850'COMPLETED',_cp850'TERMINATED')))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `charging_session`
INSERT INTO `charging_session` (`session_id`, `allocation_id`, `start_time`, `end_time`, `energy_consumed`, `status`) VALUES
  (1, 1, '2026-10-12 18:05:00', '2026-10-12 18:35:00', '20.00', 'COMPLETED'),
  (2, 2, '2026-10-12 19:35:00', NULL, '14.50', 'IN_PROGRESS'),
  (3, 3, '2026-10-12 19:50:00', NULL, '8.20', 'IN_PROGRESS'),
  (4, 4, '2026-10-12 20:05:00', NULL, '5.10', 'IN_PROGRESS');

-- Table structure for table `ev`
DROP TABLE IF EXISTS `ev`;
CREATE TABLE `ev` (
  `ev_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `model` varchar(100) NOT NULL,
  `battery_capacity` decimal(10,2) NOT NULL,
  `current_soc` decimal(5,2) NOT NULL,
  `current_location_id` int NOT NULL,
  PRIMARY KEY (`ev_id`),
  KEY `user_id` (`user_id`),
  KEY `current_location_id` (`current_location_id`),
  CONSTRAINT `ev_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`user_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `ev_ibfk_2` FOREIGN KEY (`current_location_id`) REFERENCES `location` (`location_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_ev_battery_capacity` CHECK ((`battery_capacity` > 0.00)),
  CONSTRAINT `chk_ev_current_soc` CHECK (((`current_soc` >= 0.00) and (`current_soc` <= 100.00)))
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `ev`
INSERT INTO `ev` (`ev_id`, `user_id`, `model`, `battery_capacity`, `current_soc`, `current_location_id`) VALUES
  (1, 1, 'Tata Nexon EV Max', '40.50', '45.00', 1),
  (2, 2, 'MG ZS EV', '50.30', '18.00', 1),
  (3, 3, 'Hyundai Kona Electric', '39.20', '70.00', 2),
  (4, 4, 'Mahindra XUV400', '34.50', '30.00', 1),
  (5, 5, 'BYD Atto 3', '60.48', '15.00', 2),
  (6, 6, 'Tata Tiago EV', '24.00', '55.00', 3),
  (7, 7, 'Tata Nexon EV', '40.50', '25.00', 1),
  (8, 8, 'Kia EV6', '77.40', '65.00', 3),
  (9, 9, 'MG ZS EV', '50.30', '59.00', 3),
  (10, 10, 'BMW i4', '83.90', '20.00', 3);

-- Table structure for table `location`
DROP TABLE IF EXISTS `location`;
CREATE TABLE `location` (
  `location_id` int NOT NULL AUTO_INCREMENT,
  `location_name` varchar(150) NOT NULL,
  `latitude` decimal(9,6) NOT NULL,
  `longitude` decimal(9,6) NOT NULL,
  PRIMARY KEY (`location_id`),
  UNIQUE KEY `location_name` (`location_name`),
  CONSTRAINT `chk_location_latitude` CHECK (((`latitude` >= -(90.000000)) and (`latitude` <= 90.000000))),
  CONSTRAINT `chk_location_longitude` CHECK (((`longitude` >= -(180.000000)) and (`longitude` <= 180.000000)))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `location`
INSERT INTO `location` (`location_id`, `location_name`, `latitude`, `longitude`) VALUES
  (1, 'Indiranagar Hub, Bengaluru', '12.978369', '77.640836'),
  (2, 'Electronic City Phase 1, Bengaluru', '12.839939', '77.677003'),
  (3, 'Whitefield IT Corridor, Bengaluru', '12.969800', '77.749900'),
  (4, 'Koramangala 4th Block, Bengaluru', '12.934500', '77.626500');

-- Table structure for table `resource_allocation`
DROP TABLE IF EXISTS `resource_allocation`;
CREATE TABLE `resource_allocation` (
  `allocation_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int NOT NULL,
  `charger_id` int NOT NULL,
  `allocated_power` decimal(10,2) NOT NULL,
  `allocation_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `release_time` datetime DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`allocation_id`),
  KEY `request_id` (`request_id`),
  KEY `charger_id` (`charger_id`),
  CONSTRAINT `resource_allocation_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `charging_request` (`request_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `resource_allocation_ibfk_2` FOREIGN KEY (`charger_id`) REFERENCES `charger` (`charger_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_allocation_power` CHECK ((`allocated_power` > 0.00)),
  CONSTRAINT `chk_allocation_release_time` CHECK (((`release_time` is null) or (`release_time` >= `allocation_time`))),
  CONSTRAINT `chk_allocation_status` CHECK ((`status` in (_cp850'ACTIVE',_cp850'RELEASED')))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `resource_allocation`
INSERT INTO `resource_allocation` (`allocation_id`, `request_id`, `charger_id`, `allocated_power`, `allocation_time`, `release_time`, `status`) VALUES
  (1, 1, 1, '50.00', '2026-10-12 18:05:00', '2026-10-12 18:35:00', 'RELEASED'),
  (2, 2, 1, '50.00', '2026-10-12 19:35:00', NULL, 'ACTIVE'),
  (3, 3, 2, '50.00', '2026-10-12 19:50:00', NULL, 'ACTIVE'),
  (4, 4, 4, '40.00', '2026-10-12 20:05:00', NULL, 'ACTIVE');

-- Table structure for table `station`
DROP TABLE IF EXISTS `station`;
CREATE TABLE `station` (
  `station_id` int NOT NULL AUTO_INCREMENT,
  `station_name` varchar(100) NOT NULL,
  `location_id` int NOT NULL,
  `total_power` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`station_id`),
  KEY `location_id` (`location_id`),
  CONSTRAINT `station_ibfk_1` FOREIGN KEY (`location_id`) REFERENCES `location` (`location_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_station_status` CHECK ((`status` in (_cp850'ACTIVE',_cp850'INACTIVE',_cp850'MAINTENANCE'))),
  CONSTRAINT `chk_station_total_power` CHECK ((`total_power` > 0.00))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `station`
INSERT INTO `station` (`station_id`, `station_name`, `location_id`, `total_power`, `status`) VALUES
  (1, 'Indiranagar Fast Charging Hub', 1, '150.00', 'ACTIVE'),
  (2, 'Electronic City Green Power Hub', 2, '120.00', 'ACTIVE'),
  (3, 'Whitefield Tech Charge Station', 3, '90.00', 'ACTIVE'),
  (4, 'Koramangala Eco Station', 4, '60.00', 'MAINTENANCE');

-- Table structure for table `system_log`
DROP TABLE IF EXISTS `system_log`;
CREATE TABLE `system_log` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int DEFAULT NULL,
  `event_type` varchar(50) NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `details` text NOT NULL,
  PRIMARY KEY (`log_id`),
  KEY `request_id` (`request_id`),
  CONSTRAINT `system_log_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `charging_request` (`request_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Dumping data for table `system_log`
INSERT INTO `system_log` (`log_id`, `request_id`, `event_type`, `timestamp`, `details`) VALUES
  (1, 1, 'PROCESS_CREATED', '2026-10-12 18:00:00', 'Process created for EV 1. Required energy: 20.00 kWh, Requested power: 50.00 kW, Burst time: 0.40 hrs.'),
  (2, 1, 'SCHEDULING', '2026-10-12 18:01:00', 'FCFS scheduler dispatched Request 1 at head of queue.'),
  (3, 1, 'STATION_SELECTED', '2026-10-12 18:02:00', 'Station 1 (Indiranagar) selected with 150.00 kW available capacity.'),
  (4, 1, 'ALLOCATION_SUCCESS', '2026-10-12 18:05:00', 'Charger 1 and 50.00 kW power atomically allocated to Request 1.'),
  (5, 1, 'CHARGING_STARTED', '2026-10-12 18:05:00', 'Charging Session 1 started on Charger 1.'),
  (6, 1, 'CHARGING_COMPLETED', '2026-10-12 18:35:00', 'Charging Session 1 completed. Total energy consumed: 20.00 kWh.'),
  (7, 1, 'RESOURCE_RELEASED', '2026-10-12 18:35:00', 'Charger 1 and 50.00 kW power released back to Station 1 pool.'),
  (8, 2, 'PROCESS_CREATED', '2026-10-12 19:30:00', 'Process created for EV 2. Priority: High (SoC: 18.00%), Burst time: 0.70 hrs.'),
  (9, 2, 'ALLOCATION_SUCCESS', '2026-10-12 19:35:00', 'Charger 1 and 50.00 kW power atomically allocated to Request 2.'),
  (10, 2, 'CHARGING_STARTED', '2026-10-12 19:35:00', 'Charging Session 2 in progress on Charger 1.'),
  (11, 3, 'PROCESS_CREATED', '2026-10-12 19:45:00', 'Process created for EV 4. SoC: 30.00%, Burst time: 0.40 hrs.'),
  (12, 3, 'ALLOCATION_SUCCESS', '2026-10-12 19:50:00', 'Charger 2 and 50.00 kW power allocated to Request 3.'),
  (13, 3, 'CHARGING_STARTED', '2026-10-12 19:50:00', 'Charging Session 3 in progress on Charger 2.'),
  (14, 4, 'PROCESS_CREATED', '2026-10-12 20:00:00', 'Process created for EV 5. SoC: 15.00%, Burst time: 1.00 hr.'),
  (15, 4, 'ALLOCATION_SUCCESS', '2026-10-12 20:05:00', 'Charger 4 and 40.00 kW power allocated to Request 4 at Station 2.'),
  (16, 4, 'CHARGING_STARTED', '2026-10-12 20:05:00', 'Charging Session 4 in progress on Charger 4.'),
  (17, 5, 'REQUEST_WAITING', '2026-10-12 20:15:00', 'Request 5 enqueued in READY state waiting for compatible charger dispatch.'),
  (18, 6, 'REQUEST_WAITING', '2026-10-12 20:20:00', 'Request 6 enqueued in WAITING state.'),
  (19, 7, 'TRANSACTION_ROLLBACK', '2026-10-12 17:01:00', 'Request 7 rejected: requested power 100.00 kW exceeds station feasibility limit; transaction rolled back.'),
  (20, NULL, 'SCHEDULING', '2026-10-12 20:25:00', 'System scheduler daemon cycle executed across all stations. Active power monitored.');

SET FOREIGN_KEY_CHECKS=1;
