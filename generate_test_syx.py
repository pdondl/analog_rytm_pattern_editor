#!/usr/bin/env python3
"""Generate a test .syx file with pattern + kit + sound pool for the AR pattern viewer."""

import struct
import sys

# ── Constants ──────────────────────────────────────────────────────────────────
AR_PATTERN_V5_SZ   = 0x332D  # 13101 bytes raw
AR_KIT_V5_SZ       = 0x0A32  # 2610 bytes raw
AR_SOUND_V5_SZ     = 162     # bytes raw per sound

TRACK_V5_SZ        = 0x0281  # 641 bytes per track in pattern
AR_NUM_TRACKS      = 13
AR_NUM_STEPS       = 64

KIT_TRACKS_BASE    = 0x002E
MACHINE_TYPE_OFF   = 0x7C
NOTE_OFF           = 0x0070  # notes[64] within track
VELOCITY_OFF       = 0x00B0  # velocities[64] within track
NOTE_LEN_OFF       = 0x00F0  # note_lengths[64] within track
MICRO_TIMING_OFF   = 0x0130  # micro_timings[64] within track
RETRIG_LEN_OFF     = 0x0170  # retrig_lengths[64] within track
RETRIG_RATE_OFF    = 0x01B0  # retrig_rates[64] within track
DEFAULT_NOTE_OFF   = 0x0230  # default_note within track
DEFAULT_VELO_OFF   = 0x0231  # default_velocity within track
DEFAULT_LEN_OFF    = 0x0232  # default_note_len within track
DEFAULT_TRIG_FLAGS_OFF = 0x0233  # default_trig_flags (s_u16_t, hi byte first)
NUM_STEPS_OFF      = 0x0235  # num_steps within track
SOUND_LOCK_OFF     = 0x0237  # sound_locks[64] within track
SPEED_OFF          = 0x0277  # flags_and_speed within track
TRIG_PROB_OFF      = 0x0278  # trig_probability within track

# Plock sequences
PLOCK_SEQS_BASE    = 0x2091
PLOCK_SEQ_SZ       = 0x42    # 66 bytes: type(1) + track(1) + values(64)
NUM_PLOCK_SEQS     = 72

# BPM
MASTER_CHG_OFF     = 0x3323  # u16 LE, master change length
KIT_NUMBER_OFF     = 0x3325
SWING_AMOUNT_OFF   = 0x3326
SCALE_MODE_OFF     = 0x3327  # 0=normal, 1=advanced
MASTER_SPEED_OFF   = 0x3328  # 0=2x,1=3/2x,2=1x,3=3/4x,4=1/2x,5=1/4x,6=1/8x
BPM_MSB_OFF        = 0x332A
BPM_LSB_OFF        = 0x332B

# Plock types (matching PLOCK_INFO in viewer)
PL_SRC_P1   = 0x00  # SRC param 1 (LEV for most machines)
PL_SRC_P2   = 0x01  # SRC param 2 (TUN for most machines)
PL_SRC_P3   = 0x02  # SRC param 3 (DEC for most machines)
PL_SRC_P4   = 0x03  # SRC param 4
PL_SRC_P5   = 0x04  # SRC param 5
PL_SRC_P8   = 0x07  # SRC param 8
PL_SMP_TUN  = 0x08  # Sample tune (bipolar: 64=0)
PL_SMP_FIN  = 0x09  # Sample fine tune (bipolar: 64=0)
PL_SMP_LOP  = 0x0E  # Sample loop (0=OFF, 1=ON)
PL_FLT_DEC  = 0x12  # Filter decay (127=inf)
PL_FLT_REL  = 0x13  # Filter release (127=inf)
PL_FLT_FRQ  = 0x14  # Filter frequency
PL_FLT_RES  = 0x15  # Filter resonance
PL_FLT_TYP  = 0x16  # Filter type (0-6)
PL_FLT_ENV  = 0x17  # Filter env depth (bipolar: 64=0)
PL_AMP_DEC  = 0x1A  # Amp decay (127=inf)
PL_AMP_DEL  = 0x1C  # Delay send
PL_AMP_REV  = 0x1D  # Reverb send
PL_AMP_PAN  = 0x1E  # Pan (0=L64, 64=C, 127=R63)
PL_AMP_VOL  = 0x1F  # Volume
PL_LFO_SPD  = 0x21  # LFO speed (bipolar: 64=0)
PL_LFO_MUL  = 0x22  # LFO multiply (0-11)
PL_LFO_FAD  = 0x23  # LFO fade (bipolar: 64=0)
PL_LFO_DST  = 0x24  # LFO destination
PL_LFO_WAV  = 0x25  # LFO waveform (0-6)
PL_LFO_SPH  = 0x26  # LFO start phase (0-127)
PL_LFO_MOD  = 0x27  # LFO trig mode (0-4)
PL_LFO_DEP  = 0x28  # LFO depth

