#!/usr/bin/env python3
"""Label each sound event clip as revving / vehicle / siren / horn / other.

Uses the AudioSet-trained Audio Spectrogram Transformer (AST) to score each
event clip, then applies the thresholds below. Results are written back into
the `events` table of sound_events.db (new columns are added if missing).

Examples
  # test on 300 random unclassified clips, keep clips for review.html
  python classify_events.py --db sound_events.db --hf-repo drewThomasson/sound-monitor-data --limit 300

  # process everything else in batches, deleting clips after each batch
  python classify_events.py --db sound_events.db --hf-repo drewThomasson/sound-monitor-data \
      --limit 0 --batch-size 500 --delete-after
"""

# ---------------------------------------------------------------------------
# THRESHOLDS: tune these after listening in review.html
# Scores are the model's per-class probability (0-1) for each group, using the
# highest-scoring AudioSet class in that group. Labels are checked in this
# order, so a clip that clears SIREN_MIN is a siren even if it also revs.
# ---------------------------------------------------------------------------
SIREN_MIN = 0.15    # lower = more aggressive about excluding emergency vehicles
HORN_MIN = 0.30
REVVING_MIN = 0.20  # "Accelerating, revving, vroom" / racing / motorcycle
VEHICLE_MIN = 0.20  # any other engine/car/truck noise
# A clip is revving if REVVING_MIN is met, OR if engine noise is strong and
# the revving score is at least this fraction of it (catches loud engines the
# model calls "Engine"/"Car" rather than "revving").
REVVING_RELATIVE = 0.5
MODEL_ID = "MIT/ast-finetuned-audioset-10-10-0.4593"
# ---------------------------------------------------------------------------

GROUPS = {
    "siren": ["Siren", "Police car (siren)", "Ambulance (siren)",
              "Fire engine, fire truck (siren)", "Civil defense siren",
              "Emergency vehicle"],
    "horn": ["Vehicle horn, car horn, honking", "Car alarm", "Air horn, truck horn",
             "Toot"],
    "revving": ["Accelerating, revving, vroom", "Race car, auto racing",
                "Motorcycle", "Skidding", "Tire squeal"],
    "vehicle": ["Vehicle", "Car", "Engine", "Motor vehicle (road)",
                "Car passing by", "Truck", "Bus", "Idling", "Engine starting",
                "Medium engine (mid frequency)", "Heavy engine (low frequency)",
                "Light engine (high frequency)", "Traffic noise, roadway noise"],
}

import argparse
import json
import os
import random
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor

NEW_COLUMNS = {
    "label": "TEXT",
    "p_siren": "REAL",
    "p_horn": "REAL",
    "p_revving": "REAL",
    "p_vehicle": "REAL",
    "top_classes": "TEXT",
    "classified_at": "TEXT",
}


def ensure_columns(conn):
    have = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
    for col, typ in NEW_COLUMNS.items():
        if col not in have:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} {typ}")
    conn.commit()


def decide(p):
    """Turn group scores into a single label using the thresholds above."""
    if p["siren"] >= SIREN_MIN:
        return "siren"
    if p["horn"] >= HORN_MIN:
        return "horn"
    if p["revving"] >= REVVING_MIN:
        return "revving"
    if p["vehicle"] >= VEHICLE_MIN and p["revving"] >= REVVING_RELATIVE * p["vehicle"]:
        return "revving"
    if p["vehicle"] >= VEHICLE_MIN:
        return "vehicle"
    return "other"


