# Wind Noise Guide

## Understanding Wind Noise in Sound Monitoring

Wind noise is one of the most common challenges in outdoor sound monitoring. This guide explains how wind noise affects your recordings and how to use the built-in wind noise filter to minimize false alarms.

## What is Wind Noise?

Wind noise occurs when air movement hits the microphone, creating turbulent pressure fluctuations. These fluctuations are picked up by the microphone as sound, even though they're not the noise pollution you're trying to monitor.

### Characteristics of Wind Noise:

1. **Low Frequency**: Wind noise primarily appears in very low frequencies (10-80 Hz)
2. **Broadband**: Spreads across a wide frequency range but strongest at low frequencies
3. **Random**: Non-periodic, unpredictable fluctuations
4. **Loud**: Can register as high dB levels, triggering false alarms
5. **Continuous**: Often present throughout outdoor recordings

### How Wind Noise Affects Monitoring:

- **False Alarms**: Wind gusts can exceed your detection threshold, logging non-pollution events
- **Masking**: Legitimate noise pollution may be harder to distinguish from wind
- **Storage Waste**: Recording wind events fills up storage with irrelevant data
- **Data Pollution**: Analytics become less meaningful with many wind-triggered events

## The Wind Noise Filter

Sound Monitor includes a high-pass filter specifically designed to reduce wind noise interference.

### How It Works:

The wind filter uses a **Butterworth high-pass filter** that:
1. Removes frequencies below a configurable cutoff (default: 80 Hz)
2. Preserves frequencies above the cutoff (where most noise pollution occurs)
3. Applies zero-phase filtering to maintain audio quality
4. Operates in real-time during recording

### Technical Details:

- **Algorithm**: 4th-order Butterworth high-pass filter
- **Implementation**: scipy.signal.butter + filtfilt
- **Phase Response**: Zero-phase (no delay)
- **Processing**: Applied to each audio chunk before analysis
- **Performance**: ~5-10% CPU overhead
- **Fallback**: Returns original audio if filtering fails

## Using the Wind Filter

### Enabling the Filter:

1. Open the **Settings** tab
2. Scroll to the **"🌬️ Wind Noise Filter"** section
3. Check **"Enable Wind Noise Filter"**
4. The filter is now active on all incoming audio

### Choosing a Cutoff Frequency:

The cutoff frequency determines which frequencies are removed:

#### **60 Hz (Aggressive)**
- **Best for**: Very windy conditions, coastal areas, open fields
- **Removes**: More low-frequency content
- **Trade-off**: May miss very low-frequency pollution (distant heavy vehicles)
- **Use when**: False alarms from wind are frequent

#### **80 Hz (Default/Balanced)**
- **Best for**: General outdoor monitoring, suburban areas
- **Removes**: Typical wind noise while preserving most pollution
- **Trade-off**: Good balance between wind reduction and sensitivity
- **Use when**: Moderate wind conditions

#### **100 Hz (Conservative)**
- **Best for**: Light wind conditions, sheltered locations
- **Removes**: Only the lowest wind components
- **Trade-off**: Preserves low-frequency sounds but less wind reduction
- **Use when**: Wind is minimal but occasional gusts occur

### Quick Settings:

Use the preset buttons for common values:
- **60 Hz** button: Aggressive filtering
- **80 Hz** button: Default/recommended
- **100 Hz** button: Conservative filtering

Or use the spinbox to set any value between 40-200 Hz.

## Best Practices

### Physical Wind Protection:

The wind filter is most effective when combined with physical wind protection:

1. **Windscreen/Foam Cover**: 
   - Use a foam windscreen on your microphone
   - Reduces wind hitting the microphone directly
   - Available for most microphone models ($5-20)

2. **Microphone Placement**:
   - Place in sheltered location (behind a wall, under an eave)
   - Avoid direct wind paths
   - Keep away from building corners where wind accelerates

3. **Mounting**:
   - Secure mounting reduces vibration-induced noise
   - Use shock mounts if available
   - Avoid loose cables that can cause handling noise

### Filter Configuration:

1. **Start Conservative**: Begin with 80 Hz cutoff
2. **Monitor Events**: Check if wind events are still being logged
3. **Adjust**: Increase cutoff if still getting wind false alarms
4. **Test**: Verify you're still detecting real noise pollution
5. **Fine-tune**: Adjust based on local conditions

### Seasonal Adjustments:

- **Spring/Fall**: Often windier, may need lower cutoff (60-70 Hz)
- **Summer**: Generally calmer, can use higher cutoff (80-100 Hz)
- **Winter**: Depends on location and weather patterns

### When NOT to Use the Filter:

Consider disabling the wind filter if:
- **Indoor monitoring**: Wind is not a concern
- **Monitoring low-frequency sources**: Tracking distant traffic, industrial noise below 80 Hz
- **Calm conditions**: No wind present, filter provides no benefit
- **Comparison studies**: Need raw, unfiltered data for analysis

