#!/usr/bin/env python3
"""Download videos for the loudest nighttime revving events (only those videos).

  python fetch_top_videos.py --db sound_events.db --hf-repo drewThomasson/sound-monitor-data --top 20

Picks revving events between --night-start and --night-end, loudest first, with at
most --per-night per night so the set isn't all from one bad night. Videos land in
<audio-root>/videos/... (same layout as the dataset) and are listed in
<out>/top_videos.csv.
"""
import argparse
import os
import sqlite3

import subprocess

import pandas as pd


def to_web(root, video, audio):
    """Re-encode to H.264 (browsers can't play the original MPEG-4 Part 2) and add the event audio.
    Writes <root>/web/<video> and deletes the original download."""
    src, aud, dst = (os.path.join(root, video), os.path.join(root, audio), os.path.join(root, "web", video))
    if os.path.exists(dst):
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src]
    if os.path.exists(aud):
        cmd += ["-i", aud, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)
    os.remove(src)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="sound_events.db")
    ap.add_argument("--hf-repo", required=True)
    ap.add_argument("--audio-root", default="hf_cache")
    ap.add_argument("--out", default="report")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--per-night", type=int, default=2)
    ap.add_argument("--night-start", type=int, default=22)
    ap.add_argument("--night-end", type=int, default=7)
    args = ap.parse_args()

    df = pd.read_sql("SELECT id, timestamp, duration, peak_db, p_revving, p_siren, filename, video_filename "
                     "FROM events WHERE label='revving' AND video_filename IS NOT NULL AND video_filename != ''",
                     sqlite3.connect(args.db))
    df["ts"] = pd.to_datetime(df.timestamp, format="mixed")
    h = df.ts.dt.hour
    df = df[(h >= args.night_start) | (h < args.night_end)].copy()
    df["night"] = (df.ts - pd.Timedelta(hours=args.night_end)).dt.date
    df = df.sort_values(["peak_db", "p_revving"], ascending=False)
    picks = df.groupby("night", sort=False).head(args.per_night).head(args.top)

    from huggingface_hub import hf_hub_download
    got = []
    for _, r in picks.iterrows():
        try:
            for f in (r.video_filename, r.filename):  # audio too: event videos are silent
                hf_hub_download(args.hf_repo, f, repo_type="dataset", local_dir=args.audio_root)
            to_web(args.audio_root, r.video_filename, r.filename)
            got.append(r)
        except Exception as e:
            print(f"  skipped {r.video_filename}: {e}")
    out = pd.DataFrame(got).sort_values("ts")
    os.makedirs(args.out, exist_ok=True)
    out.drop(columns=["ts"]).to_csv(os.path.join(args.out, "top_videos.csv"), index=False)
    size = sum(os.path.getsize(os.path.join(args.audio_root, "web", v)) for v in out.video_filename)
    print(f"Downloaded {len(out)} videos ({size / 1e6:.1f} MB) from {out.night.nunique()} nights "
          f"-> {args.audio_root}/videos, list in {args.out}/top_videos.csv")


if __name__ == "__main__":
    main()