# FX plock types (FX track only — same numbers, different meaning)
FX_PL_DELAY_TIME   = 0   # Delay time
FX_PL_DELAY_PP     = 1   # Delay ping-pong (0=off, 1=on)
FX_PL_DELAY_WID    = 2   # Delay width (bipolar: 64=center)
FX_PL_DELAY_FB     = 3   # Delay feedback
FX_PL_DELAY_HPF    = 4   # Delay HPF
FX_PL_DELAY_LPF    = 5   # Delay LPF
FX_PL_DELAY_REV    = 6   # Delay reverb send
FX_PL_DELAY_VOL    = 7   # Delay volume
FX_PL_DIST_DOV     = 8   # Distortion delay overdrive
FX_PL_DIST_DEL     = 9   # Distortion delay routing (0=pre, 1=post)
FX_PL_REVERB_PRE   = 10  # Reverb pre-delay
FX_PL_REVERB_DEC   = 11  # Reverb decay
FX_PL_REVERB_FRQ   = 12  # Reverb freq
FX_PL_REVERB_GAI   = 13  # Reverb gain (bipolar: 64=center)
FX_PL_REVERB_HPF   = 14  # Reverb HPF
FX_PL_REVERB_LPF   = 15  # Reverb LPF
FX_PL_REVERB_VOL   = 16  # Reverb volume
FX_PL_DIST_REV     = 17  # Distortion reverb routing (0=pre, 1=post)
FX_PL_DIST_AMT     = 18  # Distortion amount
FX_PL_DIST_SYM     = 19  # Distortion symmetry (bipolar: 64=center)
FX_PL_COMP_THR     = 21  # Compressor threshold
FX_PL_COMP_ATK     = 22  # Compressor attack
FX_PL_COMP_REL     = 23  # Compressor release
FX_PL_COMP_RAT     = 24  # Compressor ratio
FX_PL_COMP_SEQ     = 25  # Compressor sidechain EQ (0=off, 1=lpf, 2=hpf, 3=hit)
FX_PL_COMP_GAI     = 26  # Compressor makeup gain
FX_PL_COMP_MIX     = 27  # Compressor dry/wet mix
FX_PL_COMP_VOL     = 28  # Compressor volume
FX_PL_LFO_SPD      = 29  # FX LFO speed (bipolar: 64=center)
FX_PL_LFO_MUL      = 30  # FX LFO multiply
FX_PL_LFO_FAD      = 31  # FX LFO fade (bipolar: 64=center)
FX_PL_LFO_DST      = 32  # FX LFO destination
FX_PL_LFO_WAV      = 33  # FX LFO waveform
FX_PL_LFO_SPH      = 34  # FX LFO start phase
FX_PL_LFO_MOD      = 35  # FX LFO trig mode
FX_PL_LFO_DEP      = 36  # FX LFO depth (bipolar: 64=center)

# FX kit parameter offsets (absolute within kit)
FX_KIT_BASE        = 0x07CA

# Trig bits: 14 bits per step, packed in 112 bytes (64 steps × 14 bits = 896 bits = 112 bytes)
TRIG_ENABLE        = 0x0001
TRIG_SYN_PL_SW     = 0x0080
TRIG_SMP_PL_SW     = 0x0100
TRIG_ENV_PL_SW     = 0x0200
TRIG_LFO_PL_SW     = 0x0400
TRIG_SYN_PL_EN     = 0x0800
TRIG_SMP_PL_EN     = 0x1000
# Normal trig: enable + all retrigger switches on
TRIG_NORMAL        = TRIG_ENABLE | TRIG_SYN_PL_SW | TRIG_SMP_PL_SW | TRIG_ENV_PL_SW | TRIG_LFO_PL_SW
# Lock trig: enable + PL_EN set + PL_SW off (SYN/SMP switches off)
TRIG_LOCK          = TRIG_ENABLE | TRIG_SYN_PL_EN | TRIG_SMP_PL_EN | TRIG_ENV_PL_SW | TRIG_LFO_PL_SW

