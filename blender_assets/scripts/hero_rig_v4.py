"""绑定 v4：肩关节解剖修正 —— Shoulder尾(=Arm头) 从 (±0.155, 0.310) 内移到肩窝 (±0.115, 0.306)，
再重跑代理 heat 权重（旧权重是旧转轴下的 heat 场，移骨后须重算）。heat 失败自动回退 IDW。
背景: 网格实测转轴在三角肌外缘(y=0.155)，肩窝中心应在 y≈0.115(三角肌球心/上臂圆柱轴线 z≈0.306)。
用法: blender.exe --background --factory-startup --python hero_rig_v4.py
"""
import bpy, os
import numpy as np

SAVE = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
PROXY_RATIO = 0.06
Y_SHO, Z_SHO = 0.115, 0.306   # 肩窝中心（网格实测）

bpy.ops.wm.open_mainfile(filepath=SAVE)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print("OPEN", main.name, len(main.data.vertices))

# —— 1) 肩关节修正: Shoulder.tail(=Arm.head, connected) 内移到肩窝 ——
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
for pfx, sgn in (("Left", 1), ("Right", -1)):
    eb[f"{pfx}Shoulder"].tail = (0.0, sgn * Y_SHO, Z_SHO)
bpy.ops.object.mode_set(mode='OBJECT')
for nm in ("LeftShoulder", "LeftArm", "RightShoulder", "RightArm"):
    b = arm.data.bones[nm]
    print(f"BONE {nm:14s} head=({b.head_local.x:+.3f},{b.head_local.y:+.3f},{b.head_local.z:+.3f}) "
          f"tail=({b.tail_local.x:+.3f},{b.tail_local.y:+.3f},{b.tail_local.z:+.3f}) len={b.length:.3f}")

# —— 2) 清权重 + 代理 heat 重算 ——
main.vertex_groups.clear()
main.parent = arm
if not any(m.type == 'ARMATURE' for m in main.modifiers):
    am = main.modifiers.new("Armature", 'ARMATURE')
    am.object = arm

def weight_counts(o):
    vg = {g.index: g.name for g in o.vertex_groups}
    counts = {n: 0 for n in vg.values()}
    for v in o.data.vertices:
        for g in v.groups:
            if g.weight > 0.05:
                counts[vg[g.group]] += 1
    return counts

proxy = main.copy()
proxy.data = main.data.copy()
proxy.name = "rig_proxy"
bpy.context.scene.collection.objects.link(proxy)
proxy.parent = None
proxy.matrix_world = main.matrix_world
for m in list(proxy.modifiers):
    proxy.modifiers.remove(m)

bpy.ops.object.select_all(action='DESELECT')
proxy.select_set(True)
bpy.context.view_layer.objects.active = proxy
mod = proxy.modifiers.new("dec2", 'DECIMATE')
mod.ratio = PROXY_RATIO
mod.use_collapse_triangulate = True
mod.use_symmetry = True
mod.symmetry_axis = 'Y'
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')
proxy.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
pc = weight_counts(proxy)
ok = sum(pc.values()) > 0
print("PROXY HEAT", "OK" if ok else "FAILED", sum(pc.values()))

if ok:
    bpy.ops.object.select_all(action='DESELECT')
    main.select_set(True)
    bpy.context.view_layer.objects.active = main
    dt = main.modifiers.new("wt", 'DATA_TRANSFER')
    dt.object = proxy
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.datalayout_transfer(modifier=dt.name)
    bpy.ops.object.modifier_move_to_index(modifier=dt.name, index=0)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    print("TRANSFER OK")
    bpy.data.objects.remove(proxy, do_unlink=True)
else:
    bpy.data.objects.remove(proxy, do_unlink=True)
    n = len(main.data.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    main.data.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    bones = [(b.name, np.array(b.head_local, dtype=np.float32),
              np.array(b.tail_local, dtype=np.float32)) for b in arm.data.bones]
    names = [nm for nm, _, _ in bones]
    D = np.empty((len(bones), n), dtype=np.float32)
    for i, (nm, h, t) in enumerate(bones):
        vv = t - h
        L2 = float(vv @ vv) + 1e-12
        tt = np.clip(((co - h) @ vv) / L2, 0, 1)
        proj = h[None, :] + tt[:, None] * vv[None, :]
        D[i] = np.linalg.norm(co - proj, axis=1)
    Dc = np.maximum(D - 0.02, 0.0) + 1e-5
    W = 1.0 / np.power(Dc, 3)
    K = 4
    idx = np.argpartition(-W, K, axis=0)[:K]
    mask = np.zeros(W.shape, dtype=bool)
    np.put_along_axis(mask, idx, True, axis=0)
    W = np.where(mask, W, 0.0)
    W /= (W.sum(0, keepdims=True) + 1e-12)
    print("IDW OK max", round(float(W.max()), 3), "top1_mean", round(float(W.max(0).mean()), 3))
    Wq = np.rint(W * 100).astype(np.int32)
    for i, nm in enumerate(names):
        g = main.vertex_groups.get(nm)
        if g is None:
            g = main.vertex_groups.new(name=nm)
        row = Wq[i]
        for lv in range(1, 101):
            sel = np.where(row == lv)[0]
            if len(sel):
                g.add(sel.tolist(), lv / 100.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    main.select_set(True)
    bpy.context.view_layer.objects.active = main
    main.vertex_groups.active_index = 0
    try:
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5,
                                           repeat=3, expand=0.0)
        bpy.ops.object.mode_set(mode='OBJECT')
        print("SMOOTH OK")
    except Exception as e:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        print("SMOOTH FAILED", e)

# —— 3) 检查 + 保存 ——
n = len(main.data.vertices)
zero = 0
for v in main.data.vertices:
    w = 0.0
    for g in v.groups:
        if g.weight > w:
            w = g.weight
    if w < 1e-6:
        zero += 1
print("ZERO:", zero, "/", n)

# 肩区 sanity: 三角肌区(y 0.06-0.16) 各骨权重均值
co = np.empty(n * 3, dtype=np.float32)
main.data.vertices.foreach_get("co", co)
co = co.reshape(n, 3)
mz = (np.abs(co[:, 0]) < 0.14) & (co[:, 1] > 0.06) & (co[:, 1] < 0.16) & (co[:, 2] > 0.28) & (co[:, 2] < 0.40)
gi = {g.name: g.index for g in main.vertex_groups}
for bname in ("LeftShoulder", "LeftArm", "LeftForeArm", "Spine2"):
    acc = np.zeros(n, dtype=np.float32)
    ji = gi.get(bname, -1)
    for v in main.data.vertices:
        for g in v.groups:
            if g.group == ji:
                acc[v.index] = g.weight
    print(f"DELTOID-W {bname:14s} n={int(mz.sum())} mean={acc[mz].mean():.3f} max={acc[mz].max():.3f}")

bpy.ops.wm.save_as_mainfile(filepath=SAVE)
print(f"SAVED {SAVE} {os.path.getsize(SAVE)}B")
print("V4_DONE")
