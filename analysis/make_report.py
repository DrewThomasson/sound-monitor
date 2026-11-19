#!/usr/bin/env python3
"""Build charts, summary.json, a nighttime evidence log and review.html.

  python make_report.py --db sound_events.db --out report --audio-root hf_cache \
      [--hf-repo drewThomasson/sound-monitor-data]   # adds monitoring-uptime per hour

Night defaults to 10 PM - 7 AM; change with --night-start / --night-end.
"""
import argparse
import html
import json
import os
import random
import sqlite3
from collections import Counter
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

LABELS = ["revving", "vehicle", "horn", "siren", "other"]
COLORS = {"revving": "#d1495b", "vehicle": "#edae49", "horn": "#00798c",
          "siren": "#30638e", "other": "#a3a3a3", "unclassified": "#dddddd"}
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load(db):
    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
    extra = ", label, p_siren, p_horn, p_revving, p_vehicle, top_classes" if "label" in cols else ""
    df = pd.read_sql(f"SELECT id, timestamp, duration, peak_db, avg_db, filename, video_filename{extra} FROM events", conn)
    if "label" not in df:
        df["label"] = None
    df["ts"] = pd.to_datetime(df["timestamp"], format="mixed")
    df["hour"] = df.ts.dt.hour
    df["dow"] = df.ts.dt.day_of_week
    df["date"] = df.ts.dt.date
    df["label"] = df["label"].fillna("unclassified")
    return df


def is_night(hour, start, end):
    return (hour >= start) | (hour < end)


def night_of(ts, end):
    """Events after midnight belong to the previous evening's night."""
    return (ts - pd.Timedelta(hours=end)).dt.date


def uptime_from_repo(repo):
    """Count 1-minute recordings per (date, hour) from the file list only (no downloads)."""
    from huggingface_hub import HfApi
    files = HfApi().list_repo_files(repo, repo_type="dataset")
    c = Counter()
    for f in files:
        b = os.path.basename(f)
        if f.startswith("recordings/") and b.endswith(".mp3") and not b.startswith("event_"):
            try:
                t = datetime.strptime(b[:15], "%Y%m%d_%H%M%S")
            except ValueError:
                continue
            c[(str(t.date()), t.hour)] += 1
    return c


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(os.path.join(out, name), dpi=160)
    plt.close(fig)