# Machine IDs
MACHINES = {
    'BD_HARD': 0, 'BD_CLASSIC': 1, 'SD_HARD': 2, 'SD_CLASSIC': 3,
    'RS_HARD': 4, 'RS_CLASSIC': 5, 'CP_CLASSIC': 6, 'BT_CLASSIC': 7,
    'XT_CLASSIC': 8, 'CH_CLASSIC': 9, 'OH_CLASSIC': 10, 'CY_CLASSIC': 11,
    'CB_CLASSIC': 12, 'BD_FM': 13, 'SD_FM': 14, 'UT_NOISE': 15,
    'UT_IMPULSE': 16, 'CH_METALLIC': 17, 'OH_METALLIC': 18, 'CY_METALLIC': 19,
    'CB_METALLIC': 20, 'BD_PLASTIC': 21, 'BD_SILKY': 22, 'SD_NATURAL': 23,
    'HH_BASIC': 24, 'CY_RIDE': 25, 'BD_SHARP': 26, 'DISABLE': 27,
    'SY_DUAL_VCO': 28, 'SY_CHIP': 29, 'BD_ACOUSTIC': 30, 'SD_ACOUSTIC': 31,
    'SY_RAW': 32, 'HH_LAB': 33,
}

# Sysex IDs
DUMP_ID_PATTERN    = 0x54
DUMP_ID_KIT        = 0x52
DUMP_ID_SOUND      = 0x53


def encode_8to7(raw):
    """Encode 8-bit raw data to 7-bit sysex (matching AR sysex format)."""
    out = bytearray()
    chksum = 0
    pkb_nr = 0
    msbs = 0
    msb_idx = -1

    for c in raw:
        if pkb_nr == 0:
            msbs = (c & 0x80) >> 1
            msb_idx = len(out)
            out.append(0)  # placeholder
        else:
            msbs |= (c & 0x80) >> (1 + pkb_nr)

        out.append(c & 0x7F)
        chksum += (c & 0x7F)
        pkb_nr += 1

        if pkb_nr == 7:
            chksum += msbs
            out[msb_idx] = msbs
            pkb_nr = 0

    # Flush remaining
    if pkb_nr > 0:
        chksum += msbs
        out[msb_idx] = msbs

    return bytes(out), chksum & 0x3FFF


def build_sysex(raw, dump_id, obj_nr=0, dev_id=0, ver_hi=0x01, ver_lo=0x01):
    """Build a complete sysex message from raw data."""
    data, checksum = encode_8to7(raw)
    chk_hi = (checksum >> 7) & 0x7F
    chk_lo = checksum & 0x7F
    data_sz = len(data) + 2 + 2 + 1  # payload + chksum + datasize + F7
    ds_hi = (data_sz >> 7) & 0x7F
    ds_lo = data_sz & 0x7F

    syx = bytearray()
    syx.append(0xF0)
    syx.extend([0x00, 0x20, 0x3C])  # Elektron manufacturer ID
    syx.append(0x07)                 # Analog RYTM product ID
    syx.append(dev_id)
    syx.append(dump_id)
    syx.append(ver_hi)
    syx.append(ver_lo)
    syx.append(obj_nr)
    syx.extend(data)
    syx.extend([chk_hi, chk_lo, ds_hi, ds_lo])
    syx.append(0xF7)
    return bytes(syx)


def set_trig_flags(trig_bits, step, val):
    """Write a 14-bit trig value for a step (MSB-first, matching AR/viewer format)."""
    start_bit = 14 * step
    num_bits = 14
    byte_off = start_bit >> 3
    bit_off = start_bit - (byte_off << 3)
    src_shift = num_bits
    bits_left = num_bits

    while bits_left > 0:
        bits_avail = 8 - bit_off
        if bits_left < bits_avail:
            shift = bits_avail - bits_left
            mask = ((1 << bits_left) - 1) << shift
            src_shift -= bits_left
            trig_bits[byte_off] = (trig_bits[byte_off] & ~mask) | (((val >> src_shift) & ((1 << bits_left) - 1)) << shift)
            bits_left = 0
        else:
            mask = (1 << bits_avail) - 1
            src_shift -= bits_avail
            trig_bits[byte_off] = (trig_bits[byte_off] & ~mask) | ((val >> src_shift) & mask)
            bits_left -= bits_avail
            bit_off = 0
            byte_off += 1


def add_plock(raw, seq_idx, track, plock_type, step_values):
    """Write a plock sequence. step_values is a dict {step: value}.
    seq_idx is the plock sequence slot (0-71)."""
    base = PLOCK_SEQS_BASE + seq_idx * PLOCK_SEQ_SZ
    raw[base] = plock_type
    raw[base + 1] = track
    # Values default to 0xFF (no lock); set specific steps
    for s in range(AR_NUM_STEPS):
        raw[base + 2 + s] = 0xFF
    for s, v in step_values.items():
        raw[base + 2 + s] = v


