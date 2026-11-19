#!/usr/bin/env python3
"""Pull a recorder site's uploaded event lists into a local database, ready for classify_events.py.

The Android recorder uploads to sites/<site>/ in the dataset:
  events/events_<stamp>.csv   events in each upload
  recordings/<date>/*.m4a     event audio, only when there is no video
  videos/<date>/*.mp4         event videos (H.264 with sound)
  levels/<date>.csv           sound level every second (one file per day)
  status.json                 last known state of the tablet

  python process_site.py --site porch-5th-floor
  python classify_events.py --db sites/porch-5th-floor/sound_events.db \
      --hf-repo drewThomasson/sound-monitor-data --limit 0 --delete-after
  python make_report.py --db sites/porch-5th-floor/sound_events.db --out sites/porch-5th-floor/report
"""
import argparse
import json
import os
import sqlite3

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

COLUMNS = ["timestamp", "duration", "peak_db", "avg_db", "background_db", "filename", "video_filename",
           "low_frequency", "wind_suspected", "site", "calibration_db"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--hf-repo", default="drewThomasson/sound-monitor-data")
    ap.add_argument("--out", default="sites")
    args = ap.parse_args()

    base = f"sites/{args.site}"
    out_dir = os.path.join(args.out, args.site)
    cache = os.path.join(out_dir, "hf_meta")
    os.makedirs(out_dir, exist_ok=True)

    files = HfApi().list_repo_files(args.hf_repo, repo_type="dataset")
    csvs = sorted(f for f in files if f.startswith(f"{base}/events/") and f.endswith(".csv"))
    if not csvs:
        print(f"No uploads from site '{args.site}' yet.")
        return
    frames = [pd.read_csv(hf_hub_download(args.hf_repo, f, repo_type="dataset", local_dir=cache), dtype=str)
              for f in csvs]
    df = pd.concat(frames).fillna("")
    before = len(df)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")  # retried uploads can repeat rows

    db = os.path.join(out_dir, "sound_events.db")
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT UNIQUE, duration REAL, peak_db REAL, avg_db REAL,
        background_db REAL, filename TEXT, video_filename TEXT, low_frequency BOOLEAN, wind_suspected BOOLEAN,
        site TEXT, calibration_db REAL)""")
    rows = [tuple(r[c] for c in COLUMNS) for _, r in df.iterrows()]
    cur = conn.executemany(f"INSERT OR IGNORE INTO events ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})", rows)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"{len(csvs)} uploads, {before} rows ({before - len(df)} repeats) -> {cur.rowcount} new events, {total} total in {db}")

    if f"{base}/status.json" in files:
        st = json.load(open(hf_hub_download(args.hf_repo, f"{base}/status.json", repo_type="dataset", local_dir=cache)))
        print("Tablet status at last upload:", json.dumps(st, indent=2))
    hours = [f for f in files if f.startswith(f"{base}/levels/")]
    print(f"{len(hours)} hours of per-second level logs uploaded")


if __name__ == "__main__":
    main()
