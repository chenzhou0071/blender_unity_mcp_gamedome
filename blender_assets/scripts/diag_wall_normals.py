"""诊断：4 面墙 M_Stone 面中法线朝内的面（Unity 透光白带嫌疑面）分布。

用法: blender.exe --background --factory-startup --python diag_wall_normals.py
判据: 面中心相对墙质心方向 d, 若 d·n < -0.30 则该面近似朝内。
对凸长方体墙壳有效；裂缝侧壁等少数面可能误报，看数量级与高度聚集性。
"""
import bpy
from mathutils import Vector

BLEND = r"E:\pro\blender_mcp\blender_assets\scenes\M3_kit.blend"
bpy.ops.wm.open_mainfile(filepath=BLEND)

for name in ("SM_Wall_A", "SM_Wall_B", "SM_Wall_C", "SM_Wall_D"):
    o = bpy.data.objects.get(name)
    if o is None:
        print(f"[DIAG] {name}: NOT FOUND")
        continue
    me = o.data
    cent = Vector((0.0, 0.0, 0.0))
    for v in me.vertices:
        cent += v.co
    cent /= max(len(me.vertices), 1)
    n_stone = n_in = 0
    buckets = {}
    ndirs = {}
    for p in me.polygons:
        if p.material_index != 0:  # 0 = M_Stone
            continue
        n_stone += 1
        d = (p.center - cent).normalized().dot(p.normal)
        if d < -0.30:
            n_in += 1
            b = round(p.center.z * 4) / 4.0
            buckets[b] = buckets.get(b, 0) + 1
            key = (round(p.normal.x, 1), round(p.normal.y, 1), round(p.normal.z, 1))
            ndirs[key] = ndirs.get(key, 0) + 1
    pct = 100.0 * n_in / max(n_stone, 1)
    print(f"[DIAG] {name}: stone={n_stone} inward={n_in} ({pct:.1f}%) cent={tuple(round(c,2) for c in cent)}")
    for k, v in sorted(ndirs.items(), key=lambda kv: -kv[1])[:6]:
        print(f"[DIAG]   dir~{k}: {v}")
    for k in sorted(buckets):
        print(f"[DIAG]   z~{k:5.2f}: {buckets[k]}")
print("[DIAG] done")