def make_pattern():
    """Create a test pattern with trigs, plocks, note/velocity locks, and BPM."""
    raw = bytearray(AR_PATTERN_V5_SZ)

    # Magic bytes
    raw[0:4] = b'\x00\x00\x00\x00'

    # Fill plock sequence area with 0xFF (unused)
    plock_end = PLOCK_SEQS_BASE + NUM_PLOCK_SEQS * PLOCK_SEQ_SZ
    for i in range(PLOCK_SEQS_BASE, plock_end):
        raw[i] = 0xFF

    # BPM: 125.0 → 125 * 120 = 15000
    bpm = 125.0
    bpm_raw = int(bpm * 120)
    raw[BPM_MSB_OFF] = (bpm_raw >> 8) & 0xFF
    raw[BPM_LSB_OFF] = bpm_raw & 0xFF

    # Kit number (0 = kit 1)
    raw[KIT_NUMBER_OFF] = 0x00

    # Scale settings (u16 fields are big-endian)
    raw[MASTER_CHG_OFF] = 0        # master change length = 1 (BE hi)
    raw[MASTER_CHG_OFF + 1] = 1    # (BE lo)
    raw[SCALE_MODE_OFF] = 0        # normal mode
    raw[MASTER_SPEED_OFF] = 2      # 1x speed

    # Track configs: (machine, steps, speed, trig_steps, sound_locks)
    track_configs = [
        ('BD_HARD',     16, 2, [0, 4, 8, 12], {8: 5}),         # BD: 4-on-floor, step 9 → SY DUAL VCO
        ('SD_CLASSIC',  16, 2, [4, 12], {}),                    # SD: backbeat
        ('RS_CLASSIC',  16, 2, [], {}),                          # RS: off
        ('CP_CLASSIC',  16, 2, [4, 12], {}),                    # CP: with snare
        ('BT_CLASSIC',  16, 2, [], {}),                          # BT: off
        ('XT_CLASSIC',  16, 2, [2, 6, 10, 14], {}),             # LT: offbeat 16ths
        ('XT_CLASSIC',  16, 2, [], {}),                          # MT: off
        ('XT_CLASSIC',  16, 2, [], {}),                          # HT: off
        ('CH_METALLIC', 16, 2, list(range(16)), {}),             # CH: every step
        ('OH_METALLIC', 16, 2, [2, 6, 10, 14], {6: 10}),        # OH: offbeat, step 7 → HH LAB
        ('CY_RIDE',     16, 2, [0, 8], {}),                     # CY: every bar
        ('CB_CLASSIC',  16, 2, [4, 12], {}),                    # CB: offbeat
        ('BD_HARD',     16, 2, [0, 4, 8, 12], {}),               # FX: trigs on beats
    ]

    for t, (mach, steps, speed, trigs, slocks) in enumerate(track_configs):
        base = 4 + t * TRACK_V5_SZ

        # Trig bits
        trig_area = bytearray(raw[base:base + 112])
        for s in trigs:
            set_trig_flags(trig_area, s, TRIG_NORMAL)
        raw[base:base + 112] = trig_area

        # Per-step fields: init to defaults
        for s in range(AR_NUM_STEPS):
            raw[base + NOTE_OFF + s]       = 0xFF  # no note lock
            raw[base + VELOCITY_OFF + s]   = 0xFF  # no velocity lock
            raw[base + NOTE_LEN_OFF + s]   = 0xFF  # no length lock
            raw[base + MICRO_TIMING_OFF + s] = 0x00  # centered
            raw[base + RETRIG_LEN_OFF + s] = 0xFF
            raw[base + RETRIG_RATE_OFF + s] = 0xFF
            raw[base + SOUND_LOCK_OFF + s] = 0xFF

        # Sound locks
        for s, slot in slocks.items():
            raw[base + SOUND_LOCK_OFF + s] = slot

        # Track settings
        raw[base + NUM_STEPS_OFF]    = steps
        raw[base + SPEED_OFF]        = speed
        raw[base + DEFAULT_NOTE_OFF] = 60    # C3
        raw[base + DEFAULT_VELO_OFF] = 100
        raw[base + DEFAULT_LEN_OFF]  = 0x40
        raw[base + TRIG_PROB_OFF]    = 100
        # Default trig flags (s_u16_t big-endian): TRIG_NORMAL matches AR defaults
        dtf = TRIG_NORMAL
        raw[base + DEFAULT_TRIG_FLAGS_OFF]     = (dtf >> 8) & 0xFF
        raw[base + DEFAULT_TRIG_FLAGS_OFF + 1] = dtf & 0xFF

    # ── Per-step note, velocity, micro-timing locks ────────────────────────

    # FX (track 12): add lock trigs on steps 2 and 6
    fx_base = 4 + 12 * TRACK_V5_SZ
    fx_trig_area = bytearray(raw[fx_base:fx_base + 112])
    set_trig_flags(fx_trig_area, 2, TRIG_LOCK)
    set_trig_flags(fx_trig_area, 6, TRIG_LOCK)
    raw[fx_base:fx_base + 112] = fx_trig_area

    # BD (track 0): velocity accent on beat 1 (step 0)
    bd_base = 4 + 0 * TRACK_V5_SZ
    raw[bd_base + VELOCITY_OFF + 0] = 127   # accent on beat 1
    raw[bd_base + VELOCITY_OFF + 8] = 110   # slightly accented beat 3

    # SD (track 1): note variation (different pitches)
    sd_base = 4 + 1 * TRACK_V5_SZ
    raw[sd_base + NOTE_OFF + 4]  = 62   # D3 on beat 2
    raw[sd_base + NOTE_OFF + 12] = 58   # A#2 on beat 4

    # CH (track 8): micro-timing swing feel on odd steps
    ch_base = 4 + 8 * TRACK_V5_SZ
    for s in [1, 3, 5, 7, 9, 11, 13, 15]:
        raw[ch_base + MICRO_TIMING_OFF + s] = 8  # push late

    # OH (track 9): velocity dynamics
    oh_base = 4 + 9 * TRACK_V5_SZ
    raw[oh_base + VELOCITY_OFF + 2]  = 80
    raw[oh_base + VELOCITY_OFF + 6]  = 120  # accented (sound-locked step)
    raw[oh_base + VELOCITY_OFF + 10] = 70
    raw[oh_base + VELOCITY_OFF + 14] = 90

    # ── Plock sequences ───────────────────────────────────────────────────

    seq = 0  # plock sequence counter

    # BD (track 0): sweep decay across the bar
    add_plock(raw, seq, 0, PL_SRC_P3, {0: 90, 4: 70, 8: 50, 12: 40})
    seq += 1

    # BD (track 0): filter freq movement
    add_plock(raw, seq, 0, PL_FLT_FRQ, {0: 100, 4: 80, 8: 60, 12: 90})
    seq += 1

    # SD (track 1): reverb send on beat 4 only
    add_plock(raw, seq, 1, PL_AMP_REV, {4: 0, 12: 80})
    seq += 1

    # SD (track 1): pan alternating
    add_plock(raw, seq, 1, PL_AMP_PAN, {4: 40, 12: 88})
    seq += 1

    # CP (track 3): volume lock (no trig on some steps = lock trigs)
    # Steps 4 and 12 have trigs; add plocks on steps WITHOUT trigs too
    add_plock(raw, seq, 3, PL_AMP_VOL, {2: 60, 6: 45, 10: 30, 14: 50})
    seq += 1

    # LT (track 5): sample tune sweep across offbeat hits
    add_plock(raw, seq, 5, PL_SMP_TUN, {2: 50, 6: 60, 10: 70, 14: 80})
    seq += 1

    # LT (track 5): delay send increasing
    add_plock(raw, seq, 5, PL_AMP_DEL, {2: 20, 6: 50, 10: 80, 14: 110})
    seq += 1

    # CH (track 8): filter freq pattern for texture
    add_plock(raw, seq, 8, PL_FLT_FRQ, {
        0: 100, 1: 90, 2: 80, 3: 70, 4: 100, 5: 90, 6: 80, 7: 70,
        8: 110, 9: 100, 10: 90, 11: 80, 12: 110, 13: 100, 14: 90, 15: 80,
    })
    seq += 1

    # CH (track 8): amp decay variation
    add_plock(raw, seq, 8, PL_AMP_DEC, {
        0: 40, 2: 30, 4: 40, 6: 30, 8: 50, 10: 35, 12: 50, 14: 35,
    })
    seq += 1

    # OH (track 9): LFO depth on accented step (bipolar: 64=center)
    add_plock(raw, seq, 9, PL_LFO_DEP, {6: 100, 14: 30})  # +36, -34
    seq += 1

    # CY (track 10): long reverb tail
    add_plock(raw, seq, 10, PL_AMP_REV, {0: 90, 8: 60})
    seq += 1

    # CB (track 11): SRC tune variation
    add_plock(raw, seq, 11, PL_SRC_P2, {4: 70, 12: 55})
    seq += 1

    # ── New plocks to exercise rich parameter display ────────────────────

    # BD (track 0): filter type variation
    add_plock(raw, seq, 0, PL_FLT_TYP, {0: 0, 4: 2, 8: 3, 12: 6})  # LP2, BP, HP1, PK
    seq += 1

    # BD (track 0): filter env depth (bipolar: 64=center)
    add_plock(raw, seq, 0, PL_FLT_ENV, {0: 90, 4: 40, 8: 64, 12: 100})  # +26, -24, 0, +36
    seq += 1

    # BD (track 0): amp decay with infinity
    add_plock(raw, seq, 0, PL_AMP_DEC, {0: 80, 8: 127})  # 80, inf
    seq += 1

    # SD (track 1): LFO waveform
    add_plock(raw, seq, 1, PL_LFO_WAV, {4: 1, 12: 3})  # SIN, SAW
    seq += 1

    # SD (track 1): LFO trig mode
    add_plock(raw, seq, 1, PL_LFO_MOD, {4: 0, 12: 2})  # FRE, HLD
    seq += 1

    # SD (track 1): LFO speed (bipolar)
    add_plock(raw, seq, 1, PL_LFO_SPD, {4: 80, 12: 30})  # +16, -34
    seq += 1

    # SD (track 1): LFO destination (valid internal IDs)
    add_plock(raw, seq, 1, PL_LFO_DST, {4: 20, 12: 8})  # F:FRQ (id=20), S:TUN (id=8)
    seq += 1

    # SD (track 1): LFO multiply
    add_plock(raw, seq, 1, PL_LFO_MUL, {4: 3, 12: 8})  # 8, 256
    seq += 1

    # LT (track 5): sample loop toggle
    add_plock(raw, seq, 5, PL_SMP_LOP, {2: 1, 6: 0, 10: 1, 14: 0})  # ON, OFF, ON, OFF
    seq += 1

    # LT (track 5): sample fine tune (bipolar)
    add_plock(raw, seq, 5, PL_SMP_FIN, {2: 54, 6: 74, 10: 64, 14: 44})  # -10, +10, 0, -20
    seq += 1

    # CH (track 8): micro-timing values to show fractions
    raw[ch_base + MICRO_TIMING_OFF + 0] = 12   # +12 = +1/32
    raw[ch_base + MICRO_TIMING_OFF + 4] = 6    # +6 = +1/64
    raw[ch_base + MICRO_TIMING_OFF + 8] = 0x3F & (-6 + 64)  # -6 = -1/64
    raw[ch_base + MICRO_TIMING_OFF + 12] = 0x3F & (-12 + 64)  # -12 = -1/32

    # SD Classic (track 1): P8 = BAL (bipolar, machine 3)
    add_plock(raw, seq, 1, PL_SRC_P8, {4: 32, 12: 96})  # -32, +32
    seq += 1

    # LFO fade (bipolar)
    add_plock(raw, seq, 1, PL_LFO_FAD, {4: 30, 12: 90})  # -34, +26
    seq += 1

    # BD (track 0): SRC TUN (P2) — limited bipolar for BD Hard (-32..+32)
    add_plock(raw, seq, 0, PL_SRC_P2, {0: 76, 4: 52, 8: 64, 12: 32})  # +12, -12, +0, -32 (min)
    seq += 1

    # BD TUN fine companion (type=0x80, track=0x80) — must follow coarse TUN immediately
    # fine/128 = fractional part: 64→+0.50, 0→+0.00, 32→+0.25
    add_plock(raw, seq, 0x80, 0x80, {0: 64, 4: 0, 8: 32, 12: 0})  # +12.50, -12.00, +0.25, -32.00
    seq += 1

    # CP (track 3): filter decay with infinity
    add_plock(raw, seq, 3, PL_FLT_DEC, {4: 80, 12: 127})  # 80, ∞
    seq += 1

    # CP (track 3): filter release with infinity
    add_plock(raw, seq, 3, PL_FLT_REL, {4: 50, 12: 127})  # 50, ∞
    seq += 1

    # BD (track 0): LFO start phase (varied degrees)
    add_plock(raw, seq, 0, PL_LFO_SPH, {0: 0, 4: 32, 8: 64, 12: 96})  # 0°, 90°, 180°, 270°
    seq += 1

    # ── FX track (track 12) plocks ────────────────────────────────────────

    # FX: delay time variation
    add_plock(raw, seq, 12, FX_PL_DELAY_TIME, {0: 40, 4: 80, 8: 60, 12: 100})
    seq += 1

    # FX: delay feedback
    add_plock(raw, seq, 12, FX_PL_DELAY_FB, {0: 64, 8: 90})
    seq += 1

    # FX: delay ping-pong toggle
    add_plock(raw, seq, 12, FX_PL_DELAY_PP, {0: 0, 4: 1, 8: 0, 12: 1})
    seq += 1

    # FX: delay width (bipolar)
    add_plock(raw, seq, 12, FX_PL_DELAY_WID, {0: 32, 8: 96})  # -32, +32
    seq += 1

    # FX: reverb decay
    add_plock(raw, seq, 12, FX_PL_REVERB_DEC, {0: 90, 4: 40, 8: 127, 12: 110})
    seq += 1

    # FX: reverb gain (bipolar)
    add_plock(raw, seq, 12, FX_PL_REVERB_GAI, {0: 80, 8: 48})  # +16, -16
    seq += 1

    # FX: distortion amount
    add_plock(raw, seq, 12, FX_PL_DIST_AMT, {0: 30, 4: 80, 8: 50, 12: 100})
    seq += 1

    # FX: distortion symmetry (bipolar)
    add_plock(raw, seq, 12, FX_PL_DIST_SYM, {4: 40, 12: 88})  # -24, +24
    seq += 1

    # FX: distortion delay routing
    add_plock(raw, seq, 12, FX_PL_DIST_DEL, {0: 0, 8: 1})  # PRE, POST
    seq += 1

    # FX: compressor threshold
    add_plock(raw, seq, 12, FX_PL_COMP_THR, {0: 80, 4: 50, 8: 100, 12: 30})
    seq += 1

    # FX: compressor sidechain EQ
    add_plock(raw, seq, 12, FX_PL_COMP_SEQ, {0: 0, 4: 1, 8: 2, 12: 3})  # OFF, LPF, HPF, HIT
    seq += 1

    # FX: FX LFO speed (bipolar)
    add_plock(raw, seq, 12, FX_PL_LFO_SPD, {0: 80, 8: 40})  # +16, -24
    seq += 1

    # FX: FX LFO destination
    add_plock(raw, seq, 12, FX_PL_LFO_DST, {0: 37, 4: 0, 8: 11, 12: 18})  # NONE, DEL:TIM, REV:DEC, DST:AMT
    seq += 1

    # FX: FX LFO waveform
    add_plock(raw, seq, 12, FX_PL_LFO_WAV, {0: 0, 4: 2, 8: 4, 12: 6})
    seq += 1

    return raw


