import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class SmokeTest(unittest.TestCase):
    def test_database_and_api(self):
        from fastapi.testclient import TestClient
        import database
        import main
        with tempfile.TemporaryDirectory() as td:
            with patch.object(database, "DB_PATH", Path(td) / "test.db"):
                database.initialize_database()
                database.initialize_database()
                with database.get_connection() as conn:
                    conn.execute("INSERT INTO devices (device_id,device_name,bin_height_cm) VALUES (1,'test',25)")
                with TestClient(main.app) as client:
                    headers={"X-API-Key": os.environ["SMART_BIN_API_KEY"]}
                    r=client.post('/api/readings',json={'device_id':1,'raw_distance_cm':2.5},headers=headers)
                    self.assertEqual(r.status_code,200,r.text)
                    self.assertEqual(r.json()['fill_status'],'full')
                    self.assertEqual(client.get('/api/readings/latest',params={'device_id':1},headers=headers).status_code,200)
                    self.assertEqual(client.get('/api/readings/history',params={'device_id':1},headers=headers).status_code,200)
                    self.assertEqual(client.get('/api/devices/status',params={'device_id':1},headers=headers).status_code,200)
                    self.assertEqual(client.post('/api/readings',json={'device_id':1,'raw_distance_cm':2.5}).status_code,401)

if __name__ == '__main__':
    unittest.main()
