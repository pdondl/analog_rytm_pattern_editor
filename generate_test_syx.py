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
DEFAULT_NOTE_OFF   = 0x0230  # default_note within track
DEFAULT_VELO_OFF   = 0x0231  # default_velocity within track
DEFAULT_LEN_OFF    = 0x0232  # default_note_len within track
NUM_STEPS_OFF      = 0x0235  # num_steps within track
SOUND_LOCK_OFF     = 0x0237  # sound_locks[64] within track
SPEED_OFF          = 0x0277  # flags_and_speed within track
TRIG_PROB_OFF      = 0x0278  # trig_probability within track

# Trig bits: 14 bits per step, packed in 112 bytes (64 steps × 14 bits = 896 bits = 112 bytes)
TRIG_ENABLE        = 0x0001
TRIG_SYN_PL_SW     = 0x0080
TRIG_SMP_PL_SW     = 0x0100
TRIG_ENV_PL_SW     = 0x0200
TRIG_LFO_PL_SW     = 0x0400
# Normal trig: enable + all retrigger switches on
TRIG_NORMAL        = TRIG_ENABLE | TRIG_SYN_PL_SW | TRIG_SMP_PL_SW | TRIG_ENV_PL_SW | TRIG_LFO_PL_SW

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


def make_pattern():
    """Create a test pattern with trigs on some tracks."""
    raw = bytearray(AR_PATTERN_V5_SZ)

    # Magic bytes
    raw[0:4] = b'\x00\x00\x00\x00'

    # Fill plock sequence area with 0xFF (unused)
    # 72 sequences × 66 bytes each, starting at offset 0x2091
    PLOCK_SEQS_BASE = 0x2091
    PLOCK_SEQ_SZ = 0x42  # 66 bytes
    NUM_PLOCK_SEQS = 72
    plock_end = PLOCK_SEQS_BASE + NUM_PLOCK_SEQS * PLOCK_SEQ_SZ
    for i in range(PLOCK_SEQS_BASE, plock_end):
        raw[i] = 0xFF

    # Default machines per track (typical AR default kit)
    track_configs = [
        # (machine, steps, speed, trig_steps, sound_locks)
        ('BD_HARD',     16, 2, [0, 4, 8, 12], {8: 5}),          # BD: 4-on-floor, step 9 → pool slot 6 (SY DUAL VCO)
        ('SD_CLASSIC',  16, 2, [4, 12], {}),                    # SD: backbeat
        ('RS_CLASSIC',  16, 2, [], {}),                          # RS: off
        ('CP_CLASSIC',  16, 2, [4, 12], {}),                    # CP: with snare
        ('BT_CLASSIC',  16, 2, [], {}),                          # BT: off
        ('XT_CLASSIC',  16, 2, [2, 6, 10, 14], {}),             # LT: offbeat 16ths
        ('CH_CLASSIC',  16, 2, [], {}),                          # MT: off
        ('OH_CLASSIC',  16, 2, [], {}),                          # HT: off
        ('CH_METALLIC', 16, 2, [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], {}),  # CH: every step
        ('OH_METALLIC', 16, 2, [2, 6, 10, 14], {6: 10}),       # OH: offbeat, step 7 → pool slot 11 (HH LAB)
        ('CY_RIDE',     16, 2, [0, 8], {}),                     # CY: every bar
        ('CB_CLASSIC',  16, 2, [4, 12], {}),                    # CB: offbeat
        ('BD_HARD',     16, 2, [], {}),                          # FX: off
    ]

    for t, (mach, steps, speed, trigs, slocks) in enumerate(track_configs):
        base = 4 + t * TRACK_V5_SZ

        # Trig bits (112 bytes starting at offset 0)
        trig_area = bytearray(raw[base:base + 112])
        for s in trigs:
            set_trig_flags(trig_area, s, TRIG_NORMAL)
        raw[base:base + 112] = trig_area

        # Notes: 0xFF = default
        for s in range(AR_NUM_STEPS):
            raw[base + 0x0070 + s] = 0xFF

        # Velocities: 0xFF = default
        for s in range(AR_NUM_STEPS):
            raw[base + 0x00B0 + s] = 0xFF

        # Note lengths: 0xFF = default
        for s in range(AR_NUM_STEPS):
            raw[base + 0x00F0 + s] = 0xFF

        # Micro timing: 0x00 = center
        for s in range(AR_NUM_STEPS):
            raw[base + 0x0130 + s] = 0x00

        # Retrig lengths: 0xFF = default
        for s in range(AR_NUM_STEPS):
            raw[base + 0x0170 + s] = 0xFF

        # Retrig rates: 0xFF = default
        for s in range(AR_NUM_STEPS):
            raw[base + 0x01B0 + s] = 0xFF

        # Sound locks: 0xFF = no lock
        for s in range(AR_NUM_STEPS):
            raw[base + SOUND_LOCK_OFF + s] = 0xFF
        for s, slot in slocks.items():
            raw[base + SOUND_LOCK_OFF + s] = slot

        # Num steps
        raw[base + NUM_STEPS_OFF] = steps

        # Speed (2 = 1x)
        raw[base + SPEED_OFF] = speed

        # Default note (C3 = 60), velocity (100), length, probability
        raw[base + DEFAULT_NOTE_OFF] = 60    # default_note
        raw[base + DEFAULT_VELO_OFF] = 100   # default_velocity
        raw[base + DEFAULT_LEN_OFF]  = 0x40  # default_note_length
        raw[base + TRIG_PROB_OFF]    = 100   # default_trig_probability

    # Pattern name at offset 0x3319 (FW1.70): 15 bytes
    name = b'TEST PATTERN\x00\x00\x00'
    name_off = AR_PATTERN_V5_SZ - 20  # approximate offset for name
    # Actually let's put the kit number at the right offset
    # Kit number at pattern offset: need to check
    # KIT_NUMBER_OFFSET is at a fixed position in the pattern
    # From the viewer: const KIT_NUMBER_OFFSET = 0x3320;  (approximately)
    # Let's set it to kit 0
    raw[0x3325] = 0x00  # kit number (0 = kit 1)

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
        'BT_CLASSIC', 'XT_CLASSIC', 'CH_CLASSIC', 'OH_CLASSIC',
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