def make_kit(track_machines):
    """Create a test kit with specified machines per track."""
    raw = bytearray(AR_KIT_V5_SZ)

    for t, machine_name in enumerate(track_machines[:12]):
        machine_id = MACHINES.get(machine_name, 0)
        track_base = KIT_TRACKS_BASE + t * AR_SOUND_V5_SZ

        # Machine type
        raw[track_base + MACHINE_TYPE_OFF] = machine_id

        # Set some default synth param values so they show non-zero
        # synth_param_1 through synth_param_8 at offsets 0x1C..0x2A (s_u16_t = 2 bytes each)
        params = [100, 64, 80, 64, 64, 64, 64, 64]
        for i, val in enumerate(params):
            raw[track_base + 0x1C + i * 2] = val

        # Sample params: tune=64, fine=64, nr=0, br=0, sta=0, end=127, loop=0, lev=100
        sample_vals = [64, 64, 0, 0, 0, 127, 0, 100]
        for i, val in enumerate(sample_vals):
            raw[track_base + 0x2C + i * 2] = val

        # Filter: atk=0, dec=64, sus=64, rel=32, frq=64, res=0, typ=0, env=64
        filt_vals = [0, 64, 64, 32, 64, 0, 0, 64]
        for i, val in enumerate(filt_vals):
            raw[track_base + 0x3C + i * 2] = val

        # Amp: atk=0, hld=0, dec=64, drv=0, dly=0, rev=0, pan=64, vol=100
        amp_vals = [0, 0, 64, 0, 0, 0, 64, 100]
        for i, val in enumerate(amp_vals):
            raw[track_base + 0x4C + i * 2] = val

        # LFO: spd=32, mlt=1, fad=0, dst=0, wav=0, phs=0, mod=0, dep=64
        lfo_vals = [32, 1, 0, 0, 0, 0, 0, 64]
        for i, val in enumerate(lfo_vals):
            raw[track_base + 0x5E + i * 2] = val

    # ── FX track kit defaults (absolute offsets in kit) ──────────────────
    # Delay: time=64, pp=0, wid=64, fb=32, hpf=0, lpf=127, rev=0, vol=100
    fx_delay = [64, 0, 64, 32, 0, 127, 0, 100]
    for i, val in enumerate(fx_delay):
        raw[FX_KIT_BASE + i * 2] = val

    # Dist DOV=0, Dist DEL routing=0(PRE)
    raw[FX_KIT_BASE + 8 * 2] = 0    # DOV
    raw[FX_KIT_BASE + 9 * 2] = 0    # DEL routing (PRE)

    # Reverb: pre=32, dec=80, frq=64, gai=64, hpf=0, lpf=127, vol=80
    fx_reverb = [32, 80, 64, 64, 0, 127, 80]
    for i, val in enumerate(fx_reverb):
        raw[FX_KIT_BASE + (10 + i) * 2] = val

    # Dist REV routing=0(PRE), Dist AMT=0, Dist SYM=64(center)
    raw[FX_KIT_BASE + 17 * 2] = 0    # REV routing (PRE)
    raw[FX_KIT_BASE + 18 * 2] = 0    # AMT
    raw[FX_KIT_BASE + 19 * 2] = 64   # SYM (center)

    # Compressor: thr=96, atk=3(=1ms), rel=4(=1s), rat=2(=1:8), seq=0(OFF), mup=0, mix=64, vol=100
    fx_comp = [96, 3, 4, 2, 0, 0, 64, 100]
    for i, val in enumerate(fx_comp):
        raw[FX_KIT_BASE + (21 + i) * 2] = val

    # FX LFO: spd=64(stopped), mul=1, fad=64(none), dst=37(NONE), wav=0, phs=0, mod=0, dep=64
    fx_lfo = [64, 1, 64, 37, 0, 0, 0, 64]
    for i, val in enumerate(fx_lfo):
        raw[FX_KIT_BASE + (29 + i) * 2] = val

    return raw


