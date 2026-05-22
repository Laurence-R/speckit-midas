from midas.config import load_config
from midas.repositories.database import DatabaseManager
import os

cfg = load_config()
db_path = cfg.db_path
size_kb = os.path.getsize(db_path) / 1024
print("DB:", db_path)
print("大小: %.1f KB" % size_kb)

conn = DatabaseManager(db_path=db_path).connect()
tables = ["tracked_stocks", "market_events", "financial_metrics", "market_overviews", "update_jobs"]
for t in tables:
    n = conn.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
    print(t + ": " + str(n) + " 筆")

print("app_settings:")
for r in conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall():
    v = r["value"]
    if v and len(v) > 12:
        v = v[:8] + "..."
    print("  " + r["key"] + ": " + str(v))
