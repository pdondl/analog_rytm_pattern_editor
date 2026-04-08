# Plock — Analog Rytm Pattern Editor

A browser-based pattern editor for the Elektron Analog Rytm (FW 1.70+).
Runs entirely client-side: open a `.syx` dump or pull the current workbuffer
over Web MIDI, edit trigs and parameter locks in a familiar step-grid UI,
and send the result back to the machine.

Includes a built-in audio preview with TR-909-flavour drum voices for
quick rhythmic feedback while editing — useful for sketching patterns
away from the hardware.

## Features

- **Trig grid**: 12 tracks × up to 64 steps, two pages. Click to toggle,
  ⌥-click for lock trigs, ⇧-click to mute.
- **Parameter locks**: inspect and edit plocks for every per-step parameter
  (SYN/SMP/FLT/AMP/LFO, sends, trig conditions, retrig, micro-timing, swing,
  slide, sound locks).
- **Advanced scale mode**: per-track length and speed, master-length restart,
  and visible per-track playheads during playback.
- **Audio preview**: hand-rolled Web Audio voices dispatched by machine type
  (BD/SD/RS/CP/BT/LT/MT/HT/CH/OH/CY/CB plus SY/UT fallbacks), with sound-lock
  aware volume/pan and trig-condition evaluation. The editor's "Audio preview
  coverage" panel lists exactly what the preview reflects and what it ignores.
- **MIDI I/O**: connects to the first port whose name contains "rytm";
  requests the current workbuffer pattern and kit via SysEx; sends edits back.
- **File I/O**: load/save `.syx` pattern dumps locally.

## Usage

Open `plock.html` in a recent Chromium-based browser (Web MIDI + SysEx
required; Firefox does not support SysEx). Either click **Connect MIDI**
and **Request Pattern**, or **Load .syx** to open a dump from disk.
Click a step to toggle, ⌘-click to open the step inspector, click a track
label to edit its defaults.

## Files

- `plock.html` — main editor page
- `index.html` — redirect stub for GitHub Pages hosting
- `style.css` — all styling
- `ar-state.js` — app state container and UI helpers
- `ar-constants.js` — byte offsets, enums, machine tables
- `ar-sysex.js` — SysEx decode/encode, pattern/kit parsing
- `ar-editor.js` — grid rendering, step/track inspectors, parameter editing
- `ar-midi.js` — Web MIDI connection and transfer
- `ar-audio.js` — tick-based scheduler, voice synthesis, playhead

## Credits

Pattern, kit, sound, and SysEx byte layouts are derived from the
[**libanalogrytm**](https://github.com/bsp2/libanalogrytm) reverse-engineering
effort by **bsp**, **void**, and **alisomay**, distributed under the MIT
license. This editor wouldn't exist without their work decoding the firmware
1.70 binary format.

Built by [Plenty of Names in the Club](http://plentyofnam.es).

## License

MIT.
