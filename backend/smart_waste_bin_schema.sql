PRAGMA foreign_keys = ON;

-- Devices are retired with status = 'inactive', not deleted.
-- ON DELETE RESTRICT protects devices that have records; the trigger below
-- blocks deleting any device at all, so the rule is fully enforced.
CREATE TABLE IF NOT EXISTS  devices (
  device_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  device_name   TEXT NOT NULL UNIQUE,
  location      TEXT,
  bin_height_cm REAL NOT NULL CHECK (bin_height_cm > 0),
  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','offline','maintenance')),
  last_seen     DATETIME
);

-- Fill level categories: low 0-49%, half 50-89%, full 90-100% (matches ESP32, LCD, Blynk)
-- Ultrasonic sensor #2 (waste level)
CREATE TABLE IF NOT EXISTS sensor_readings (
  reading_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id         INTEGER NOT NULL REFERENCES devices(device_id) ON DELETE RESTRICT,
  raw_distance_cm   REAL NOT NULL CHECK (raw_distance_cm >= 0),
  clean_distance_cm REAL CHECK (clean_distance_cm >= 0),
  fill_percentage   REAL CHECK (fill_percentage BETWEEN 0 AND 100),
  fill_status       TEXT CHECK (fill_status IN ('low','half','full')),
  recorded_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
  alert_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id   INTEGER NOT NULL REFERENCES devices(device_id) ON DELETE RESTRICT,
  reading_id  INTEGER REFERENCES sensor_readings(reading_id) ON DELETE SET NULL,
  alert_type  TEXT NOT NULL,
  message     TEXT,
  is_resolved INTEGER NOT NULL DEFAULT 0 CHECK (is_resolved IN (0,1)),
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME
);

CREATE TABLE IF NOT EXISTS system_logs (
  log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id   INTEGER REFERENCES devices(device_id) ON DELETE RESTRICT,
  event_type  TEXT NOT NULL,
  description TEXT,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_readings_device_time   ON sensor_readings(device_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_alerts_device_resolved ON alerts(device_id, is_resolved);
CREATE INDEX IF NOT EXISTS idx_logs_device_time       ON system_logs(device_id, created_at);

CREATE TRIGGER IF NOT EXISTS trg_devices_no_delete
BEFORE DELETE ON devices
BEGIN
  SELECT RAISE(ABORT, 'Devices cannot be deleted; set status = ''inactive'' instead.');
END;
