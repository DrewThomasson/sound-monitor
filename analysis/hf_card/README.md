---
pretty_name: Residential Street Noise Monitor (Atlanta)
tags:
  - audio
  - noise
  - noise-pollution
  - urban-sound
  - vehicles
task_categories:
  - audio-classification
size_categories:
  - 100K<n<1M
---

# Residential Street Noise Monitor (Atlanta)

Two months of continuous sound monitoring from an apartment on a residential street in Atlanta, GA,
collected to document **cars loudly revving their engines, especially late at night**.

Recorded with [sound-monitor](https://github.com/DrewThomasson/sound-monitor), an open-source app
that records audio around the clock and logs every sound that crosses a loudness threshold as an
"event", saving a short audio clip and a video of each one.

| | |
|---|---|
| **Period** | Nov 10, 2025 – Jan 13, 2026 (65 days) |
| **Monitoring uptime** | 95.5% (89,400 one-minute recordings) |
| **Loud events logged** | 11,291 (about 174 per day) |
| **Engine revving events** | **1,782**, with sirens excluded |
| **Revving at night (10 PM – 7 AM)** | **544**, on 63 of 65 nights |
| **Revving between midnight and 5 AM** | 270 |

## Key findings

**Revving happens almost every night, and weekends are much worse.**
Saturdays had 420 revving events, compared with 150 on Mondays. Friday and Saturday nights account
for 282 of the 544 nighttime events.

| Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|
| 150 | 188 | 250 | 222 | 248 | **420** | 304 |

**The worst nights** were Sat Nov 22 (33 revving events), Sat Dec 13 (31), Sat Jan 10 (29),
Fri Nov 21 (23), New Year's Eve (22) and Fri Dec 5 (22).

**The busiest hours** are 7–11 PM, with a second cluster from midnight to 4 AM on Saturday nights.

### Patterns

- **Friday and Saturday nights average 15.7 revving events, about 3 times the 5.6 on other nights.**
- **Saturday nights run late.** Early Sunday morning (midnight – 4 AM) had 95 revving events,
  compared with about 19 for the same hours on an average weekday.
- **Revving makes up a larger share of the noise at night:** 19% of loud events at night, 15% during the day.
- **It comes in bursts.** A third of revving events (603 of 1,782) came within 5 minutes of another one,
  which suggests the same driver making repeated passes or revving in place. The longest burst
  was 9 events in 4 minutes (Dec 27, 6:22 PM), and the longest at night was 7 events in 10 minutes
  (Sat Jan 10, 10:13 PM).
- **It's steady, not a one-off.** Revving averaged 25–30 events per day in each of November,
  December and January.
- **The only full night with no revving was Thanksgiving Eve** (Nov 26). The monitor was running
  the whole night and logged 62 other loud events.
- For comparison, the monitor heard about 10 emergency sirens per day. Those are counted separately
  and excluded from all revving numbers.

![When revving happens: day of week by hour](analysis/03_revving_heatmap.png)

![Revving events per night](analysis/04_night_revving_per_night.png)

![Engine revving by hour of day](analysis/02_revving_by_hour.png)

![All loud events by hour and type](analysis/01_events_by_hour.png)

### What the loud events were

| Type | Events | Share |
|---|---|---|
| Vehicle noise (other than revving) | 6,491 | 57.7% |
| Other sounds | 2,199 | 19.5% |
| **Engine revving** | **1,782** | **15.8%** |
| Emergency sirens (excluded from revving) | 669 | 5.9% |
| Horns and car alarms | 108 | 1.0% |

![Loudness by event type](analysis/05_loudness_by_label.png)

## How events were labeled

Each event clip was scored with the
[Audio Spectrogram Transformer](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593)
trained on Google's AudioSet. Its 527 sound classes were grouped, and each clip got one label,
checked in this order:

1. **Siren**: police, ambulance, fire truck, civil defense siren or emergency vehicle (score of at least 0.15).
   Sirens come first, so emergency vehicles never count as revving.
2. **Horn**: car horn, truck horn or car alarm (score of at least 0.30).
3. **Revving**: "Accelerating, revving, vroom", racing, motorcycle, skidding or tire squeal
   (score of at least 0.20), or strong engine noise where the revving score is at least half the engine score.
4. **Vehicle**: any other car, truck, bus or engine sound (score of at least 0.20).
5. **Other**: everything else.

A random sample of the labels was spot-checked by ear before the full run.

## Limitations

- **The decibel values are not calibrated.** They come from a consumer microphone and are useful for
  comparing events with each other, not for comparing against legal dBA limits.
- **The labels are a model's best guess.** Not every clip was checked by hand, so expect some
  mistakes in every category.
- **42 events have no audio clip** in this dataset, so they are unlabeled.
- Night is defined here as 10 PM – 7 AM.

## Dataset layout

```
sound_events.db                                  SQLite log of every event
recordings/YYYY-MM-DD/YYYYMMDD_HHMMSS.mp3        continuous 1-minute recordings
recordings/YYYY-MM-DD/event_<timestamp>.mp3      audio clip of each loud event
videos/YYYY-MM-DD/event_<timestamp>.mp4          video of each loud event (no audio track)
analysis/                                        the charts on this page
```

`sound_events.db` has one table, `events`:

| Column | Meaning |
|---|---|
| `id` | event number |
| `timestamp` | start time, local (Eastern) time |
| `duration` | seconds |
| `peak_db`, `avg_db` | peak and average level (uncalibrated) |
| `low_frequency` | whether the event was dominated by low frequencies |
| `filename` | path to the event's audio clip |
| `video_filename` | path to the event's video |

To fetch only the database and event clips, without the 43 GB of continuous recordings:

```python
from huggingface_hub import snapshot_download
snapshot_download("drewThomasson/sound-monitor-data", repo_type="dataset",
                  allow_patterns=["sound_events.db", "recordings/*/event_*.mp3"])
```

## Privacy

The recordings capture a public street. Clips and videos may include passing voices, faces or
license plates. Please don't use this data to identify individuals.
