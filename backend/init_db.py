from database import initialize_database, get_connection


def main():
    initialize_database()
    with get_connection() as conn:
        conn.execute("""INSERT OR IGNORE INTO devices
            (device_id, device_name, location, bin_height_cm)
            VALUES (1, 'Smart Waste Bin 01', 'School Project', 25.0)""")
    print("Database initialized; existing readings preserved.")


if __name__ == "__main__":
    main()