def make_sound(machine_name):
    """Create a test sound with specified machine type."""
    raw = bytearray(AR_SOUND_V5_SZ)
    machine_id = MACHINES.get(machine_name, 0)
    raw[MACHINE_TYPE_OFF] = machine_id

    # Set some param defaults
    params = [100, 64, 80, 64, 64, 64, 64, 64]
    for i, val in enumerate(params):
        raw[0x1C + i * 2] = val

    sample_vals = [64, 64, 0, 0, 0, 127, 0, 100]
    for i, val in enumerate(sample_vals):
        raw[0x2C + i * 2] = val

    filt_vals = [0, 64, 64, 32, 64, 0, 0, 64]
    for i, val in enumerate(filt_vals):
        raw[0x3C + i * 2] = val

    amp_vals = [0, 0, 64, 0, 0, 0, 64, 100]
    for i, val in enumerate(amp_vals):
        raw[0x4C + i * 2] = val

    lfo_vals = [32, 1, 0, 0, 0, 0, 0, 64]
    for i, val in enumerate(lfo_vals):
        raw[0x5E + i * 2] = val

    return raw


def main():
    # Track machines for the kit
    track_machines = [
        'BD_HARD', 'SD_CLASSIC', 'RS_CLASSIC', 'CP_CLASSIC',
        'BT_CLASSIC', 'XT_CLASSIC', 'XT_CLASSIC', 'XT_CLASSIC',
        'CH_METALLIC', 'OH_METALLIC', 'CY_RIDE', 'CB_CLASSIC',
    ]

    # Build pattern
    pat_raw = make_pattern()
    pat_syx = build_sysex(pat_raw, DUMP_ID_PATTERN, obj_nr=0)

    # Build kit
    kit_raw = make_kit(track_machines)
    kit_syx = build_sysex(kit_raw, DUMP_ID_KIT, obj_nr=0)

    # Build sound pool sounds (for the two sound-locked slots used: 5 and 10)
    # Slot 5: SY DUAL VCO (compatible with BD track)
    sound5 = make_sound('SY_DUAL_VCO')
    sound5_syx = build_sysex(sound5, DUMP_ID_SOUND, obj_nr=5)

    # Slot 10: HH LAB (compatible with OH track)
    sound10 = make_sound('HH_LAB')
    sound10_syx = build_sysex(sound10, DUMP_ID_SOUND, obj_nr=10)

    # Bundle into single .syx file
    bundle = pat_syx + kit_syx + sound5_syx + sound10_syx

    outfile = 'test_pattern.syx'
    with open(outfile, 'wb') as f:
        f.write(bundle)

    print(f'Generated {outfile}:')
    print(f'  Pattern: {len(pat_syx)} bytes (raw {len(pat_raw)})')
    print(f'  Kit:     {len(kit_syx)} bytes (raw {len(kit_raw)})')
    print(f'  Sound 5: {len(sound5_syx)} bytes (SY DUAL VCO)')
    print(f'  Sound 10: {len(sound10_syx)} bytes (HH LAB)')
    print(f'  Total:   {len(bundle)} bytes')
    print()
    print('Track machines:')
    for i, m in enumerate(track_machines):
        names = ['BD','SD','RS','CP','BT','LT','MT','HT','CH','OH','CY','CB']
        print(f'  {names[i]:2s}: {m}')
    print()
    print('Sound locks:')
    print('  BD step 9 → pool slot 6 (SY DUAL VCO)')
    print('  OH step 7 → pool slot 11 (HH LAB)')


if __name__ == '__main__':
    main()
