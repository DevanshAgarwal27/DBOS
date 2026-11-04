"""
Database Module
Handles MySQL database connections and executes parameterized queries.
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import mysql.connector
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def get_connection():
    """
    Connects to MySQL using settings from config.py and returns the connection object.
    """
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def execute_select(query, params=None):
    """
    Executes a SELECT query with parameters and returns all rows as a list of dictionaries.
    Properly closes cursor and connection in the finally block.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print(f"Database error during SELECT: {e}")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def execute_modify(query, params=None):
    """
    Executes an INSERT, UPDATE, or DELETE query with parameters and commits changes.
    Rolls back transaction on error and always closes cursor and connection.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        if conn is not None:
            conn.rollback()
        print(f"Database error during modify: {e}")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_waiting_requests():
    """
    Fetches real charging requests from MySQL where process_state = 'WAITING'.
    Retrieves request ID, EV ID, EV model, arrival time, required energy,
    requested power, and process state by joining CHARGING_REQUEST and EV.
    Does not modify any database records.
    Returns a list of dictionaries, or an empty list if none found or on error.
    """
    query = """
        SELECT 
            r.request_id,
            r.ev_id,
            e.model AS ev_model,
            r.arrival_time,
            r.required_energy,
            r.requested_power,
            r.soc_at_request,
            r.is_reserved,
            r.process_state
        FROM CHARGING_REQUEST r
        JOIN EV e ON r.ev_id = e.ev_id
        WHERE r.process_state = 'WAITING'
        ORDER BY r.arrival_time ASC, r.request_id ASC;
    """
    try:
        rows = execute_select(query)
        return rows if rows is not None else []
    except Exception:
        try:
            fallback_query = query.replace("r.is_reserved,\n", "")
            rows = execute_select(fallback_query)
            if rows:
                for row in rows:
                    row["is_reserved"] = False
            return rows if rows is not None else []
        except Exception as e:
            print(f"[ERROR] Database error fetching waiting requests: {e}")
            return []


def get_resource_allocation_inputs():
    """
    Step 5: Fetches all data required by the C++ Resource Allocator:
      1. Waiting requests with EV details and location
      2. Active stations with dynamically computed used power
      3. Available chargers at active stations
    """
    req_query = """
        SELECT 
            r.request_id,
            r.ev_id,
            e.model AS ev_model,
            r.arrival_time,
            r.required_energy,
            r.requested_power,
            r.soc_at_request,
            r.process_state,
            e.current_location_id AS location_id
        FROM CHARGING_REQUEST r
        JOIN EV e ON r.ev_id = e.ev_id
        WHERE r.process_state = 'WAITING'
        ORDER BY r.arrival_time ASC, r.request_id ASC;
    """

    station_query = """
        SELECT 
            s.station_id,
            s.station_name,
            s.location_id,
            s.total_power,
            s.status,
            COALESCE((
                SELECT SUM(ra.allocated_power)
                FROM RESOURCE_ALLOCATION ra
                JOIN CHARGER c ON ra.charger_id = c.charger_id
                WHERE c.station_id = s.station_id AND ra.status = 'ACTIVE'
            ), 0.00) AS used_power
        FROM STATION s
        WHERE s.status = 'ACTIVE'
        ORDER BY s.station_id ASC;
    """

    charger_query = """
        SELECT 
            c.charger_id,
            c.station_id,
            c.connector_type,
            c.power_capacity,
            c.status
        FROM CHARGER c
        JOIN STATION s ON c.station_id = s.station_id
        WHERE c.status = 'AVAILABLE' AND s.status = 'ACTIVE'
        ORDER BY c.charger_id ASC;
    """

    requests = execute_select(req_query) or []
    stations = execute_select(station_query) or []
    chargers = execute_select(charger_query) or []

    return requests, stations, chargers


def commit_resource_allocations_atomic(proposals, rejections=None):
    """
    Step 5: Safely rechecks resource availability and commits proposed allocations
    and rejections inside an atomic MySQL transaction.
    """
    if not proposals and not rejections:
        return 0, 0, "No allocation proposals or rejections to commit."

    conn = None
    cursor = None
    allocated_count = 0
    rejected_count = 0

    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        if rejections:
            for rej in rejections:
                req_id = int(rej["request_id"])
                power = float(rej["requested_power"])

                cursor.execute(
                    "UPDATE CHARGING_REQUEST SET process_state = 'REJECTED' WHERE request_id = %s;",
                    (req_id,)
                )
                log_details = f"Request {req_id} rejected: requested power {power:.2f} kW exceeds station feasibility limit; transaction rolled back."
                cursor.execute(
                    """
                    INSERT INTO SYSTEM_LOG (request_id, event_type, timestamp, details)
                    VALUES (%s, 'TRANSACTION_ROLLBACK', NOW(), %s);
                    """,
                    (req_id, log_details)
                )
                rejected_count += 1

        if proposals:
            for prop in proposals:
                req_id = int(prop["request_id"])
                charger_id = int(prop["charger_id"])
                station_id = int(prop["station_id"])
                power = float(prop["allocated_power"])

                cursor.execute(
                    "SELECT request_id, process_state, requested_power FROM CHARGING_REQUEST WHERE request_id = %s FOR UPDATE;",
                    (req_id,)
                )
                req_row = cursor.fetchone()
                if not req_row or req_row["process_state"] != "WAITING":
                    raise ValueError(f"Request {req_id} is no longer in WAITING state.")

                cursor.execute(
                    "SELECT charger_id, station_id, power_capacity, status FROM CHARGER WHERE charger_id = %s FOR UPDATE;",
                    (charger_id,)
                )
                charger_row = cursor.fetchone()
                if not charger_row or charger_row["status"] != "AVAILABLE":
                    raise ValueError(f"Charger {charger_id} is no longer AVAILABLE.")
                if float(charger_row["power_capacity"]) < power:
                    raise ValueError(f"Charger {charger_id} capacity ({charger_row['power_capacity']} kW) < requested power ({power} kW).")

                cursor.execute(
                    "SELECT station_id, total_power, status FROM STATION WHERE station_id = %s FOR UPDATE;",
                    (station_id,)
                )
                station_row = cursor.fetchone()
                if not station_row or station_row["status"] != "ACTIVE":
                    raise ValueError(f"Station {station_id} is no longer ACTIVE.")

                cursor.execute(
                    """
                    SELECT COALESCE(SUM(ra.allocated_power), 0.00) AS used_power
                    FROM RESOURCE_ALLOCATION ra
                    JOIN CHARGER c ON ra.charger_id = c.charger_id
                    WHERE c.station_id = %s AND ra.status = 'ACTIVE';
                    """,
                    (station_id,)
                )
                used_row = cursor.fetchone()
                used_power = float(used_row["used_power"]) if used_row else 0.0
                total_power = float(station_row["total_power"])
                remaining_power = total_power - used_power

                if remaining_power < power:
                    raise ValueError(f"Station {station_id} remaining power ({remaining_power:.2f} kW) < required power ({power:.2f} kW).")

                cursor.execute(
                    """
                    INSERT INTO RESOURCE_ALLOCATION (request_id, charger_id, allocated_power, allocation_time, status)
                    VALUES (%s, %s, %s, NOW(), 'ACTIVE');
                    """,
                    (req_id, charger_id, power)
                )

                cursor.execute(
                    "UPDATE CHARGER SET status = 'OCCUPIED' WHERE charger_id = %s;",
                    (charger_id,)
                )

                cursor.execute(
                    "UPDATE CHARGING_REQUEST SET process_state = 'RUNNING' WHERE request_id = %s;",
                    (req_id,)
                )

                log_details = f"Charger {charger_id} and {power:.2f} kW power atomically allocated to Request {req_id} at Station {station_id}."
                cursor.execute(
                    """
                    INSERT INTO SYSTEM_LOG (request_id, event_type, timestamp, details)
                    VALUES (%s, 'ALLOCATION_SUCCESS', NOW(), %s);
                    """,
                    (req_id, log_details)
                )

                allocated_count += 1

        conn.commit()
        return allocated_count, rejected_count, None

    except Exception as e:
        if conn is not None:
            conn.rollback()
        err_msg = str(e)
        try:
            execute_modify(
                """
                INSERT INTO SYSTEM_LOG (request_id, event_type, timestamp, details)
                VALUES (NULL, 'TRANSACTION_ROLLBACK', NOW(), %s);
                """,
                (f"Resource allocation transaction rolled back: {err_msg}",)
            )
        except Exception:
            pass
        return 0, 0, err_msg
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_allocations_without_session():
    query = """
        SELECT 
            ra.allocation_id,
            ra.request_id,
            ra.charger_id,
            ra.allocated_power,
            ra.allocation_time,
            e.model AS ev_model,
            r.required_energy
        FROM RESOURCE_ALLOCATION ra
        JOIN CHARGING_REQUEST r ON ra.request_id = r.request_id
        JOIN EV e ON r.ev_id = e.ev_id
        LEFT JOIN CHARGING_SESSION cs ON ra.allocation_id = cs.allocation_id
        WHERE ra.status = 'ACTIVE' AND cs.session_id IS NULL
        ORDER BY ra.allocation_id ASC;
    """
    return execute_select(query) or []


def start_charging_session_atomic(allocation_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT ra.allocation_id, ra.request_id, ra.charger_id, ra.allocated_power, ra.status, cs.session_id
            FROM RESOURCE_ALLOCATION ra
            LEFT JOIN CHARGING_SESSION cs ON ra.allocation_id = cs.allocation_id
            WHERE ra.allocation_id = %s FOR UPDATE;
            """,
            (allocation_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Allocation #{allocation_id} not found.")
        if row["status"] != "ACTIVE":
            raise ValueError(f"Allocation #{allocation_id} is not ACTIVE.")
        if row["session_id"] is not None:
            raise ValueError(f"Allocation #{allocation_id} already has an existing session (#{row['session_id']}).")

        req_id = row["request_id"]
        charger_id = row["charger_id"]

        cursor.execute(
            """
            INSERT INTO CHARGING_SESSION (allocation_id, start_time, energy_consumed, status)
            VALUES (%s, NOW(), 0.00, 'IN_PROGRESS');
            """,
            (allocation_id,)
        )
        session_id = cursor.lastrowid

        details = f"Charging Session {session_id} started for Request {req_id} on Charger {charger_id}."
        cursor.execute(
            """
            INSERT INTO SYSTEM_LOG (request_id, event_type, timestamp, details)
            VALUES (%s, 'CHARGING_STARTED', NOW(), %s);
            """,
            (req_id, details)
        )

        conn.commit()
        return session_id, None
    except Exception as e:
        if conn is not None:
            conn.rollback()
        return None, str(e)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_in_progress_sessions():
    """
    Step 7: Fetches all charging sessions that are currently IN_PROGRESS.
    """
    query = """
        SELECT 
            cs.session_id,
            cs.allocation_id,
            cs.start_time,
            ra.request_id,
            ra.charger_id,
            c.station_id,
            s.station_name,
            ra.allocated_power,
            r.required_energy,
            e.model AS ev_model
        FROM CHARGING_SESSION cs
        JOIN RESOURCE_ALLOCATION ra ON cs.allocation_id = ra.allocation_id
        JOIN CHARGER c ON ra.charger_id = c.charger_id
        JOIN STATION s ON c.station_id = s.station_id
        JOIN CHARGING_REQUEST r ON ra.request_id = r.request_id
        JOIN EV e ON r.ev_id = e.ev_id
        WHERE cs.status = 'IN_PROGRESS'
        ORDER BY cs.session_id ASC;
    """
    return execute_select(query) or []


def complete_charging_session_atomic(session_id):
    """
    Step 7: Atomically completes an in-progress charging session and releases all resources:
      1. Locks CHARGING_SESSION (verifies status = 'IN_PROGRESS')
      2. Updates CHARGING_SESSION status to 'COMPLETED', end_time = NOW(), energy_consumed = required_energy
      3. Updates RESOURCE_ALLOCATION status to 'RELEASED', release_time = NOW()
      4. Updates CHARGER status to 'AVAILABLE' (returns port to pool)
      5. Updates CHARGING_REQUEST process_state to 'COMPLETED'
      6. Inserts 'CHARGING_COMPLETED' and 'RESOURCE_RELEASED' into SYSTEM_LOG
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT 
                cs.session_id,
                cs.status AS session_status,
                cs.allocation_id,
                ra.request_id,
                ra.charger_id,
                c.station_id,
                ra.allocated_power,
                r.required_energy,
                e.model AS ev_model
            FROM CHARGING_SESSION cs
            JOIN RESOURCE_ALLOCATION ra ON cs.allocation_id = ra.allocation_id
            JOIN CHARGER c ON ra.charger_id = c.charger_id
            JOIN CHARGING_REQUEST r ON ra.request_id = r.request_id
            JOIN EV e ON r.ev_id = e.ev_id
            WHERE cs.session_id = %s FOR UPDATE;
            """,
            (session_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Session #{session_id} not found.")
        if row["session_status"] != "IN_PROGRESS":
            raise ValueError(f"Session #{session_id} is already '{row['session_status']}'. Cannot complete again.")

        alloc_id = row["allocation_id"]
        req_id = row["request_id"]
        charger_id = row["charger_id"]
        station_id = row["station_id"]
        energy = float(row["required_energy"])
        power = float(row["allocated_power"])

        cursor.execute(
            """
            UPDATE CHARGING_SESSION 
            SET status = 'COMPLETED', end_time = NOW(), energy_consumed = %s
            WHERE session_id = %s;
            """,
            (energy, session_id)
        )

        cursor.execute(
            """
            UPDATE RESOURCE_ALLOCATION 
            SET status = 'RELEASED', release_time = NOW()
            WHERE allocation_id = %s;
            """,
            (alloc_id,)
        )

        cursor.execute(
            "UPDATE CHARGER SET status = 'AVAILABLE' WHERE charger_id = %s;",
            (charger_id,)
        )

        cursor.execute(
            "UPDATE CHARGING_REQUEST SET process_state = 'COMPLETED' WHERE request_id = %s;",
            (req_id,)
        )

        cursor.execute(
            """
            INSERT INTO SYSTEM_LOG (request_id, event_type, timestamp, details)
            VALUES (%s, 'CHARGING_COMPLETED', NOW(), %s);
            """,
            (req_id, f"Charging Session {session_id} completed. Total energy consumed: {energy:.2f} kWh.")
        )
        cursor.execute(
            """
            INSERT INTO SYSTEM_LOG (request_id, event_type, timestamp, details)
            VALUES (%s, 'RESOURCE_RELEASED', NOW(), %s);
            """,
            (req_id, f"Charger {charger_id} and {power:.2f} kW power released back to Station {station_id} pool.")
        )

        conn.commit()
        return row, None
    except Exception as e:
        if conn is not None:
            conn.rollback()
        return None, str(e)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def get_all_charging_sessions():
    """
    Step 7: Fetches all charging sessions with EV and charger information for display.
    """
    query = """
        SELECT 
            cs.session_id,
            cs.allocation_id,
            ra.request_id,
            e.model AS ev_model,
            ra.charger_id,
            cs.start_time,
            cs.end_time,
            cs.energy_consumed,
            cs.status
        FROM CHARGING_SESSION cs
        JOIN RESOURCE_ALLOCATION ra ON cs.allocation_id = ra.allocation_id
        JOIN CHARGING_REQUEST r ON ra.request_id = r.request_id
        JOIN EV e ON r.ev_id = e.ev_id
        ORDER BY cs.session_id ASC;
    """
    return execute_select(query) or []


def get_all_requests_for_metrics():
    """
    Step 7: Fetches requests from CHARGING_REQUEST for OS performance metrics calculation.
    """
    query = """
        SELECT 
            r.request_id,
            r.ev_id,
            e.model AS ev_model,
            r.arrival_time,
            r.required_energy,
            r.requested_power,
            r.soc_at_request,
            r.process_state
        FROM CHARGING_REQUEST r
        JOIN EV e ON r.ev_id = e.ev_id
        ORDER BY r.arrival_time ASC, r.request_id ASC;
    """
    return execute_select(query) or []



