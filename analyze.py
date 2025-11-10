#!/usr/bin/env python3
"""
Sound Monitor Analysis Tool

Analyzes the CSV log file and generates summary statistics and reports
for presenting to city councils or noise enforcement.
"""

import csv
import sys
from datetime import datetime
from collections import defaultdict, Counter


def analyze_log(csv_file='sound_events.csv'):
    """Analyze the sound events log file."""
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            events = list(reader)
    except FileNotFoundError:
        print(f"Error: {csv_file} not found. Run sound_monitor.py first to collect data.")
        return
    
    if not events:
        print("No events recorded yet.")
        return
    
    print("=" * 70)
    print("SOUND MONITOR - ANALYSIS REPORT")
    print("=" * 70)
    print()
    
    # Basic statistics
    total_events = len(events)
    peak_levels = [float(e['Peak dB']) for e in events]
    avg_levels = [float(e['Average dB']) for e in events]
    
    print(f"📊 SUMMARY STATISTICS")
    print(f"   Total Events: {total_events}")
    print(f"   Highest Peak: {max(peak_levels):.2f} dB")
    print(f"   Lowest Peak: {min(peak_levels):.2f} dB")
    print(f"   Average Peak: {sum(peak_levels)/len(peak_levels):.2f} dB")
    print(f"   Average Overall: {sum(avg_levels)/len(avg_levels):.2f} dB")
    print()
    
    # Events by day of week
    print(f"📅 EVENTS BY DAY OF WEEK")
    day_counts = Counter(e['Day of Week'] for e in events)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in day_order:
        count = day_counts.get(day, 0)
        bar = '█' * count
        print(f"   {day:10s}: {count:3d} {bar}")
    print()
    
    # Events by hour of day
    print(f"🕐 EVENTS BY HOUR OF DAY")
    hour_counts = defaultdict(int)
    for event in events:
        time_str = event['Time']
        hour = int(time_str.split(':')[0])
        hour_counts[hour] += 1
    
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        bar = '█' * count
        print(f"   {hour:02d}:00 - {hour:02d}:59: {count:3d} {bar}")
    print()
    
    # Peak noise times
    print(f"🔊 TOP 10 LOUDEST EVENTS")
    sorted_events = sorted(events, key=lambda x: float(x['Peak dB']), reverse=True)[:10]
    for i, event in enumerate(sorted_events, 1):
        print(f"   {i:2d}. {event['Date']} {event['Time']} ({event['Day of Week'][:3]})")
        print(f"       Peak: {event['Peak dB']} dB - {event['Recording File']}")
    print()
    
    # Late night events (11 PM - 6 AM)
    print(f"🌙 LATE NIGHT EVENTS (11 PM - 6 AM)")
    late_night = []
    for event in events:
        hour = int(event['Time'].split(':')[0])
        if hour >= 23 or hour < 6:
            late_night.append(event)
    
    if late_night:
        print(f"   Total late night events: {len(late_night)}")
        print(f"   Percentage of all events: {len(late_night)/total_events*100:.1f}%")
        print()
        print(f"   Latest night events:")
        for event in sorted(late_night, key=lambda x: float(x['Peak dB']), reverse=True)[:5]:
            print(f"   • {event['Date']} {event['Time']} - {event['Peak dB']} dB")
    else:
        print(f"   No late night events recorded.")
    print()
    
    # Very loud events (> 80 dB)
    print(f"⚠️  VERY LOUD EVENTS (> 80 dB)")
    very_loud = [e for e in events if float(e['Peak dB']) > 80]
    if very_loud:
        print(f"   Count: {len(very_loud)}")
        for event in very_loud[:10]:
            print(f"   • {event['Date']} {event['Time']} - {event['Peak dB']} dB - {event['Day of Week']}")
    else:
        print(f"   No events above 80 dB recorded.")
    print()
    
    # Date range
    dates = [event['Date'] for event in events]
    print(f"📆 MONITORING PERIOD")
    print(f"   First event: {min(dates)}")
    print(f"   Last event: {max(dates)}")
    print(f"   Date range: {(datetime.strptime(max(dates), '%Y-%m-%d') - datetime.strptime(min(dates), '%Y-%m-%d')).days + 1} days")
    print()
    
    print("=" * 70)
    print("To present this data:")
    print("1. Open sound_events.csv in Excel/Google Sheets/LibreOffice")
    print("2. Create charts showing events over time")
    print("3. Include audio samples from the recordings/ directory")
    print("4. Highlight late night and weekend patterns")
    print("=" * 70)


def main():
    """Main entry point."""
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'sound_events.csv'
    analyze_log(csv_file)


if __name__ == '__main__':
    main()
