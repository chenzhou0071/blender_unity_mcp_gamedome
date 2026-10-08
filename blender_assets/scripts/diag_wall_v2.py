"""诊断 v2：精确判据找"墙正面区域中法线朝内"的异常面（Unity 透光白带候选）。

判据: 面中心 y < -0.15（墙前侧区域, 墙正面 y≈-0.25）
      且 n.y > +0.2（法线朝 +y = 朝墙内）→ 从正面看会被 Unity 单面剔除。
输出: 每面墙异常面数量、高度分布、法线方向直方图；并导出红色标记对象。
用法: blender.exe --background --factory-startup --python diag_wall_v2.py
"""
import bpy, bmesh, os
from mathutils import Vector

BLEND = r"E:\pro\blender_mcp\blender_assets\scenes\M3_kit.blend"
OUT = r"E:\pro\blender_mcp\docs\milestones\M3"
bpy.ops.wm.open_mainfile(filepath=BLEND)

for name in ("SM_Wall_A", "SM_Wall_B", "SM_Wall_C", "SM_Wall_D"):
    o = bpy.data.objects.get(name)
    if o is None:
        print(f"[V2] {name}: NOT FOUND")
        continue
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    bad = []
    for f in bm.faces:
        if f.material_index != 0:
            continue
        c = f.calc_center_median()
        n = f.normal
        if c.y < -0.15 and n.y > 0.20:
            bad.append(f)
    # 统计
    buckets = {}
    ndirs = {}
    for f in bad:
        b = round(f.calc_center_median().z * 4) / 4.0
        buckets[b] = buckets.get(b, 0) + 1
        key = (round(f.normal.x, 1), round(f.normal.y, 1), round(f.normal.z, 1))
        ndirs[key] = ndirs.get(key, 0) + 1
    print(f"[V2] {name}: total_faces={len(bm.faces)} bad={len(bad)}")
    for k in sorted(buckets):
        print(f"[V2]   z~{k:5.2f}: {buckets[k]}")
    for k, v in sorted(ndirs.items(), key=lambda kv: -kv[1])[:8]:
        print(f"[V2]   dir~{k}: {v}")
    # 导出红色标记对象
    red = bpy.data.materials.get("M_DIAG_RED")
    if red is None:
        red = bpy.data.materials.new("M_DIAG_RED")
        red.use_nodes = True
        b = next(n for n in red.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        for s in b.inputs:
            if s.identifier == "Base Color":
                s.default_value = (1.0, 0.05, 0.05, 1.0)
            if s.identifier == "Emission Color":
                s.default_value = (1.0, 0.05, 0.05, 1.0)
            if s.identifier == "Emission Strength":
                s.default_value = 4.0
    bm2 = bmesh.new()
    vmap = {}
    for f in bad:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm2.verts.new(v.co)
            vs.append(vmap[v])
        try:
            nf = bm2.faces.new(vs)
            nf.normal_flip() if False else None
        except ValueError:
            pass
    me2 = bpy.data.meshes.new("DIAG_" + name)
    bm2.to_mesh(me2); bm2.free()
    ob2 = bpy.data.objects.new("DIAG_" + name, me2)
    bpy.context.scene.collection.objects.link(ob2)
    me2.materials.append(red)
    bm.free()
print("[V2] done")
