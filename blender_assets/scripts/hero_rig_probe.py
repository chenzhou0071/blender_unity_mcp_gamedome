"""骨架关节探测：对减面后几何做顶点分布统计，辅助确定骨骼关节位置。
用法: blender.exe --background --factory-startup --python hero_rig_probe.py
"""
import bpy
import numpy as np

GLB = r"E:\pro\blender_mcp\blender_assets\import\hero_highpoly.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

meshes = [o for o in bpy.data.objects if o.type == 'MESH']

# bbox 原始（决定对称轴/错开轴）
def bbox(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ __import__('mathutils').Vector(c))
    mn = np.array([min(p[i] for p in pts) for i in range(3)])
    mx = np.array([max(p[i] for p in pts) for i in range(3)])
    return mn, mx

mn0, mx0 = bbox(meshes)
dims0 = mx0 - mn0
thin_axis = int(np.argmin(dims0))
sym_axis = 0 if dims0[0] >= dims0[1] else 1
print(f"PRE dims={dims0.round(3)} thin={'XYZ'[thin_axis]} sym={'XYZ'[sym_axis]}")

# 与建骨流程一致：先减面到最终几何
for o in meshes:
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    mod = o.modifiers.new("dec", 'DECIMATE')
    mod.ratio = 0.30
    mod.use_collapse_triangulate = True
    mod.use_symmetry = True
    mod.symmetry_axis = 'XYZ'[sym_axis]
    bpy.ops.object.modifier_apply(modifier=mod.name)

chunks = []
total = 0
for o in meshes:
    n = len(o.data.vertices)
    arr = np.empty(n * 3, dtype=np.float64)
    o.data.vertices.foreach_get("co", arr)
    arr = arr.reshape(n, 3)
    m = np.array(o.matrix_world)
    hom = np.c_[arr, np.ones(n)]
    chunks.append((hom @ m.T)[:, :3])
    total += n
P = np.vstack(chunks)
print(f"TOTAL verts={total}")

mn = P.min(0); mx = P.max(0); dims = mx - mn
print("DIMS x=%.3f y=%.3f z=%.3f mins=(%.3f,%.3f,%.3f) maxs=(%.3f,%.3f,%.3f)"
      % (*dims, *mn, *mx))
z0, H = mn[2], dims[2]

print("=== Z-BAND 2%% (x[min,max] y[min,max] n) ===")
for i in range(50):
    lo = z0 + H * i / 50; hi = z0 + H * (i + 1) / 50
    sel = P[(P[:, 2] >= lo) & (P[:, 2] < hi)]
    if len(sel) == 0:
        print(f"{i*2:3d}% empty")
        continue
    print(f"{i*2:3d}% x[{sel[:,0].min():+.3f},{sel[:,0].max():+.3f}] "
          f"y[{sel[:,1].min():+.3f},{sel[:,1].max():+.3f}] n={len(sel)}")

print("=== LEG y-percentile by z ===")
for pct in (3, 8, 15, 22, 30, 38, 46):
    sel = P[(P[:, 2] >= z0 + H * pct / 100) & (P[:, 2] < z0 + H * (pct + 1.5) / 100)]
    if len(sel) < 20:
        continue
    qy = np.percentile(sel[:, 1], [3, 25, 50, 75, 97])
    qx = np.percentile(sel[:, 0], [3, 97])
    print(f"z{pct:2d}% y[p3..p97]={qy.round(3)} x[p3..p97]={qx.round(3)} n={len(sel)}")

Ymax = max(abs(mn[1]), abs(mx[1]))
print(f"=== ARM |y|>{Ymax*0.55:.3f} ===")
arm = P[np.abs(P[:, 1]) > Ymax * 0.55]
if len(arm):
    a_lo, a_hi = arm[:, 2].min(), arm[:, 2].max()
    print(f"arm z[{a_lo:.3f},{a_hi:.3f}] n={len(arm)}")
    print("=== Y-BAND 5%% (z_c[zmin,zmax] x_c n) in arm-z-band ===")
    for i in range(-20, 20):
        lo = 2 * Ymax * i / 20 - Ymax; hi = lo + 2 * Ymax / 20
        sel = P[(P[:, 1] >= lo) & (P[:, 1] < hi)]
        sa = sel[(sel[:, 2] >= a_lo) & (sel[:, 2] <= a_hi)]
        if len(sa) < 10:
            continue
        side = "R" if (lo + hi) / 2 < 0 else "L"
        print(f"y[{lo:+.3f},{hi:+.3f}] {side}: z_c={sa[:,2].mean():.3f}"
              f"[{sa[:,2].min():.3f},{sa[:,2].max():.3f}] x_c={sa[:,0].mean():+.3f} n={len(sa)}")

print("=== HEAD z>85% ===")
hd = P[P[:, 2] > z0 + H * 0.85]
if len(hd):
    print(f"head y[{hd[:,1].min():+.3f},{hd[:,1].max():+.3f}] "
          f"x[{hd[:,0].min():+.3f},{hd[:,0].max():+.3f}] n={len(hd)}")
print("PROBE DONE")
