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
    """30s loop：洞穴氛围（四轮试听：去水滴）——低频 swell（低通抬到 600Hz）+ 轻中频空气层（小喇叭可听）。"""
    n = int(dur * SR)
    base = lowpass(brown_noise(n, 0.015), alpha_for(600))
    out = [base[i] * (0.6 + 0.4 * math.sin(2 * math.pi * 0.05 * i / SR)) * 0.5 for i in range(n)]
    air = band_noise(white(n), 500, 1500)                # 空气层：中频轻层，异相 swell 缓起伏
    for i in range(n):
        swell2 = 0.6 + 0.4 * math.sin(2 * math.pi * 0.037 * i / SR + 1.3)
        out[i] += air[i] * swell2 * 0.16
    return out

def gen_fire_crackle(dur=10.0):
    """10s loop：宽频脆响火盆（五轮：参照用户实录音）——低频燃烧底噪 + 三层噼啪（高频碎点 / 宽频脆响 / 大爆）。"""
    n = int(dur * SR)
    out = [b * 0.10 for b in lowpass(brown_noise(n, 0.03), alpha_for(900))]  # ①燃烧底噪：0-900Hz 温热沙沙
    t = 0.0
    while True:                                          # ②碎点层：密集微小噼啪（3-10kHz、极短、很轻）
        t += random.expovariate(14.0)
        if t >= dur - 0.05:
            break
        start = int(t * SR)
        cn = int(0.04 * SR)
        pulse = band_noise(white(cn), 3000, 10000)
        amp = random.uniform(0.04, 0.12)
        tau = random.uniform(0.002, 0.005) * SR
        for i in range(cn):
            if start + i < n:
                out[start + i] += pulse[i] * math.exp(-i / tau) * amp
    t = 0.15
    while True:                                          # ③脆响层：宽带"啪"（600Hz 以上全开、~3/s）
        t += random.expovariate(3.0)
        if t >= dur - 0.1:
            break
        start = int(t * SR)
        cn = int(0.1 * SR)
        pulse = band_noise(white(cn), 600, 11000)        # 限高频端（参考：核心 3-9k、顶部渐弱）
        thud = band_noise(white(cn), 150, 500)           # 低频噗：线底部重一点（仿参考）
        amp = random.uniform(0.30, 0.60)
        tau = random.uniform(0.008, 0.018) * SR
        for i in range(cn):
            if start + i < n:
                out[start + i] += (pulse[i] + thud[i] * 0.35) * math.exp(-i / tau) * amp
    t = 0.5
    while True:                                          # ④大爆层：偶尔一声更响（~0.4/s）
        t += random.expovariate(0.4)
        if t >= dur - 0.1:
            break
        start = int(t * SR)
        cn = int(0.15 * SR)
        pulse = band_noise(white(cn), 500, 12000)
        thud = band_noise(white(cn), 120, 450)
        amp = random.uniform(0.75, 1.0)
        tau = random.uniform(0.012, 0.025) * SR
        for i in range(cn):
            if start + i < n:
                out[start + i] += (pulse[i] + thud[i] * 0.4) * math.exp(-i / tau) * amp
    return out

def gen_footstep(hi_fc, seed=1, dur=0.18, hi_amp=0.42, tau2_ms=8):
    """0.18s：参考式轻脚步（六轮：用户实录）——低频"扑"层（60-1200Hz、τ14ms）+ 中高频"哒"层（1200-hi_fc 二次滤波、快衰）。"""
    random.seed(seed)
    n = int(dur * SR)
    lo = band_noise(white(n), 60, 1200)
    hi = lowpass(band_noise(white(n), 1200, hi_fc), alpha_for(hi_fc))   # 二次滚降：15kHz 以上急降（贴参考）
    e1 = env(n, int(0.004 * SR), 0.014 * SR)
    e2 = env(n, int(0.002 * SR), tau2_ms / 1000.0 * SR)
    return [lo[i] * e1[i] * 0.55 + hi[i] * e2[i] * hi_amp for i in range(n)]

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
    """0.25s：清脆"咔-嗒"（MC 按钮风）——1.6-2.2kHz 宽频短脉冲（τ≈10ms）+ 轻石质共鸣，双响间隔 45ms。"""
    n = int(dur * SR)
    out = [0.0] * n
    for t0, amp, fc, tau in ((0.0, 1.0, 2000, 0.010), (0.045, 0.8, 1700, 0.012)):
        start = int(t0 * SR)
        cn = int(0.06 * SR)
        band = high_noise(white(cn), fc * 0.7)           # 宽频短脉冲（高频主导，非纯音→不刺）
        for i in range(cn):
            if start + i < n:
                out[start + i] += band[i] * math.exp(-i / (tau * SR)) * amp
    for i in range(int(0.06 * SR)):                      # 轻石质共鸣：给"实体感"的短 body
        out[i] += math.sin(2 * math.pi * 900 * i / SR) * math.exp(-i / (0.010 * SR)) * 0.25
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
        # 脚步/火盆/石门/推石/落地改用实录提取（tools/audio_extract.py 从 docs/milestones/M5/ref_audio/*.mp3 生成），
        # 不经本脚本合成，避免重跑时覆盖（对应 gen_* 函数保留便于回退）
        ("plate_click.wav", gen_plate_click(), 0.92),
        ("goal_chime.wav", gen_goal_chime(), 0.88),
    ]
    for name, samples, norm in jobs:
        write_wav(os.path.join(OUT, name), samples, normalize=norm)
        print("gen:", name, round(len(samples) / SR, 3), "s")
    print("OK audio generated %d files" % len(jobs))
    if "--preview" in sys.argv:
        preview_montage()

if __name__ == "__main__":
    main()