def charts(df, out, night_start, night_end):
    cl = df[df.label != "unclassified"]
    present = [l for l in LABELS if l in set(cl.label)]

    # 1. Hour of day, stacked by label (share of classified, scaled to all events)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    by = cl.groupby(["hour", "label"]).size().unstack(fill_value=0).reindex(range(24), fill_value=0)
    scale = len(df) / max(len(cl), 1)
    bottom = pd.Series(0.0, index=range(24))
    for l in present:
        ax.bar(by.index, by[l] * scale, bottom=bottom, color=COLORS[l], label=l)
        bottom += by[l] * scale
    ax.axvspan(-0.5, night_end - 0.5, color="#000", alpha=0.06)
    ax.axvspan(night_start - 0.5, 23.5, color="#000", alpha=0.06)
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{(h % 12) or 12}{'a' if h < 12 else 'p'}" for h in range(24)])
    ax.set_ylabel("Loud events (estimated)")
    ax.set_title("Loud events by hour of day (shaded = night)")
    ax.legend(ncol=5, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, out, "01_events_by_hour.png")

    rev = cl[cl.label == "revving"]
    if rev.empty:
        return

    # 2. Revving by hour
    fig, ax = plt.subplots(figsize=(10, 4))
    h = rev.groupby("hour").size().reindex(range(24), fill_value=0)
    ax.bar(h.index, h.values, color=[COLORS["revving"] if is_night(i, night_start, night_end) else "#e9a3ac"
                                     for i in h.index])
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{(i % 12) or 12}{'a' if i < 12 else 'p'}" for i in range(24)])
    ax.set_ylabel("Revving events (classified sample)")
    ax.set_title("Engine revving by hour of day (dark = night hours)")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, out, "02_revving_by_hour.png")

    # 3. Day-of-week x hour heatmap
    fig, ax = plt.subplots(figsize=(10, 3.6))
    m = rev.groupby(["dow", "hour"]).size().unstack(fill_value=0).reindex(index=range(7), columns=range(24),
                                                                           fill_value=0)
    im = ax.imshow(m.values, aspect="auto", cmap="Reds")
    ax.set_yticks(range(7))
    ax.set_yticklabels(DOW)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{(i % 12) or 12}{'a' if i < 12 else 'p'}" for i in range(0, 24, 2)])
    ax.set_title("When revving happens: day of week x hour")
    fig.colorbar(im, ax=ax, label="events")
    save(fig, out, "03_revving_heatmap.png")

    # 4. Night revving per night over time
    fig, ax = plt.subplots(figsize=(10, 4))
    nr = rev[is_night(rev.hour, night_start, night_end)]
    per = nr.groupby(night_of(nr.ts, night_end)).size()
    all_nights = pd.date_range(df.ts.min().normalize(), df.ts.max().normalize(), freq="D").date
    per = per.reindex(all_nights, fill_value=0)
    ax.bar(pd.to_datetime(per.index), per.values, color=COLORS["revving"], width=0.8)
    ax.set_ylabel("Night revving events")
    ax.set_title(f"Revving events per night ({night_start % 12 or 12}PM-{night_end}AM)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    save(fig, out, "04_night_revving_per_night.png")

    # 5. Loudness by label
    fig, ax = plt.subplots(figsize=(8, 4))
    data = [cl[cl.label == l].peak_db for l in present]
    ax.boxplot(data, tick_labels=present, showfliers=False)
    ax.set_ylabel("Peak level (dB, uncalibrated)")
    ax.set_title("How loud each type of event is")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, out, "05_loudness_by_label.png")


