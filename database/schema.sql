CREATE DATABASE IF NOT EXISTS dbos_ev;
USE dbos_ev;

-- Table 1: APP_USER
CREATE TABLE APP_USER (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone_no VARCHAR(15) NOT NULL
);

-- Table 2: LOCATION
CREATE TABLE LOCATION (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(150) NOT NULL UNIQUE,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    CONSTRAINT chk_location_latitude CHECK (latitude >= -90.000000 AND latitude <= 90.000000),
    CONSTRAINT chk_location_longitude CHECK (longitude >= -180.000000 AND longitude <= 180.000000)
);

-- Table 3: EV
CREATE TABLE EV (
    ev_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    model VARCHAR(100) NOT NULL,
    battery_capacity DECIMAL(10,2) NOT NULL,
    current_soc DECIMAL(5,2) NOT NULL,
    current_location_id INT NOT NULL,
    CONSTRAINT chk_ev_battery_capacity CHECK (battery_capacity > 0.00),
    CONSTRAINT chk_ev_current_soc CHECK (current_soc >= 0.00 AND current_soc <= 100.00),
    FOREIGN KEY (user_id) REFERENCES APP_USER(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (current_location_id) REFERENCES LOCATION(location_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table 4: STATION
CREATE TABLE STATION (
    station_id INT AUTO_INCREMENT PRIMARY KEY,
    station_name VARCHAR(100) NOT NULL,
    location_id INT NOT NULL,
    total_power DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT chk_station_total_power CHECK (total_power > 0.00),
    CONSTRAINT chk_station_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE')),
    FOREIGN KEY (location_id) REFERENCES LOCATION(location_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table 5: CHARGER
CREATE TABLE CHARGER (
    charger_id INT AUTO_INCREMENT PRIMARY KEY,
    station_id INT NOT NULL,
    connector_type VARCHAR(50) NOT NULL,
    power_capacity DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
    CONSTRAINT chk_charger_power_capacity CHECK (power_capacity > 0.00),
    CONSTRAINT chk_charger_status CHECK (status IN ('AVAILABLE', 'OCCUPIED', 'FAULTY')),
    FOREIGN KEY (station_id) REFERENCES STATION(station_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table 6: CHARGING_REQUEST
CREATE TABLE CHARGING_REQUEST (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    ev_id INT NOT NULL,
    arrival_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    required_energy DECIMAL(10,2) NOT NULL,
    requested_power DECIMAL(10,2) NOT NULL,
    soc_at_request DECIMAL(5,2) NOT NULL,
    is_reserved BOOLEAN NOT NULL DEFAULT FALSE,
    reserved_slot_time DATETIME NULL,
    process_state VARCHAR(20) NOT NULL DEFAULT 'WAITING',
    CONSTRAINT chk_request_energy CHECK (required_energy > 0.00),
    CONSTRAINT chk_request_power CHECK (requested_power > 0.00),
    CONSTRAINT chk_request_soc CHECK (soc_at_request >= 0.00 AND soc_at_request <= 100.00),
    CONSTRAINT chk_request_process_state CHECK (process_state IN ('WAITING', 'READY', 'RUNNING', 'COMPLETED', 'REJECTED')),
    FOREIGN KEY (ev_id) REFERENCES EV(ev_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Table 7: RESOURCE_ALLOCATION
CREATE TABLE RESOURCE_ALLOCATION (
    allocation_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    charger_id INT NOT NULL,
    allocated_power DECIMAL(10,2) NOT NULL,
    allocation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    release_time DATETIME NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT chk_allocation_power CHECK (allocated_power > 0.00),
    CONSTRAINT chk_allocation_status CHECK (status IN ('ACTIVE', 'RELEASED')),
    CONSTRAINT chk_allocation_release_time CHECK (release_time IS NULL OR release_time >= allocation_time),
    FOREIGN KEY (request_id) REFERENCES CHARGING_REQUEST(request_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (charger_id) REFERENCES CHARGER(charger_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table 8: CHARGING_SESSION
CREATE TABLE CHARGING_SESSION (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    allocation_id INT NOT NULL UNIQUE,
    start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME NULL,
    energy_consumed DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
    CONSTRAINT chk_session_energy CHECK (energy_consumed >= 0.00),
    CONSTRAINT chk_session_status CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'TERMINATED')),
    CONSTRAINT chk_session_end_time CHECK (end_time IS NULL OR end_time >= start_time),
    FOREIGN KEY (allocation_id) REFERENCES RESOURCE_ALLOCATION(allocation_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table 9: SYSTEM_LOG
CREATE TABLE SYSTEM_LOG (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NULL,
    event_type VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES CHARGING_REQUEST(request_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
