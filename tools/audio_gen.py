"""M5-1 音效合成（纯标准库）：按计划参数表生成 11 个 WAV 到 Unity 工程（起跳音效经用户试听移除）。
输出: game/3D-Demo/Assets/Audio/*.wav （44.1kHz / 16bit / mono）
可选: python audio_gen.py --preview
      另生成 docs/milestones/M5/audio_preview_all.wav（试听拼合文件，长音效节选）
"""
import wave, struct, math, random, os, sys

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "game", "3D-Demo", "Assets", "Audio")
PREVIEW = os.path.join(HERE, "..", "docs", "milestones", "M5", "audio_preview_all.wav")

# ---------- 基础工具 ----------
def write_wav(path, samples, normalize=0.9):
    """samples: -1..1 float 列表；normalize>0 时先按峰值归一化到该值（防削波）。"""
    if normalize:
        peak = max(abs(s) for s in samples) or 1.0
        k = normalize / peak
        samples = [s * k for s in samples]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))

def lowpass(sig, alpha):
    """一阶低通（alpha 越大截止频率越高）。"""
    out, prev = [], 0.0
    for s in sig:
        prev += alpha * (s - prev)
        out.append(prev)
    return out

def alpha_for(fc):
    """一阶低通 alpha ← 目标截止频率（Hz）。"""
    return 1.0 - math.exp(-2.0 * math.pi * fc / SR)

def brown_noise(n, step=0.02):
    """随机游走棕噪声（归一化到 ±1）。"""
    v, out = 0.0, []
    for _ in range(n):
        v = max(-1, min(1, v + random.uniform(-step, step)))
        out.append(v)
    return out

def white(n):
    return [random.uniform(-1, 1) for _ in range(n)]

def env(n, attack, decay):
    """AD 包络：attack 样本内渐起，其后按 decay 时间常数指数衰减。"""
    return [min(1.0, i / max(1, attack)) * math.exp(-max(0, i - attack) / max(1.0, decay)) for i in range(n)]

def band_noise(noise, fc_lo, fc_hi):
    """简易带通 = 低通(高频) - 低通(低频)。"""
    lo = lowpass(noise, alpha_for(fc_lo))
    hi = lowpass(noise, alpha_for(fc_hi))
    return [h - l for h, l in zip(hi, lo)]

def high_noise(noise, fc):
    """简易高通 = 原信号 - 低通。"""
    lp = lowpass(noise, alpha_for(fc))
    return [x - y for x, y in zip(noise, lp)]

# ---------- 10 个音效生成器 ----------
def gen_ambient_temple(dur=30.0):
    """30s loop：棕噪声低速滤波 + 0.05Hz 幅度起伏 + 每 4-9s 随机水滴（1.2kHz 指数衰减 80ms）。"""
    n = int(dur * SR)
    base = lowpass(brown_noise(n, 0.015), alpha_for(180))
    out = [base[i] * (0.6 + 0.4 * math.sin(2 * math.pi * 0.05 * i / SR)) * 0.5 for i in range(n)]
    dn = int(0.4 * SR)                                   # 水滴长度（5τ）
    t = random.uniform(4, 9)
    while t < dur - 0.5:
        start = int(t * SR)
        for i in range(dn):
            if start + i < n:
                out[start + i] += 0.5 * math.sin(2 * math.pi * 1200 * i / SR) * math.exp(-i / (0.08 * SR))
        t += random.uniform(4, 9)
    return out

