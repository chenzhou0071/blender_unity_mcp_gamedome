"""M5-1 音效波形自检：对 audio_gen.py 产物做 5 项检查。
检查项: 文件存在 / 时长偏差≤10% / 峰值≤0.99(不削波) / RMS∈[-30,-12]dB / 前1s非静音(>-60dB)
用法: python tools/audio_check.py   （全过打印表格并退出码 0；任一失败退出码 1）
"""
import wave, struct, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "..", "game", "3D-Demo", "Assets", "Audio")

TARGETS = [
    ("ambient_temple.wav", 30.0),
    ("fire_crackle.wav", 10.0),
    ("footstep_stone_1.wav", 0.25),
    ("footstep_stone_2.wav", 0.25),
    ("footstep_stone_3.wav", 0.25),
    ("footstep_stone_4.wav", 0.25),
    ("land.wav", 0.30),
    ("block_grind.wav", 2.0),
    ("plate_click.wav", 0.25),
    ("door_rumble.wav", 3.0),
    ("goal_chime.wav", 2.5),
]

def read_wav(path):
    with wave.open(path, "rb") as w:
        n, sr = w.getnframes(), w.getframerate()
        raw = w.readframes(n)
    return [v / 32768.0 for v in struct.unpack("<%dh" % n, raw)], sr

def rms_db(samples):
    if not samples:
        return -120.0
    m = math.sqrt(sum(s * s for s in samples) / len(samples))
    return 20 * math.log10(m) if m > 1e-9 else -120.0

def main():
    ok_all = True
    print("%-22s %8s %8s %6s %8s %8s  %s" % ("file", "dur_t", "dur_a", "dev%", "peak", "rms_dB", "head_dB"))
    print("-" * 82)
    for name, target in TARGETS:
        path = os.path.join(AUDIO, name)
        if not os.path.isfile(path):
            print("%-22s  MISSING" % name); ok_all = False; continue
        s, sr = read_wav(path)
        dur = len(s) / sr
        dev = abs(dur - target) / target * 100.0
        peak = max(abs(v) for v in s) if s else 0.0
        rms = rms_db(s)
        head = rms_db(s[:int(min(1.0, dur) * sr)])
        checks = [
            dev <= 10.0,
            peak <= 0.99,
            -30.0 <= rms <= -12.0,
            head > -60.0,
        ]
        ok = all(checks)
        ok_all &= ok
        print("%-22s %8.3f %8.3f %5.1f%% %8.3f %8.1f %8.1f  %s"
              % (name, target, dur, dev, peak, rms, head, "PASS" if ok else "FAIL"))
    print("-" * 82)
    print("ALL PASS" if ok_all else "FAILED")
    sys.exit(0 if ok_all else 1)

main()
