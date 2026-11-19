---
pretty_name: Residential Street Noise Monitor (Atlanta) – 5th-floor porch
tags:
  - audio
  - video
  - noise
  - noise-pollution
  - urban-sound
  - vehicles
task_categories:
  - audio-classification
---

# Residential Street Noise Monitor (Atlanta) – 5th-floor porch

The second recording site for documenting **cars loudly revving their engines near a residential
street in Atlanta, GA, especially late at night**.

The first site recorded from street level at the intersection from Nov 2025 to Jan 2026. Its data and
analysis are in **[drewThomasson/sound-monitor-data](https://huggingface.co/datasets/drewThomasson/sound-monitor-data)**.
This site records from a 5th-floor porch of the neighboring building, starting November 2026.

Because the location, height and microphone are different, **don't add the two sites' counts together**.
Compare patterns instead: time of day, weekends and late nights.

## How it's recorded

An Amazon Fire 7 tablet runs a purpose-built recorder app
([source](https://github.com/DrewThomasson/sound-monitor)) around the clock:

- It listens continuously and logs a **loud event** whenever the sound rises a set amount above the
  street's normal background level. The trigger adapts to the spot instead of using a fixed level.
- Each event is saved as a short **video with sound** (H.264/AAC, plays in any browser), starting 2 seconds
  before the noise.
- The **sound level is logged every second**, so it's always clear when the recorder was running.
- Everything uploads automatically twice a day.

Events are labeled afterwards (revving / vehicle / siren / horn / other) with the same AudioSet model used
for the first site, so emergency sirens can be excluded.

## Layout

```
sites/<site>/events/events_<upload time>.csv     events in each upload
sites/<site>/videos/<date>/event_<time>.mp4      video + sound of each event
sites/<site>/recordings/<date>/event_<time>.m4a  audio only (only if video was off)
sites/<site>/levels/<date>.csv                   sound level every second
sites/<site>/status.json                         recorder health at the last upload
```

Event CSV columns: `timestamp` (local Eastern time), `duration` (s), `peak_db`, `avg_db`, `background_db`,
`filename`, `video_filename`, `low_frequency`, `wind_suspected`, `site`, `calibration_db`.

## Limitations

- Decibel values are uncalibrated unless `calibration_db` is non-zero. Use them to compare events with each
  other, not with legal dBA limits.
- `wind_suspected` events are kept but flagged; wind on an outdoor microphone can look like a loud event.
- Labels are an AI model's best guess.

## Privacy

The recordings capture a public street. Clips may include passing voices, faces or license plates.
Please don't use this data to identify individuals.