def review_html(df, out, audio_root, per_label=40, seed=0):
    cl = df[df.label != "unclassified"].copy()
    cl["path"] = cl.filename.map(lambda f: os.path.join(audio_root, f))
    cl = cl[cl.path.map(os.path.exists)]
    picks = []
    for l in LABELS:
        sub = cl[cl.label == l]
        picks.append(sub.sample(min(per_label, len(sub)), random_state=seed))
    # borderline: revving with any siren signal, and sirens just over the threshold
    border = cl[((cl.label == "revving") & (cl.p_siren > 0.03)) | ((cl.label == "siren") & (cl.p_siren < 0.3))]
    picks.append(border.assign(label=border.label + " (borderline)"))
    sel = pd.concat(picks).drop_duplicates("id", keep="last") if picks else cl.head(0)

    def video_tag(r):
        v = r.get("video_filename")
        vp = os.path.join(audio_root, "web", v) if isinstance(v, str) and v else None
        if not vp or not os.path.exists(vp):
            return ""
        vrel = os.path.relpath(os.path.abspath(vp), os.path.abspath(out))
        return f'<br><video controls preload="none" width="280" src="{html.escape(vrel)}"></video>'

    rows = []
    for _, r in sel.sort_values(["label", "ts"]).iterrows():
        rel = os.path.relpath(os.path.abspath(r.path), os.path.abspath(out))
        top = ", ".join(f"{n} {p:.2f}" for n, p in json.loads(r.top_classes or "[]")[:4])
        base = r.label.split(" ")[0]
        rows.append(
            f'<tr data-label="{html.escape(base)}"><td><span class="tag {html.escape(base)}">{html.escape(r.label)}</span></td>'
            f'<td>{r.ts:%a %b %d %I:%M:%S %p}</td><td>{r.peak_db:.1f}</td>'
            f'<td>{r.p_siren:.2f}</td><td>{r.p_revving:.2f}</td><td>{r.p_vehicle:.2f}</td>'
            f'<td class="top">{html.escape(top)}</td>'
            f'<td><audio controls preload="none" src="{html.escape(rel)}"></audio>{video_tag(r)}</td>'
            f'<td>#{r.id}</td></tr>')
    evidence = ""
    tv = os.path.join(out, "top_videos.csv")
    if os.path.exists(tv):
        cards = []
        for _, v in pd.read_csv(tv).iterrows():
            vid = os.path.relpath(os.path.abspath(os.path.join(audio_root, "web", v.video_filename)), os.path.abspath(out))
            aud = os.path.relpath(os.path.abspath(os.path.join(audio_root, v.filename)), os.path.abspath(out))
            t = pd.Timestamp(v.timestamp)
            cards.append(f'<div class="card"><video controls preload="metadata" src="{html.escape(vid)}"></video>'
                         f'<b>{t:%a %b %d, %I:%M %p}</b> &middot; {v.peak_db:.1f} dB &middot; #{v.id}'
                         f'<audio controls preload="none" src="{html.escape(aud)}"></audio></div>')
        evidence = ("<h2>Top nighttime revving events</h2><p>Loudest night revving events, at most 2 per night. "
                    "Each video has the event audio merged in; the separate audio player is the original clip.</p>"
                    f'<div class="grid">{"".join(cards)}</div><h2>All sampled clips</h2>')
    buttons = "".join(f'<button onclick="f(\'{l}\')">{l}</button>' for l in LABELS)
    page = f"""<!doctype html><meta charset="utf-8"><title>Sound event review</title>
<style>
body{{font:14px -apple-system,system-ui,sans-serif;margin:24px;color:#222;background:#fff}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:6px 8px;border-bottom:1px solid #eee;text-align:left;vertical-align:middle}}
th{{position:sticky;top:0;background:#fafafa}}.top{{color:#666;font-size:12px;max-width:360px}}
.tag{{padding:2px 8px;border-radius:10px;color:#fff;font-size:12px;white-space:nowrap}}
{''.join(f'.{l}{{background:{c}}}' for l, c in COLORS.items())}
button{{margin:0 6px 12px 0;padding:6px 12px;border:1px solid #ccc;border-radius:6px;background:#fff;cursor:pointer}}
audio{{height:32px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-bottom:24px}}
.card{{display:flex;flex-direction:column;gap:6px}}.card video{{width:100%;border-radius:6px;background:#000}}.card audio{{width:100%}}
</style>
<h1>Spot-check the labels</h1>
<p>Listen to a few clips per label. If you hear sirens labeled <b>revving</b>, note the <b>siren</b> score of those
rows and lower <code>SIREN_MIN</code> in <code>classify_events.py</code> to just below it, then run
<code>python classify_events.py --relabel</code> (fast, no re-download) and rebuild this report.
Rows marked "borderline" are the most likely mistakes.</p>
{evidence}
<button onclick="f('')">all ({len(sel)})</button>{buttons}
<table><tr><th>label</th><th>time</th><th>peak dB</th><th>siren</th><th>revving</th><th>vehicle</th>
<th>model's top guesses</th><th>clip</th><th>id</th></tr>
{''.join(rows)}</table>
<script>function f(l){{document.querySelectorAll('tr[data-label]').forEach(r=>r.style.display=(!l||r.dataset.label===l)?'':'none')}}</script>
"""
    with open(os.path.join(out, "review.html"), "w") as fh:
        fh.write(page)
    return len(sel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="sound_events.db")
    ap.add_argument("--out", default="report")
    ap.add_argument("--audio-root", default="hf_cache")
    ap.add_argument("--hf-repo", help="If given, count 1-minute recordings to measure monitoring uptime")
    ap.add_argument("--night-start", type=int, default=22)
    ap.add_argument("--night-end", type=int, default=7)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    df = load(args.db)
    ns, ne = args.night_start, args.night_end
    cl = df[df.label != "unclassified"]
    rev = cl[cl.label == "revving"]
    night_rev = rev[is_night(rev.hour, ns, ne)]
    n_days = (df.ts.max().normalize() - df.ts.min().normalize()).days + 1
    frac = len(cl) / len(df) if len(df) else 0

    s = {
        "date_range": [str(df.ts.min()), str(df.ts.max())],
        "days_covered": n_days,
        "total_loud_events": len(df),
        "events_per_day": round(len(df) / n_days, 1),
        "night_hours": f"{ns}:00-{ne}:00",
        "events_at_night_all_types": int(is_night(df.hour, ns, ne).sum()),
        "classified_events": len(cl),
        "classified_fraction": round(frac, 3),
        "label_counts_classified": cl.label.value_counts().to_dict(),
        "label_share_classified": (cl.label.value_counts(normalize=True).round(3)).to_dict(),
        "revving_classified": len(rev),
        "revving_at_night_classified": len(night_rev),
        "revving_night_share": round(len(night_rev) / len(rev), 3) if len(rev) else None,
        "sirens_excluded_classified": int((cl.label == "siren").sum()),
        "peak_db_note": "Levels are from an uncalibrated microphone; compare them to each other, not to legal dBA limits.",
    }
    s["events_without_clip"] = int(len(df) - len(cl))
    if frac and frac < 0.99:
        s["estimated_revving_total"] = round(len(rev) / frac)
        s["estimated_revving_at_night_total"] = round(len(night_rev) / frac)
        s["note"] = (f"Only {frac:.1%} of events are classified so far; 'estimated_*' figures scale the sample "
                     "up to all events.")
    if len(rev):
        s["revving_peak_db"] = {"median": round(rev.peak_db.median(), 1), "max": round(rev.peak_db.max(), 1)}
        s["revving_busiest_hours"] = {f"{h:02d}:00": int(c) for h, c in rev.hour.value_counts().head(5).items()}
        s["revving_by_weekday"] = {DOW[d]: int(rev.dow.eq(d).sum()) for d in range(7)}
        nights = night_rev.groupby(night_of(night_rev.ts, ne)).size().sort_values(ascending=False)
        s["worst_nights"] = {str(k): int(v) for k, v in nights.head(10).items()}
        s["nights_with_revving"] = int(len(nights))
        s["revving_midnight_to_5am"] = int((rev.hour < 5).sum())
        s["revving_on_fri_sat_nights"] = int(night_rev.ts.map(
            lambda t: (t - pd.Timedelta(hours=ne)).dayofweek in (4, 5)).sum())

    if args.hf_repo:
        up = uptime_from_repo(args.hf_repo)
        minutes = sum(up.values())
        s["monitoring_minutes_recorded"] = minutes
        s["monitoring_uptime_pct"] = round(100 * minutes / (n_days * 1440), 1)
        night_min = sum(v for (d, h), v in up.items() if is_night(h, ns, ne))
        if night_min and len(rev):
            s["revving_per_night_hour_est"] = round(
                s.get("estimated_revving_at_night_total", len(night_rev)) / (night_min / 60), 2)

    with open(os.path.join(args.out, "summary.json"), "w") as fh:
        json.dump(s, fh, indent=2, default=str)

    log = night_rev.sort_values("ts")[["id", "timestamp", "duration", "peak_db", "p_revving", "p_siren",
                                       "top_classes", "filename", "video_filename"]]
    log.to_csv(os.path.join(args.out, "night_log.csv"), index=False)

    charts(df, args.out, ns, ne)
    n = review_html(df, args.out, args.audio_root)
    print(json.dumps(s, indent=2, default=str))
    print(f"\nWrote {args.out}/: charts, summary.json, night_log.csv ({len(log)} rows), review.html ({n} clips)")


if __name__ == "__main__":
    main()
