# Analog Rytm Pattern Editor — TODO

## Remaining Features

### LFO Frequency Reference
- There is a bit somewhere that switches LFO speed reference between track BPM and fixed 120 BPM
- Need to find where this bit lives in the sysex data and expose it in the editor

### SY DUAL VCO Waveform Enum
- The CFG parameter on SY DUAL VCO needs a proper enum mapping
- Requires figuring out the exact value-to-label mapping from the hardware

### FX Track
- The FX track (track 13) has a completely different parameter layout
- Delay, Reverb, Distortion, Compressor parameters need their own section definitions
- Currently not displayed or editable

## Code Quality

### Clean Up & Modularize
- Split the monolithic `pattern_viewer.html` into separate files:
  - `ar-sysex.js` — SysEx encode/decode, pattern/kit/sound parsing
  - `ar-constants.js` — machine names, param names, enums, bipolar/decimal/freq maps
  - `ar-editor.js` — UI logic, slider/panel rendering, plock editing
  - `ar-midi.js` — WebMIDI connect, send/receive
  - `style.css` — all styles (currently inline in `<style>`)

### Magic Constants → Named Defines
- Replace hex offsets (0x1C, 0x2E, etc.) with named constants
- Document the ar_sound_t struct offsets systematically
- Consolidate KIT_TRACKS_BASE, AR_SOUND_V5_SZ, MACHINE_TYPE_OFFSET, etc.

### Code Comments
- Add JSDoc-style comments to major functions
- Document the s_u16_t encoding (hi-first, lo byte LSB-shifted)
- Document the plock fine byte system (0x80+ companion slots)
- Document the difference between kit byte encoding vs plock encoding for freq params