## Troubleshooting

### Issue: Still getting wind false alarms with filter enabled

**Solutions**:
1. Lower the cutoff frequency (try 60 Hz)
2. Add a physical windscreen to your microphone
3. Reposition microphone in more sheltered location
4. Increase detection threshold slightly
5. Review events to confirm they are actually wind (could be legitimate low-frequency noise)

### Issue: Missing real noise pollution events

**Solutions**:
1. Raise the cutoff frequency (try 100 Hz)
2. Disable the filter temporarily to test
3. Check if the pollution source is unusually low-frequency
4. Consider monitoring without filter and filtering data in post-processing

### Issue: Audio sounds different with filter enabled

**Explanation**:
- This is normal - low frequencies are removed
- Bass/rumble will be reduced
- Higher-frequency sounds will be clearer
- This is the intended effect to reduce wind noise

### Issue: Filter not making a difference

**Possible causes**:
1. Wind noise might be higher frequency than typical
2. Problem might not be wind (check waveform patterns)
3. Filter cutoff too high (try 60 Hz)
4. Physical wind protection needed as well

## Understanding Filter Impact

### What Gets Filtered:

Frequencies removed depend on cutoff setting:
- **60 Hz cutoff**: Removes 0-60 Hz (subsonic + very low bass)
- **80 Hz cutoff**: Removes 0-80 Hz (subsonic + low bass)
- **100 Hz cutoff**: Removes 0-100 Hz (subsonic + bass fundamentals)

### What's Preserved:

Most noise pollution occurs above 100 Hz:
- Traffic: 200-2000 Hz
- Voices/Shouting: 300-3000 Hz
- Music: 80-15000 Hz (most energy above 100 Hz)
- Construction: 500-4000 Hz
- Aircraft: 400-2000 Hz
- Dogs barking: 500-1000 Hz

### Frequency Reference:

- **20-60 Hz**: Subsonic, distant thunder, distant heavy vehicles
- **60-100 Hz**: Bass fundamentals, rumble
- **100-200 Hz**: Low notes, male voice fundamentals
- **200-500 Hz**: Voice, traffic noise
- **500+ Hz**: Most noise pollution occurs here

## Technical Background

### Why High-Pass Filtering Works:

Wind noise has distinct spectral characteristics:
1. **Energy Distribution**: Most energy in 10-80 Hz range
2. **1/f Spectrum**: Power decreases with increasing frequency
3. **Broadband Nature**: Spreads across spectrum but strongest at low frequencies

By removing frequencies below 80 Hz:
- Wind noise energy is dramatically reduced (often 60-80% reduction)
- Most noise pollution is preserved (occurs above 100 Hz)
- Signal-to-noise ratio improves
- False alarm rate decreases

### Filter Design Choices:

**Butterworth Filter**: Chosen for:
- Maximally flat passband (no ripples)
- Good transition between pass/stop bands
- Well-established and reliable
- Efficient implementation

**4th Order**: Provides:
- -24 dB/octave rolloff (steep enough)
- Computational efficiency
- Stability across different sample rates

**Zero-Phase (filtfilt)**: Ensures:
- No time delay or phase distortion
- Maintains event timing accuracy
- Better audio quality

## Advanced Usage

### Custom Cutoff Selection:

For specific monitoring scenarios:

- **Heavy truck monitoring**: Use 100 Hz (preserve low rumble)
- **Music/party monitoring**: Use 60 Hz (music is higher frequency)
- **Construction monitoring**: Use 60 Hz (construction noise is higher)
- **General outdoor**: Use 80 Hz (balanced approach)

### Combining with Other Features:

1. **Low-Frequency Detection**: Still works above filter cutoff
2. **Calibration**: Apply filter first, then calibrate
3. **Threshold**: May need to adjust after enabling filter
4. **Analytics**: Filtered data used for all analysis

### Data Integrity:

- **Recordings**: Saved audio includes filter if enabled
- **Raw Data**: Cannot recover filtered frequencies later
- **Reversibility**: Keep filter disabled if you need unfiltered data
- **Post-Processing**: For research, record raw and filter offline

## Conclusion

The wind noise filter is a powerful tool for outdoor noise monitoring, but it's most effective when:
1. Combined with physical wind protection
2. Configured for local conditions
3. Adjusted based on monitoring results
4. Used appropriately for your monitoring goals

Remember: The goal is to reduce false alarms from wind while still accurately detecting and recording noise pollution events. Finding the right balance may require some experimentation with your specific setup and location.

## Additional Resources

- **Sound Monitor README**: General application documentation
- **Settings Tab**: Real-time filter controls and information
- **Analytics Tab**: Review filtered vs. unfiltered event patterns
- **Community**: Share your wind filtering experiences and tips

---

**Questions or Issues?**
If you're experiencing wind noise problems not addressed in this guide, please open an issue on GitHub with:
- Your filter settings
- Sample event data
- Description of wind conditions
- Microphone setup details