def gen_fire_crackle(dur=10.0):
    """10s loop：低幅棕噪声底 + 随机噼啪（细噼 70% 高通 900Hz / 闷噗 30% 带通 300-700Hz），整体偏闷。"""
    n = int(dur * SR)
    out = [b * 0.20 for b in lowpass(brown_noise(n, 0.03), alpha_for(350))]
    t = 0.15
    while True:
        t += random.expovariate(5.5)                     # 平均 5.5 个/秒
        if t >= dur - 0.1:
            break
        start = int(t * SR)
        amp = random.uniform(0.35, 0.8)
        if random.random() < 0.7:                        # 细噼：降亮 + 拉长尾（15-30ms）
            cn = int(random.uniform(0.03, 0.07) * SR)
            tau = random.uniform(0.012, 0.03) * SR
            pulse = high_noise(white(cn), 900)
        else:                                            # 闷噗：低频爆（50-100ms）
            cn = int(random.uniform(0.05, 0.1) * SR)
            tau = random.uniform(0.02, 0.045) * SR
            pulse = band_noise(white(cn), 300, 700)
        for i in range(cn):
            if start + i < n:
                out[start + i] += pulse[i] * math.exp(-i / tau) * amp
    return out

def gen_footstep(fc, dur=0.25, seed=1, tau_ms=60, spread=1.8, thump_hz=0, thump_amp=0.0):
    """0.25s：带通噪声 burst（中心 fc、带宽 spread、尾音 tau_ms）+ 可选低频夯击层。
    4 个变体在音高/亮度/尾音/夯击上拉开差异。"""
    random.seed(seed)
    n = int(dur * SR)
    noise = white(n)
    band = band_noise(noise, fc * 0.55, fc * spread)
    e = env(n, int(0.02 * SR), int(tau_ms / 1000.0 * SR))
    out = [band[i] * e[i] * 0.8 for i in range(n)]
    if thump_hz:
        for i in range(n):
            out[i] += math.sin(2 * math.pi * thump_hz * i / SR) * math.exp(-i / (0.04 * SR)) * thump_amp
    return out

def gen_land(dur=0.30):
    """0.30s：低频 thud（90Hz）+ 噪声，更重尾音（τ 100ms）。"""
    n = int(dur * SR)
    out = []
    for i in range(n):
        t = i / SR
        e = min(1.0, i / (0.01 * SR)) * math.exp(-max(0, i - 0.01 * SR) / (0.10 * SR))
        s = (math.sin(2 * math.pi * 90 * t) * 0.75 + random.uniform(-1, 1) * 0.35) * e
        out.append(s)
    return out

def gen_block_grind(dur=2.0):
    """2s loop：带通噪声 200-800Hz 三角扫频 + 8Hz 周期性幅度调制。"""
    n = int(dur * SR)
    noise = white(n)
    out, lo_lp, hi_lp = [], 0.0, 0.0
    for i in range(n):
        tri = 1 - abs(2 * (i / n) - 1)                   # 0→1→0
        fc = 200 + 600 * tri
        lo_lp += alpha_for(fc * 0.6) * (noise[i] - lo_lp)
        hi_lp += alpha_for(fc * 1.6) * (noise[i] - hi_lp)
        am = 0.55 + 0.45 * math.sin(2 * math.pi * 8 * i / SR)
        out.append((hi_lp - lo_lp) * am)
    return out

def gen_plate_click(dur=0.25):
    """0.25s：石板压下的"咔-哒"双响（1.1k/850Hz clack + 160Hz 低频 thud 层），更沉。"""
    n = int(dur * SR)
    out = [0.0] * n
    for t0, amp, f, tau in ((0.0, 1.0, 1100, 0.02), (0.09, 0.7, 850, 0.025)):
        start = int(t0 * SR)
        cn = int(0.08 * SR)
        for i in range(cn):
            if start + i < n:
                e = math.exp(-i / (tau * SR))
                s = math.sin(2 * math.pi * f * i / SR) * 0.7 + random.uniform(-1, 1) * 0.3
                out[start + i] += s * e * amp
    for i in range(n):                                   # 低频 thud 层：压下去的"咚"（τ50ms）
        out[i] += math.sin(2 * math.pi * 160 * i / SR) * math.exp(-i / (0.05 * SR)) * 0.5
    return out