def relabel_only(conn):
    """Re-apply thresholds to stored scores without re-running the model."""
    rows = conn.execute("SELECT id, p_siren, p_horn, p_revving, p_vehicle FROM events "
                        "WHERE p_siren IS NOT NULL").fetchall()
    for rid, s, h, r, v in rows:
        conn.execute("UPDATE events SET label=? WHERE id=?",
                     (decide({"siren": s, "horn": h, "revving": r, "vehicle": v}), rid))
    conn.commit()
    print(f"Relabeled {len(rows)} events with current thresholds.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="sound_events.db")
    ap.add_argument("--hf-repo", help="Hugging Face dataset to fetch clips from (only event_*.mp3 are fetched)")
    ap.add_argument("--audio-root", default="hf_cache", help="Where clips live / are downloaded to")
    ap.add_argument("--limit", type=int, default=300, help="Max events to classify this run (0 = all remaining)")
    ap.add_argument("--batch-size", type=int, default=500, help="Clips downloaded per batch")
    ap.add_argument("--delete-after", action="store_true", help="Delete each batch's clips once classified")
    ap.add_argument("--reclassify", action="store_true", help="Also redo events that already have scores")
    ap.add_argument("--relabel", action="store_true", help="Only re-apply thresholds to stored scores (fast, no model)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    ensure_columns(conn)
    if args.relabel:
        relabel_only(conn)
        return

    where = "" if args.reclassify else "WHERE p_siren IS NULL"
    rows = conn.execute(f"SELECT id, filename FROM events {where}").fetchall()
    rows = [r for r in rows if r[1] and os.path.basename(r[1]).startswith("event_")]
    random.Random(args.seed).shuffle(rows)  # random sample so a test run spans all dates
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        print("Nothing to classify.")
        return
    print(f"Classifying {len(rows)} events")

    import librosa
    import numpy as np
    import torch
    from transformers import ASTFeatureExtractor, ASTForAudioClassification

    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    fx = ASTFeatureExtractor.from_pretrained(MODEL_ID)
    model = ASTForAudioClassification.from_pretrained(MODEL_ID).to(device).eval()
    id2label = model.config.id2label
    label2id = {v: k for k, v in id2label.items()}
    group_idx = {}
    for g, names in GROUPS.items():
        missing = [n for n in names if n not in label2id]
        if missing:
            print(f"  note: not in model vocabulary, skipped: {missing}")
        group_idx[g] = [label2id[n] for n in names if n in label2id]

    def fetch(rel):
        local = os.path.join(args.audio_root, rel)
        if os.path.exists(local):
            return local
        if not args.hf_repo:
            return None
        from huggingface_hub import hf_hub_download
        for attempt in range(4):
            try:
                return hf_hub_download(args.hf_repo, rel, repo_type="dataset", local_dir=args.audio_root)
            except Exception as e:  # rate limits / transient network errors
                if attempt == 3:
                    print(f"  download failed {rel}: {e}")
                    return None
                time.sleep(2 ** attempt * 3)

    done = 0
    t0 = time.time()
    for b in range(0, len(rows), args.batch_size):
        batch = rows[b:b + args.batch_size]
        with ThreadPoolExecutor(8) as pool:
            paths = list(pool.map(lambda r: fetch(r[1]), batch))

        results = []
        mini = 16
        items = [(r, p) for r, p in zip(batch, paths) if p]
        for i in range(0, len(items), mini):
            chunk = items[i:i + mini]
            waves, ok = [], []
            for (rid, rel), p in chunk:
                try:
                    y, _ = librosa.load(p, sr=16000, mono=True)
                    if len(y) < 1600:
                        y = np.pad(y, (0, 1600 - len(y)))
                    waves.append(y)
                    ok.append((rid, rel))
                except Exception as e:
                    print(f"  could not decode {rel}: {e}")
            if not waves:
                continue
            feats = fx(waves, sampling_rate=16000, return_tensors="pt").to(device)
            with torch.no_grad():
                probs = torch.sigmoid(model(**feats).logits).cpu().numpy()
            for (rid, rel), pr in zip(ok, probs):
                p = {g: float(pr[idx].max()) if idx else 0.0 for g, idx in group_idx.items()}
                top = np.argsort(pr)[::-1][:5]
                top_classes = [[id2label[int(k)], round(float(pr[k]), 3)] for k in top]
                results.append((decide(p), p["siren"], p["horn"], p["revving"], p["vehicle"],
                                json.dumps(top_classes), time.strftime("%Y-%m-%d %H:%M:%S"), rid))

        conn.executemany("UPDATE events SET label=?, p_siren=?, p_horn=?, p_revving=?, p_vehicle=?, "
                         "top_classes=?, classified_at=? WHERE id=?", results)
        conn.commit()

        if args.delete_after:
            for p in paths:
                if p and os.path.exists(p):
                    os.remove(p)
            # clear empty date folders and the HF download metadata
            for root, dirs, files in os.walk(args.audio_root, topdown=False):
                for d in dirs:
                    full = os.path.join(root, d)
                    if not os.listdir(full):
                        os.rmdir(full)

        done += len(batch)
        rate = done / (time.time() - t0)
        left = (len(rows) - done) / rate if rate else 0
        print(f"  {done}/{len(rows)} done ({len(results)} labeled this batch), ~{left/60:.0f} min left", flush=True)

    counts = conn.execute("SELECT label, COUNT(*) FROM events WHERE label IS NOT NULL GROUP BY label "
                          "ORDER BY 2 DESC").fetchall()
    print("Labels so far:", dict(counts))


if __name__ == "__main__":
    sys.exit(main())
