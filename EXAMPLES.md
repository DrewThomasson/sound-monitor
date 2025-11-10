# Usage Examples - Sound Monitor

Real-world usage scenarios and examples for the Sound Monitor application.

## Scenario 1: Documenting Late-Night Traffic Noise

**Problem:** Loud cars and motorcycles speeding through residential area at night.

**Setup:**
1. Position laptop with external USB microphone near bedroom window
2. Set threshold to 75 dB (above normal night ambient)
3. Enable low-frequency detection for rumbling engines
4. Start recording at 10 PM, let run until 6 AM

**What to Monitor:**
- Events in Event Log tab filtered by time range
- Low-frequency column to identify rumbling vehicles
- Peak dB levels to show severity

**For City Council:**
```python
# Export data with filter
# In Event Log tab:
# - Filter: Peak dB >= 75
# - Export to CSV
# - Include dates: Nov 1-30, 2024
# - Time range: 10 PM - 6 AM

Results might show:
- 247 events over 30 days
- Average: 8.2 events per night
- Peak: 98.3 dB at 2:47 AM
- 65% low-frequency (vehicles)
```

**Presentation Points:**
- "Our data shows an average of 8 loud noise events per night"
- "Peak noise reached 98 dB - equivalent to a motorcycle"
- "65% of events are low-frequency vehicle noise"
- Play 3-5 worst examples during presentation

---

## Scenario 2: Construction Site Monitoring

**Problem:** Construction site creating excessive noise during prohibited hours.

**Setup:**
1. Place monitoring station in affected home/office
2. Set threshold to 80 dB (construction equipment level)
3. Monitor during prohibited hours (7 PM - 7 AM)
4. Run for 2-4 weeks

**Analysis:**
```python
# In Statistics tab:
# Total Events: 156
# During prohibited hours (7PM-7AM): 23
# Peak dB: 94.2
# Average event duration: 3.2 minutes

# In Event Log:
# Sort by timestamp
# Filter by time range
# Export violations
```

**Evidence Collection:**
- Screenshots of event log showing prohibited times
- Audio files of worst violations
- CSV export for official documentation
- Statistics showing frequency and severity

---

## Scenario 3: Neighbor Noise Complaints

**Problem:** Documenting ongoing neighbor disturbances for landlord/authorities.

**Setup:**
1. Run continuously in apartment
2. Set threshold to 70 dB (conversation level)
3. Calibrate for accurate readings
4. Keep detailed notes of each event

**Tracking:**
```python
# Create a supplementary log
Event 1: 2024-11-10 22:15 - Loud music, 87 dB
Event 2: 2024-11-10 23:42 - Shouting, 82 dB
Event 3: 2024-11-11 01:15 - Bass thumping, 79 dB

# Cross-reference with Sound Monitor events
# Export events from those time ranges
# Play recordings to verify
```

**Documentation Package:**
1. CSV export of all events
2. Statistical summary
3. 5-10 audio samples
4. Written incident log with timestamps
5. Screenshots of event table

---

## Scenario 4: Outdoor Event Monitoring

**Problem:** Regular outdoor events creating noise pollution.

**Setup:**
1. Laptop with good battery (or power adapter)
2. Weather-protected microphone placement
3. Set threshold to 85 dB
4. Monitor during event hours

**Advanced Analysis:**
```python
# Compare event-day vs non-event-day

Event Days (Fridays):
- Average events: 45
- Peak dB: 102.3
- Duration: 6 hours (8 PM - 2 AM)

Non-Event Days:
- Average events: 3
- Peak dB: 81.2
- Duration: Sporadic

# Export both datasets separately
# Create comparison chart
```

**Presentation:**
- Side-by-side statistics
- Audio examples from event nights
- Show health impact (sleep disruption data)
- Propose reasonable noise limits

---

## Scenario 5: Airport/Train Noise Study

**Problem:** Long-term study of transportation noise impact.

