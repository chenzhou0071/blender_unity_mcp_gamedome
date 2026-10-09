"""IDW 长尾剪除: 对"非手臂区域"的 Arm/ForeArm/Hand 小权重按"到臂骨段距离"平滑衰减。
背景: IDW(1/d^3) 的长尾把手臂链权重扩散到背部(距臂轴>10cm)，摆臂时背部微边(rest 1-3mm)被
     "小权重差 × 大旋转位移"拉长 10-35mm。heat 场无此长尾。
做法: 每顶点 d = 到同侧 {Arm, ForeArm, Hand} 三骨段的最短距离;
     f = clip((0.10 - d) / 0.05, 0, 1); 手臂链权重 *= f; 再全组归一化 + 微值清理(0.005)。
     三角肌/上臂本体 d<0.05 → f=1 不动; 腋下过渡区 0.05-0.10 渐减; 背部 d>0.10 清零。
用法: blender.exe --background --factory-startup --python hero_rig_prune.py
"""
import bpy, os
import numpy as np

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
D_LO, D_HI = 0.05, 0.10

bpy.ops.wm.open_mainfile(filepath=BLEND)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
n = len(main.data.vertices)
co = np.empty(n * 3, dtype=np.float32)
main.data.vertices.foreach_get("co", co)
co = co.reshape(n, 3)
print("OPEN verts", n)

def seg_dist(P, h, t):
    h = np.array(h, dtype=np.float32)
    t = np.array(t, dtype=np.float32)
    vv = t - h
    L2 = float(vv @ vv) + 1e-12
    tt = np.clip(((P - h) @ vv) / L2, 0, 1)
    proj = h[None, :] + tt[:, None] * vv[None, :]
    return np.linalg.norm(P - proj, axis=1)

D = np.full(n, 1e9, dtype=np.float32)
for pfx in ("Left", "Right"):
    dd = np.full(n, 1e9, dtype=np.float32)
    for bn in ("Arm", "ForeArm", "Hand"):
        b = arm.data.bones[f"{pfx}{bn}"]
        dd = np.minimum(dd, seg_dist(co, b.head_local, b.tail_local))
    D = np.minimum(D, dd)

f = np.clip((D_HI - D) / (D_HI - D_LO), 0.0, 1.0)
print(f"DIST stats: min={D.min():.3f} f<1: {int((f < 1).sum())}  f==0: {int((f == 0).sum())}")

# 读取全量权重
groups = main.vertex_groups
ng = len(groups)
gi = {g.name: g.index for g in groups}
W = np.zeros((n, ng), dtype=np.float32)
for vi, v in enumerate(main.data.vertices):
    for ge in v.groups:
        W[vi, ge.group] = ge.weight
print("READ W", W.shape)

cols = [gi[f"{p}{bn}"] for p in ("Left", "Right") for bn in ("Arm", "ForeArm", "Hand")]
Wn = W.copy()
Wn[:, cols] *= f[:, None]
m = (f < 1.0) & (W.sum(1) > 0)
s = Wn.sum(1, keepdims=True)
Wn[m] = Wn[m] / (s[m] + 1e-12)
# 微值清理仅作用于受影响行
Wn[m][Wn[m] < 0.005] = 0.0
s2 = Wn.sum(1, keepdims=True)
Wn[m] = Wn[m] / (s2[m] + 1e-12)

aff = np.where(m)[0]
print("AFFECTED verts", len(aff))

# 写回: remove 旧值 → 逐点 add 新值（0.001 精度）
for j, g in enumerate(groups):
    old = aff[W[aff, j] > 0]
    if len(old):
        g.remove(old.tolist())
for i in aff:
    xi = Wn[i]
    nz = np.where(xi > 1e-4)[0]
    for j in nz:
        groups[int(j)].add([int(i)], float(np.rint(xi[j] * 1000) / 1000), 'REPLACE')
print("WRITE OK")

# 零权检查
zero = 0
for i in aff:
    if Wn[i].max() < 1e-6:
        zero += 1
print("ZERO in affected:", zero, "/", len(aff))

bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(f"SAVED {BLEND} {os.path.getsize(BLEND)}B")
print("PRUNE_DONE")
