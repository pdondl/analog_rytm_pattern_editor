# Audio Preview Engine — Notes

## Goal

Browser-based audio preview so the user gets immediate rhythmic feedback while
editing patterns. The focus is on **sequencer accuracy**, not sound fidelity —
voices are hand-rolled 909-flavour synthesis dispatched per machine type, not
faithful replicas of the AR's 34 algorithms.

Key benefit: makes it obvious which UI controls (trigs, conditions,
micro-timing, retrig, velocity, swing, accent, mute, sound locks) have a
direct audible effect.

## Status

### Done

**Scheduler**
- Tick-based lookahead scheduler on a 2880 PPQN grid (Web Audio
  "tale of two clocks", `setTimeout` queues events ~25 ms ahead)
- BPM from pattern data
- Per-track speed multipliers (2×, 3/2×, 1×, 3/4×, 1/2×, 1/4×, 1/8×)
- Master speed (normal mode)
- Pattern length (master length in normal mode, per-track length in advanced)
- Advanced scale mode with master-length restart (all tracks snap to step 0
  at master boundary regardless of their own length)
- Mid-playback edits to length / speed take effect on the next tick
  (volatile track fields read via getters from `AR.state.pattern.raw`)
- Pre-roll suppression: playhead stays hidden until effective time ≥ 0 so
  no mid-cycle flash on play

**Trigs**
- Enable / mute / accent
- Velocity (per-step lock or default) → voice gain
- Note (per-step lock or default) → pitch ratio for tonal voices
- Micro-timing (signed, in 1/384ths of 16 steps; scales with track speed)
- Swing flag per step (raw 0..30 → 50..80 %)
- Retrig: rate (fractions of whole note), velocity offset ramp,
  length in 1/16 steps, length = ∞ (runs until next enabled trig)
- All 57 trig conditions: probability 1..100 %, FILL/!FILL, PRE/!PRE,
  NEI/!NEI, 1ST/!1ST, ratio patterns 1:2 .. 8:8
- FILL mode toggle button

**Voices and routing**
- Per-track machine dispatch by ID (BD/SD/RS/CP/BT/LT/MT/HT/CH/OH/CY/CB
  plus SY/UT fallbacks); `DISABLE` machine is silently skipped
- Sound locks honoured: `getStepSound(t, s)` resolves to a pool entry when
  present, else the kit's track sound; machine type / volume / pan are read
  from whichever applies
- Per-hit bus: voice → gain (kit AMP volume × velocity) → panner
  (kit AMP pan) → master
- Default kit seeded by `newPattern()` so empty patterns are immediately
  audible

**Visual**
- Per-track playhead (each track shows its own step position in advanced mode)
- Step flash animation (white fade) on the active step
- "Audio preview coverage" disclosure panel under the editor listing
  audible vs ignored parameters

### Open

These are deliberately *not* implemented yet. The coverage panel tells the
user up-front, so plocking away is safe — the hardware will play what it
shows, the preview just won't reflect those tweaks.

- **Plocks** on any parameter (SYN1..8, SMP, FLT, AMP attack/hold/decay,
  LFO dest/speed/depth, sends). Cheapest first step would be plock-aware
  AMP_VOL / AMP_PAN at schedule time so pan locks at least move.
- **Parameter slides** (slide flag → linear-ramp interpolation between the
  current effective value and the next trig's effective value over the step
  duration). Only meaningful after plocks are honoured.
- **Note length** (irrelevant for the standard drum voices — AR uses it
  only as the amp-envelope gate for non-drum sounds).
- **Filter / envelope / LFO** as real Web Audio nodes driven by the kit's
  bytes. Today the voices use fixed envelopes per machine type and ignore
  FLT / AMP / LFO settings entirely. This is the largest item by far.
- **Sample playback** (SMP). The preview doesn't load samples and the SMP
  layer is silent.
- **FX**: delay, reverb, distortion, compressor, FX LFO. Sends are ignored.
- **Master change length** (`master_chg`, the pattern-chain length). The
  preview only loops a single pattern, so chain semantics are out of scope.