**Setup:**
1. Continuous monitoring for 90+ days
2. Multiple threshold levels (75, 85, 95 dB)
3. Low-frequency detection enabled
4. Regular data exports (weekly)

**Data Collection:**
```python
# Weekly exports
Week 1: 234 events, peak 96.2 dB
Week 2: 189 events, peak 94.8 dB
Week 3: 267 events, peak 99.1 dB
...

# Analyze patterns:
# - Time of day distribution
# - Day of week patterns
# - Seasonal variations
# - Event frequency trends
```

**Long-term Analysis:**
1. Track trends over time
2. Correlate with flight/train schedules
3. Identify peak times and days
4. Build comprehensive dataset

---

## Tips for Different Scenarios

### Legal/Official Use
- Calibrate microphone with certified meter
- Keep detailed written logs
- Backup data regularly
- Document setup and methodology
- Take photos of setup

### Continuous Monitoring
- Check storage weekly
- Export data regularly
- Monitor system status (battery, CPU)
- Verify recording is active
- Keep spare equipment ready

### Evidence Presentation
- Select worst 5-10 examples
- Create summary statistics
- Include date ranges clearly
- Export professional CSV reports
- Have audio files ready to play

### Personal Documentation
- Set appropriate thresholds
- Filter out false positives
- Keep event log updated
- Note unusual events
- Archive old recordings

---

## Sample Workflows

### Quick Check (1 hour)
```
1. Launch application
2. Start recording
3. Monitor live for 1 hour
4. Review Event Log
5. Play interesting events
6. Export if needed
```

### Overnight Monitoring
```
1. Start recording at bedtime
2. Let run 8-10 hours
3. Review in morning
4. Filter by time range
5. Note significant events
6. Continue for multiple nights
```

### Weekly Documentation
```
1. Start Monday morning
2. Run continuously 7 days
3. Check daily for issues
4. Export on Sunday
5. Review statistics
6. Prepare summary
```

### Month-Long Study
```
1. Set up permanent monitoring station
2. Run continuously
3. Export weekly
4. Track trends
5. Build comprehensive dataset
6. Prepare final report
```

---

## Export Templates

### For City Council
**Filename:** `NoiseReport_YYYYMM.csv`
**Include:** All events above threshold, sorted by peak dB
**Supplement:** Statistics summary, audio samples, photos

### For Landlord/Management
**Filename:** `NoiseComplaint_AptXXX_YYYYMM.csv`
**Include:** Events during quiet hours, written log
**Supplement:** Relevant audio files, lease references

### For Legal Documentation
**Filename:** `NoiseEvidence_CaseXXX_YYYYMMDD.csv`
**Include:** All data for date range
**Supplement:** Setup documentation, calibration proof, chain of custody

### For Health/Environmental Study
**Filename:** `NoiseStudy_LocationXXX_YYYYMM.csv`
**Include:** Full dataset with metadata
**Supplement:** Methodology, statistical analysis, visualizations

---

## Common Threshold Settings

| Noise Source | Typical dB | Recommended Threshold |
|--------------|-----------|---------------------|
| Quiet office | 40-50 | 55-60 |
| Normal conversation | 60-65 | 70-75 |
| Traffic noise | 70-80 | 75-85 |
| Loud music | 85-95 | 80-90 |
| Construction | 90-100 | 85-95 |
| Emergency siren | 100-110 | 95-100 |

Adjust based on your ambient noise level and what you consider "loud."

---

## Troubleshooting Common Issues

**Too many events logged:**
- Increase threshold by 5-10 dB
- Check for nearby constant noise sources
- Verify microphone placement

**Too few events:**
- Decrease threshold
- Check microphone is working
- Verify device selection
- Test with clapping or music

**Storage filling up:**
- Export and archive old data
- Delete unnecessary recordings
- Compress archive files
- Add external storage

---

**Remember:** The goal is to collect objective, verifiable evidence to support your case. Be consistent, thorough, and professional in your documentation.
