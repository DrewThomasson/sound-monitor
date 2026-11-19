#!/usr/bin/env python3
"""Build a static web page of example events for each label, ready for a Hugging Face Space.

  python build_showcase.py --db sound_events.db --hf-repo drewThomasson/sound-monitor-data --out showcase

For each label it takes the --per-label most confident examples, plus the
nighttime revving events in report/top_videos.csv. Each example gets its audio
clip and its video re-encoded to H.264 with the audio merged in, so it plays in
any browser. Output: <out>/index.html, <out>/media/, <out>/README.md.
"""
import argparse
import html
import json
import os
import shutil
import sqlite3
import subprocess

import pandas as pd

from fetch_top_videos import to_web

LABELS = {
    "revving": ("Engine revving", "#d1495b", "p_revving",
                "Cars accelerating hard or revving in place. These are what the report counts."),
    "siren": ("Emergency sirens", "#30638e", "p_siren",
              "Police, ambulance and fire trucks. Checked first and excluded from revving counts."),
    "horn": ("Horns and car alarms", "#00798c", "p_horn", "Car horns, truck horns and car alarms."),
    "vehicle": ("Other vehicle noise", "#edae49", "p_vehicle",
                "Cars, trucks and buses passing without hard revving."),
    "other": ("Other sounds", "#8a8a8a", None, "Everything else loud enough to trigger the monitor."),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="sound_events.db")
    ap.add_argument("--hf-repo", required=True)
    ap.add_argument("--audio-root", default="hf_cache")
    ap.add_argument("--report", default="report")
    ap.add_argument("--out", default="showcase")
    ap.add_argument("--per-label", type=int, default=10)
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    df = pd.read_sql("SELECT id, timestamp, duration, peak_db, label, p_siren, p_horn, p_revving, p_vehicle, "
                     "top_classes, filename, video_filename FROM events WHERE label IS NOT NULL "
                     "AND video_filename != ''", con)
    df["ts"] = pd.to_datetime(df.timestamp, format="mixed")
    picks = []
    for lab, (_, _, score, _) in LABELS.items():
        sub = df[df.label == lab]
        if score:
            sub = sub.sort_values(score, ascending=False)
        else:  # "other": clips the model is most sure are not vehicles/sirens/horns
            sub = sub.assign(mx=sub[["p_siren", "p_horn", "p_revving", "p_vehicle"]].max(axis=1)).sort_values("mx")
        picks.append(sub.head(args.per_label).assign(section=lab))
    top = pd.read_csv(os.path.join(args.report, "top_videos.csv"))
    picks.append(df[df.id.isin(top.id)].assign(section="night"))
    sel = pd.concat(picks)

    from huggingface_hub import hf_hub_download
    media = os.path.join(args.out, "media")
    os.makedirs(media, exist_ok=True)
    items = []
    for _, r in sel.iterrows():
        mp4, mp3 = os.path.join(media, f"{r.id}.mp4"), os.path.join(media, f"{r.id}.mp3")
        try:
            web = os.path.join(args.audio_root, "web", r.video_filename)
            for f in ([r.filename] if os.path.exists(web) else [r.video_filename, r.filename]):
                if not os.path.exists(os.path.join(args.audio_root, f)):
                    hf_hub_download(args.hf_repo, f, repo_type="dataset", local_dir=args.audio_root)
            if not os.path.exists(web):
                to_web(args.audio_root, r.video_filename, r.filename)
            shutil.copy(web, mp4)
            shutil.copy(os.path.join(args.audio_root, r.filename), mp3)
        except Exception as e:
            print(f"  skipped #{r.id}: {e}")
            continue
        items.append(r)

    def card(r):
        top3 = ", ".join(f"{n} ({p:.0%})" for n, p in json.loads(r.top_classes)[:3])
        name, color = LABELS[r.label][:2]
        return (f'<article><video controls preload="metadata" playsinline src="media/{r.id}.mp4"></video>'
                f'<div class="meta"><span class="tag" style="background:{color}">{html.escape(name)}</span>'
                f'<b>{r.ts:%a %b %-d, %Y · %-I:%M %p}</b><span>{r.peak_db:.1f} dB peak · event #{r.id}</span>'
                f'<span class="guess">Model heard: {html.escape(top3)}</span>'
                f'<audio controls preload="none" src="media/{r.id}.mp3"></audio></div></article>')

    by = pd.DataFrame(items)
    sections = []
    night = by[by.section == "night"].sort_values("ts")
    sections.append(("night", "Loudest nighttime revving (10 PM – 7 AM)", "#d1495b",
                     "The loudest revving events at night, at most 2 per night.", night))
    for lab, (name, color, _, blurb) in LABELS.items():
        sections.append((lab, name, color, blurb, by[by.section == lab]))

    s = json.load(open(os.path.join(args.report, "summary.json")))
    counts = s["label_counts_classified"]
    nav = "".join(f'<a href="#{k}" style="--c:{c}">{html.escape(t.split(" (")[0])}</a>'
                  for k, t, c, _, d in sections if len(d))
    body = "".join(
        f'<section id="{k}"><h2 style="--c:{c}">{html.escape(t)}'
        f'{f" <small>{counts[k]:,} events total</small>" if k in counts else ""}</h2>'
        f'<p>{html.escape(b)}</p><div class="grid">{"".join(card(r) for _, r in d.iterrows())}</div></section>'
        for k, t, c, b, d in sections if len(d))

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Street Noise Examples</title>
<style>
:root{{--bg:#fafaf9;--fg:#1c1c1c;--muted:#666;--card:#fff;--line:#e6e6e3}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151515;--fg:#eee;--muted:#a0a0a0;--card:#1f1f1f;--line:#333}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:32px 16px 64px}}h1{{font-size:30px;margin:0 0 8px}}
.lead{{color:var(--muted);max-width:760px}}a{{color:inherit}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:24px 0}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}}
.stat b{{display:block;font-size:26px}}.stat span{{color:var(--muted);font-size:13px}}
nav{{position:sticky;top:0;background:var(--bg);padding:10px 0;display:flex;flex-wrap:wrap;gap:8px;z-index:1;border-bottom:1px solid var(--line)}}
nav a{{text-decoration:none;padding:6px 12px;border-radius:999px;border:1px solid var(--line);border-left:4px solid var(--c)}}
h2{{margin:40px 0 4px;padding-left:10px;border-left:5px solid var(--c)}}h2 small{{color:var(--muted);font-weight:400;font-size:14px}}
section>p{{color:var(--muted);margin:0 0 16px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}}
article{{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
video{{width:100%;aspect-ratio:16/9;background:#000;display:block}}
.meta{{padding:10px 12px;display:flex;flex-direction:column;gap:4px;font-size:13px}}.meta span{{color:var(--muted)}}
.tag{{align-self:flex-start;color:#fff!important;padding:1px 8px;border-radius:999px;font-size:12px}}
.guess{{font-size:12px}}audio{{width:100%;height:32px;margin-top:4px}}
footer{{margin-top:48px;color:var(--muted);font-size:13px}}
</style></head><body><main>
<h1>What the street sounds like at night</h1>
<p class="lead">Examples from two months of round-the-clock sound monitoring on a residential street in Atlanta.
Every loud sound was recorded and then labeled automatically by an AI audio model, so emergency sirens could be
separated from cars revving their engines. Play a few from each group to hear how the labels hold up.
Each video includes the recorded sound.</p>
<div class="stats">
<div class="stat"><b>{s['total_loud_events']:,}</b><span>loud events in {s['days_covered']} days</span></div>
<div class="stat"><b>{s['revving_classified']:,}</b><span>engine revving events</span></div>
<div class="stat"><b>{s['revving_at_night_classified']:,}</b><span>revving between 10 PM and 7 AM</span></div>
<div class="stat"><b>{s['sirens_excluded_classified']:,}</b><span>sirens excluded from revving</span></div>
<div class="stat"><b>{s['monitoring_uptime_pct']}%</b><span>of the time the monitor was recording</span></div>
</div>
<nav>{nav}</nav>
{body}
<footer>Data, charts and method:
<a href="https://huggingface.co/datasets/{args.hf_repo}">huggingface.co/datasets/{args.hf_repo}</a>.
Decibel values are uncalibrated and labels are an AI model's best guess, so expect occasional mistakes.
Examples per group are the clips the model was most confident about.</footer>
</main></body></html>"""
    with open(os.path.join(args.out, "index.html"), "w") as fh:
        fh.write(page)
    with open(os.path.join(args.out, "README.md"), "w") as fh:
        fh.write(f"""---
title: Street Noise Examples
emoji: 🚗
colorFrom: red
colorTo: gray
sdk: static
pinned: false
---

Playable examples of each kind of loud event from the
[sound-monitor-data](https://huggingface.co/datasets/{args.hf_repo}) dataset.
""")
    size = sum(os.path.getsize(os.path.join(media, f)) for f in os.listdir(media))
    print(f"{len(by)} examples, media {size / 1e6:.1f} MB ->", dict(by.section.value_counts()))


if __name__ == "__main__":
    main()
