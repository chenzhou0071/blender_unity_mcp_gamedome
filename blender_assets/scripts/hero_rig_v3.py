"""绑定 v3：骨微调后重试 heat → 仍失败则 IDW 反距离权重(无截断, top4, 量化写回) + 平滑。
用法: blender.exe --background --factory-startup --python hero_rig_v3.py
说明: envelope+硬补权的质量不达标（撕裂/生硬）；IDW 为保底平滑方案。
"""
import bpy, os
import numpy as np

SAVE = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
PROXY_RATIO = 0.06

bpy.ops.wm.open_mainfile(filepath=SAVE)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print("OPEN", main.name, len(main.data.vertices))

# 0) 清权重组，确保绑定关系
main.vertex_groups.clear()
main.parent = arm
if not any(m.type == 'ARMATURE' for m in main.modifiers):
    am = main.modifiers.new("Armature", 'ARMATURE')
    am.object = arm

# 1) 骨微调：抬升"半埋在网格表面"的脚部骨（助 heat 求解）
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
for nm in ("LeftFoot", "RightFoot"):
    eb[nm].tail.z += 0.015
for nm in ("LeftToeBase", "RightToeBase"):
    eb[nm].tail.z += 0.015
bpy.ops.object.mode_set(mode='OBJECT')
print("BONES adjusted (foot/toe raised)")

def weight_counts(o):
    vg = {g.index: g.name for g in o.vertex_groups}
    counts = {n: 0 for n in vg.values()}
    for v in o.data.vertices:
        for g in v.groups:
            if g.weight > 0.05:
                counts[vg[g.group]] += 1
    return counts

# 2) 代理 heat 重试
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
    # —— heat 路线：传递到主模 ——
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
    # —— IDW 路线：直接对主模计算 ——
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
    near = D.argmin(0)
    for i, nm in enumerate(names):
        print("NEAR", nm, int((near == i).sum()))
    Dc = np.maximum(D - 0.02, 0.0) + 1e-5
    W = 1.0 / np.power(Dc, 3)
    K = 4
    idx = np.argpartition(-W, K, axis=0)[:K]  # 取 top4（对负值取最小=原值最大）
    mask = np.zeros(W.shape, dtype=bool)
    np.put_along_axis(mask, idx, True, axis=0)
    W = np.where(mask, W, 0.0)
    W /= (W.sum(0, keepdims=True) + 1e-12)
    print("IDW OK max", round(float(W.max()), 3),
          "top1_mean", round(float(W.max(0).mean()), 3))
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
        print("VGW", nm, int((row > 0).sum()))
    # 权重平滑（3 轮；需 weight paint 模式）
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

# 3) 零权检查
zero = 0
for v in main.data.vertices:
    w = 0.0
    for g in v.groups:
        if g.weight > w:
            w = g.weight
    if w < 1e-6:
        zero += 1
print("ZERO after fix:", zero, "/", len(main.data.vertices))

bpy.ops.wm.save_as_mainfile(filepath=SAVE)
print(f"SAVED {SAVE} {os.path.getsize(SAVE)}B")
print("V3_DONE")
