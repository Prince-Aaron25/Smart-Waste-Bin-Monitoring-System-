# Smart Waste Bin

## Setup (Windows PowerShell)

1. In the project root run:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Generate a new API key with `python -c "import secrets; print(secrets.token_urlsafe(32))"`, and replace the placeholder.
3. Run:
   ```powershell
   cd backend
   python init_db.py
   python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
4. Visit http://127.0.0.1:8000/docs and test `POST /api/readings` with `{"device_id":1,"raw_distance_cm":2.5}` and your `X-API-Key` header.

For ESP32 access on trusted local Wi-Fi, run with `--host 0.0.0.0` instead and use the laptop LAN IPv4 address in the ESP32 HTTP URL. Avoid public port forwarding. ESP32 sketch and dashboard were not present in the original ZIP.

## Notes
- `init_db.py` is safe to rerun; schema creation uses `IF NOT EXISTS`.
- Existing database records are preserved, not migrated or replaced.
- `register_device.py` remains as a compatibility shortcut to initialization.
- The `25.0` cm initial height is only an example: calibrate it to your bin.
- Your Blynk token and Wi-Fi credentials should stay outside shared archives.
