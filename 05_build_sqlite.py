"""
05_build_sqlite.py  (Google Analytics)
--------------------------------------
Loads the processed CSVs into a SQLite database (data/funnel.db). Boolean
funnel flags are cast to 0/1 integers so SUM()/AVG() work in SQL.

NOTE: build the DB on local disk, not a network mount, to avoid SQLite
"disk I/O error" locking issues, then copy it into place.

Run:  python src/05_build_sqlite.py
Then: sqlite3 data/funnel.db ".read sql/funnel_queries_sqlite.sql"
"""

import sqlite3, shutil, os
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
DB = ROOT / "data" / "funnel.db"
TMP = "/tmp/ga_funnel.db"

BOOLS = ["reached_product_view", "reached_cart", "reached_checkout", "purchased"]

def main():
    sessions = pd.read_csv(PROC / "sessions.csv")
    purchases = pd.read_csv(PROC / "purchases.csv")
    for c in BOOLS:
        sessions[c] = sessions[c].astype(bool).astype(int)

    if os.path.exists(TMP):
        os.remove(TMP)
    con = sqlite3.connect(TMP)
    sessions.to_sql("sessions", con, index=False)
    purchases.to_sql("purchases", con, index=False)
    con.execute("CREATE INDEX idx_sess_dev ON sessions(device)")
    con.execute("CREATE INDEX idx_sess_ch ON sessions(channel)")
    con.commit(); con.close()
    shutil.copy(TMP, DB)

    print(f"Built {DB.relative_to(ROOT)}  (sessions: {len(sessions):,}, purchases: {len(purchases):,})")

if __name__ == "__main__":
    main()
