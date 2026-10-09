"""肩部短微边权重钳制 v3（去肩顶转移版）：对肩区短边(rest<3mm)且两端权重差大的边，迭代拉平两端权重。
背景: v4 移骨(IDW 重算)后微边量化台阶制造两端差异 → 90° 摆臂 max 拉伸比翻倍(9→19)；
     本脚本 = shoulder_fix 的通用钳制部分，去掉"肩顶权重挪给 Shoulder"
     （那是旧转轴下的权宜之计，转轴已修正到肩窝后不再需要）。
用法: blender.exe --background --factory-startup --python hero_rig_shoulder_fix3.py
"""
import bpy, os
import numpy as np

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
LEN_MAX = 0.003     # 短边阈值 3mm
DW_MIN = 0.08       # 两端权重差 L1 阈值
ROUNDS = 3          # 迭代轮数
BETA = 0.5          # 每轮混合系数

bpy.ops.wm.open_mainfile(filepath=BLEND)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
n = len(main.data.vertices)
co = np.empty(n * 3, dtype=np.float32)
main.data.vertices.foreach_get("co", co)
co = co.reshape(n, 3)
print("OPEN verts", n)

# 1) 读取全量权重矩阵 W (n, ngroups)
groups = main.vertex_groups
ng = len(groups)
gcol = {g.index: i for i, g in enumerate(groups)}
W = np.zeros((n, ng), dtype=np.float32)
for vi, v in enumerate(main.data.vertices):
    for ge in v.groups:
        W[vi, gcol[ge.group]] = ge.weight
print("READ W", W.shape)

# 2) 候选短边（肩区盒: |x|<0.19, 0.02<|y|<0.24, 0.19<z<0.43）
ne = len(main.data.edges)
ea = np.empty(ne * 2, dtype=np.int32)
main.data.edges.foreach_get("vertices", ea)
ea = ea.reshape(ne, 2)
rlen = np.linalg.norm(co[ea[:, 0]] - co[ea[:, 1]], axis=1)
pa = co[ea[:, 0]]
pb = co[ea[:, 1]]
def inbox(p):
    return (np.abs(p[:, 0]) < 0.19) & (np.abs(p[:, 1]) > 0.02) & \
           (np.abs(p[:, 1]) < 0.24) & (p[:, 2] > 0.19) & (p[:, 2] < 0.43)
m_zone = inbox(pa) | inbox(pb)
delta = np.abs(W[ea[:, 0]] - W[ea[:, 1]]).sum(1)
sel = np.where(m_zone & (rlen < LEN_MAX) & (delta > DW_MIN))[0]
print(f"SHORT-EDGE zone_cand={int((m_zone & (rlen < LEN_MAX)).sum())} selected={len(sel)}")
if len(sel) == 0:
    print("NO CANDIDATES - nothing to clamp")
else:
    a = ea[sel, 0]
    b = ea[sel, 1]
    affected = np.unique(np.concatenate([a, b]))
    print("AFFECTED verts", len(affected))

    # 3) 迭代钳制：每点向"所连选中边的中点权重"均值混合
    Wn = W.copy()
    for r in range(ROUNDS):
        s = 0.5 * (Wn[a] + Wn[b])
        accS = np.zeros((n, ng), dtype=np.float32)
        cntS = np.zeros(n, dtype=np.int32)
        np.add.at(accS, a, s)
        np.add.at(accS, b, s)
        np.add.at(cntS, a, 1)
        np.add.at(cntS, b, 1)
        m = cntS > 0
        Wn[m] = (1 - BETA) * Wn[m] + BETA * (accS[m] / cntS[m, None])
        d2 = np.abs(Wn[a] - Wn[b]).sum(1)
        print(f"ROUND {r+1} n={len(sel)} pairL1 mean={d2.mean():.4f} max={d2.max():.4f}")

    # 4) top4 稀疏化 + 小值归零 + 归一化（仅 affected）
    sub = Wn[affected]
    idx4 = np.argpartition(-sub, 4, axis=1)[:, :4]
    m4 = np.zeros(sub.shape, dtype=bool)
    np.put_along_axis(m4, idx4, True, axis=1)
    sub = np.where(m4, sub, 0.0)
    sub[sub < 0.005] = 0.0
    sub /= (sub.sum(1, keepdims=True) + 1e-12)
    Wn[affected] = sub
    print("SPARSE OK")

    # 5) 写回：先 remove 旧值 → 逐点 add 新值（0.001 精度）
    for j, g in enumerate(groups):
        old_sel = affected[W[affected, j] > 0]
        if len(old_sel):
            g.remove(old_sel.tolist())
    for i in affected:
        xi = Wn[i]
        nz = np.where(xi > 0)[0]
        for j in nz:
            groups[int(j)].add([int(i)], float(np.rint(xi[j] * 1000) / 1000), 'REPLACE')
    print("WRITE OK")

    # 6) 零权检查（affected 内）
    zero = 0
    for i in affected:
        if Wn[i].max() < 1e-6:
            zero += 1
    print("ZERO in affected:", zero, "/", len(affected))

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"SAVED {BLEND} {os.path.getsize(BLEND)}B")
print("SHOULDER_FIX3_DONE")