- **Sound pool fetching over SysEx** (see TODO #19). Pool entries are
  honoured when present in the loaded `.syx`, but we don't request the
  pool from the device.
- **MIDI clock out / MIDI note out** to drive the actual hardware while
  the preview runs. Currently audio-only.

## Hardware test results (2026-04-05)

- **Micro-timing is step-relative.** µT offsets are 1/384ths of 16 steps,
  so they scale with the per-track speed multiplier. Confirmed by comparing
  a 1× track with +4 µT against a 3/4× track with +3 µT — perfectly in
  sync, no flam. Proves the 1/384th grid is exact even at non-power-of-2
  speeds.
- **Retrig is absolute.** Retrig rates are fixed beat-relative subdivisions,
  independent of track speed. A 1/16 retrig fires at the same real-time
  rate regardless of the track multiplier.

## Tick grid: 2880 PPQN

The AR's internal clock uses a single high-resolution tick grid.

- **11520 ticks per whole note** (= 2880 PPQN)
- **720 ticks per 1/16 step** at 1× speed
- **Micro-timing**: 24 units per speed-adjusted step. Per-beat µT divisions
  at each track speed:

  | Speed | µT divs/beat | Ticks per µT unit |
  |-------|-------------|-------------------|
  | 1/8×  | 3           | 960               |
  | 1/4×  | 6           | 480               |
  | 1/2×  | 12          | 240               |
  | 3/4×  | 18          | 160               |
  | 1×    | 24          | 120               |
  | 3/2×  | 36          | 80                |
  | 2×    | 48          | 60                |

  All integer. 2880 = 2⁶ × 3² × 5. The factors of 3² cover the 3/4× and
  3/2× speed multipliers (which break power-of-2 PPQNs like 480 or 960).
  The factor of 5 covers retrig rates with a factor of 5 (1/5, 1/10, etc.).

- **Retrig rates** are fractions of a **whole note** (absolute, not
  speed-scaled):
  `1/1, 1/2, 1/3, 1/4, 1/5, 1/6, 1/8, 1/10, 1/12, 1/16, 1/20, 1/24, 1/32, 1/40, 1/48, 1/64, 1/80`
  — all divide evenly into 11520.

Everything (step timing, swing offsets, micro-timing, retrig sub-hits) lives
on this single grid. No floating-point subdivision needed.

## Drum voice synthesis (current)

Minimal Web Audio voices, dispatched by machine ID. No AudioWorklet.

| Machine | Synthesis approach |
|---------|--------------------|
| **BD** (BD_HARD etc.) | Sine + pitch envelope sweep (~150→40 Hz), short click transient |
| **SD** (SD_CLASSIC etc.) | Sine body (~180 Hz) + HP-filtered noise burst |
| **RS** (RS_CLASSIC, RS_HARD) | Short HP-filtered click, very short decay |
| **CP** (CP_CLASSIC) | Noise through BPF with double-hit envelope |
| **BT** | Sine ~65 Hz (lowest tom) |
| **LT** | Sine ~90 Hz |
| **MT** | Sine ~120 Hz |
| **HT** | Sine ~155 Hz |
| **CH** | HP-filtered metal-cluster noise, ~20 ms decay |
| **OH** | Same metal cluster, ~200 ms decay |
| **CY** (CY_RIDE) | BP-filtered metal cluster + sine harmonic, long decay |
| **CB** | Two detuned squares, short decay |
| **SY**\* | Generic synth fallback (sine + envelope) |
| **UT** noise / impulse | Plain noise / single click |

\* `playSynth` and `playUtNoise` / `playUtImpulse` are catch-alls for the
   non-drum machine families so unknown / synth machines still produce
   *something* audible.

The metal cluster is six oscillators at 205.3 / 304.4 / 369.6 / 522.7 / 540
/ 800 Hz (909 metal recipe) shared between CH/OH/CY for a coherent hi-hat
family.

## File structure

Single file: **`ar-audio.js`**

- IIFE module exposing `AR.audio = { start, stop, toggle, setFillMode }`
- Tick-based scheduler, voice synthesis, playhead, kit/sound-pool helpers
- Reads pattern data directly from `AR.state.pattern.raw` — no copies
- Volatile per-track fields (length, speed, defaults, probability) accessed
  through getters so editor edits are picked up on the next scheduler tick

The editor (`ar-editor.js`) adds Play/Stop/FILL buttons and calls into
`AR.audio`. Audio concerns stay out of editor code.