def gen_door_rumble(dur=3.0):
    """3s：低频噪声（60-150Hz）渐强 2s + 1s 衰减尾。"""
    n = int(dur * SR)
    band = band_noise(white(n), 60, 150)
    out = []
    for i in range(n):
        t = i / SR
        e = (t / 2.0) ** 1.5 if t < 2.0 else math.exp(-(t - 2.0) / 0.35)
        out.append(band[i] * e)
    return out

def gen_goal_chime(dur=2.5):
    """2.5s：C5-E5-G5 正弦叠加，各错开 150ms 起音、指数衰减 + 轻微 detune。"""
    n = int(dur * SR)
    out = [0.0] * n
    for f, t0 in ((523.25, 0.0), (659.25, 0.15), (783.99, 0.30)):
        start, f2 = int(t0 * SR), f * 1.003        # +5 cent 微失谐副本
        for i in range(n - start):
            e = math.exp(-i / (0.7 * SR)) * min(1.0, i / (0.005 * SR))
            s = (math.sin(2 * math.pi * f * i / SR) + 0.6 * math.sin(2 * math.pi * f2 * i / SR)) / 1.6
            out[start + i] += s * e * 0.5
    return out

# ---------- 试听拼合（--preview） ----------
NAMES = ["ambient_temple.wav", "fire_crackle.wav",
         "footstep_stone_1.wav", "footstep_stone_2.wav", "footstep_stone_3.wav", "footstep_stone_4.wav",
         "land.wav", "block_grind.wav", "plate_click.wav", "door_rumble.wav", "goal_chime.wav"]

def preview_montage():
    cut = {"ambient_temple.wav": 4.0, "fire_crackle.wav": 4.0}   # 长音效节选
    gap = [0.0] * int(0.5 * SR)
    alls = []
    for nm in NAMES:
        with wave.open(os.path.join(OUT, nm), "rb") as w:
            k = w.getnframes()
            raw = w.readframes(k)
        s = [v / 32768.0 for v in struct.unpack("<%dh" % k, raw)]
        alls.extend(s[:int(cut.get(nm, 1e9) * SR)])
        alls.extend(gap)
    write_wav(PREVIEW, alls, normalize=0)                        # 已归一段，montage 不再二级归一
    print("preview:", os.path.normpath(PREVIEW), len(alls) / SR, "s")

def main():
    random.seed(42)
    jobs = [
        ("ambient_temple.wav", gen_ambient_temple(), 0.5),
        ("fire_crackle.wav", gen_fire_crackle(), 0.9),
        # 脚步 4 变体：低闷/中浑/亮尾/高脆，拉开区分度（首轮试听反馈"没区别"）
        ("footstep_stone_1.wav", gen_footstep(320, seed=1, tau_ms=45, spread=1.6, thump_hz=110, thump_amp=0.35), 0.92),
        ("footstep_stone_2.wav", gen_footstep(480, seed=2, tau_ms=75, spread=2.0, thump_hz=95, thump_amp=0.22), 0.92),
        ("footstep_stone_3.wav", gen_footstep(720, seed=3, tau_ms=95, spread=2.4), 0.92),
        ("footstep_stone_4.wav", gen_footstep(980, seed=4, tau_ms=40, spread=1.5, thump_hz=150, thump_amp=0.30), 0.92),
        ("land.wav", gen_land(), 0.92),
        ("block_grind.wav", gen_block_grind(), 0.9),
        ("plate_click.wav", gen_plate_click(), 0.92),
        ("door_rumble.wav", gen_door_rumble(), 0.9),
        ("goal_chime.wav", gen_goal_chime(), 0.88),
    ]
    for name, samples, norm in jobs:
        write_wav(os.path.join(OUT, name), samples, normalize=norm)
        print("gen:", name, round(len(samples) / SR, 3), "s")
    print("OK audio generated %d files" % len(jobs))
    if "--preview" in sys.argv:
        preview_montage()

main()
