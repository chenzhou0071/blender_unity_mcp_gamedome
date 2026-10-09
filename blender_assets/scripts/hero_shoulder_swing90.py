"""肩关节 90° 摆动验证：大臂前平举/后平举/前上120°(攀爬抓握) 三方向 × 侧视+前3/4。
目的: 回答"手臂从肩膀摆动 90° 时肩部形态是否合格"（跑步式小摆幅之外的极限工况）。
只读不保存。用法: blender.exe --background --factory-startup --python hero_shoulder_swing90.py
输出: docs/milestones/M4/hero_shoulder_swing90.png(上排=侧视, 下排=前3/4; 列=前90/后90/前上120)
"""
import bpy, os, math
import numpy as np
from mathutils import Vector, Matrix

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
OUT = r"E:\pro\blender_mcp\docs\milestones\M4\hero_shoulder_swing90.png"

bpy.ops.wm.open_mainfile(filepath=BLEND)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
n0 = len(main.data.vertices)
co0 = np.empty(n0 * 3)
main.data.vertices.foreach_get("co", co0)
co0 = co0.reshape(n0, 3)
print("OPEN verts", n0)

# —— 场景 ——
gm = bpy.data.materials.new("G"); gm.use_nodes = True
gb = next(x for x in gm.node_tree.nodes if x.type == 'BSDF_PRINCIPLED')
gb.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1)
gb.inputs["Roughness"].default_value = 0.95
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, -0.5005))
bpy.context.object.data.materials.append(gm)

sd = bpy.data.lights.new("S", type='SUN'); sd.energy = 3.2
sun = bpy.data.objects.new("S", sd); bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (0.95, 0.15, 0.5)
fd = bpy.data.lights.new("F", type='SUN'); fd.energy = 1.6
fill = bpy.data.objects.new("F", fd); bpy.context.scene.collection.objects.link(fill)
fill.rotation_euler = (1.15, -0.25, -2.3)

cd = bpy.data.cameras.new("C"); cd.lens = 50
cam = bpy.data.objects.new("C", cd); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in engines:
        bpy.context.scene.render.engine = cand
        break
sc = bpy.context.scene
sc.render.resolution_x = 640
sc.render.resolution_y = 640

def shoot(loc, target, path):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

# —— 姿势工具 ——
def wrot(bone, axis, deg):
    pb = arm.pose.bones[bone]
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    pb.matrix_basis = pb.bone.matrix_local.inverted() @ R @ pb.bone.matrix_local

def walign2(bone, target_dir):
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    M = pb.matrix.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(target_dir).normalized())
    newM = (q.to_matrix().to_4x4() @ M.to_3x3().to_4x4()).to_4x4()
    newM.translation = M.translation
    pb.matrix = newM
    bpy.context.view_layer.update()

def clear_pose():
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)

# 三方向 90°+ 摆臂（大臂绕肩摆动；前臂微弯 20-30°）
POSES = [
    ("fwd90",  [('world', 'LeftArm', (1.0, 0.12, 0.06)),
                ('world', 'RightArm', (1.0, -0.12, 0.06)),
                ('world', 'LeftForeArm', (0.82, 0.10, 0.56)),
                ('world', 'RightForeArm', (0.82, -0.10, 0.56))]),
    ("back90", [('world', 'LeftArm', (-1.0, 0.12, 0.06)),
                ('world', 'RightArm', (-1.0, -0.12, 0.06)),
                ('world', 'LeftForeArm', (-0.88, 0.12, -0.44)),
                ('world', 'RightForeArm', (-0.88, -0.12, -0.44))]),
    ("fwd120", [('world', 'LeftArm', (0.82, 0.25, 0.51)),
                ('world', 'RightArm', (0.82, -0.25, 0.51)),
                ('world', 'LeftForeArm', (0.70, 0.20, 0.68)),
                ('world', 'RightForeArm', (0.70, -0.20, 0.68))]),
]

def apply(ops):
    clear_pose()
    for op in ops:
        if op[0] == 'rot':
            wrot(op[1], op[2], op[3])
        else:
            walign2(op[1], op[2])
    bpy.context.view_layer.update()

# 肩区边（拉伸统计）
ne = len(main.data.edges)
ea = np.empty(ne * 2, dtype=np.int32)
main.data.edges.foreach_get("vertices", ea)
ea = ea.reshape(ne, 2)
rlen = np.linalg.norm(co0[ea[:, 0]] - co0[ea[:, 1]], axis=1)
mid = (co0[ea[:, 0]] + co0[ea[:, 1]]) / 2
mE = (mid[:, 2] > 0.24) & (mid[:, 2] < 0.42) & (np.abs(mid[:, 1]) > 0.02) & \
     (np.abs(mid[:, 1]) < 0.28) & (np.abs(mid[:, 0]) < 0.2)

CS = (0.0, 2.3, 0.85)     # 侧视（+y 侧, 前后摆动最清晰）
CQ = (1.6, 1.5, 0.80)     # 前 3/4
CF = (2.3, 0.0, 0.85)     # 正面
TGT = (0.0, 0.0, 0.05)

for name, ops in POSES:
    apply(ops)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = main.evaluated_get(dg)
    me = ev.to_mesh()
    m = len(me.vertices)
    co = np.empty(m * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    ev.to_mesh_clear()
    wlen = np.linalg.norm(co[ea[:, 0]] - co[ea[:, 1]], axis=1)
    ratio = wlen / np.maximum(rlen, 1e-9)
    print(f"POSE {name:6s} edge ratio shoulder p99={np.percentile(ratio[mE], 99):.3f} max={ratio[mE].max():.3f}")
    shoot(CS, TGT, OUT.replace('.png', f'_{name}_s.png'))
    shoot(CQ, TGT, OUT.replace('.png', f'_{name}_q.png'))
    shoot(CF, TGT, OUT.replace('.png', f'_{name}_f.png'))

# —— 拼图 2 行 × 3 列（上=侧视, 下=前3/4）——
order = ["fwd90_s", "back90_s", "fwd120_s", "fwd90_q", "back90_q", "fwd120_q"]
imgs = [bpy.data.images.load(OUT.replace('.png', f'_{t}.png')) for t in order]
w, h = imgs[0].size
canvas = np.zeros((h * 2, w * 3, 4), dtype=np.float32)
for i, im in enumerate(imgs):
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    r, c = i // 3, i % 3
    canvas[(1 - r) * h:(2 - r) * h, c * w:(c + 1) * w] = px
out = bpy.data.images.new("sheet", width=w * 3, height=h * 2, alpha=True)
out.pixels.foreach_set(canvas.ravel())
out.filepath_raw = OUT
out.file_format = 'PNG'
out.save()
print(f"saved {OUT} {os.path.getsize(OUT)}B")

# —— 正面拼图 1 行 × 3 列 ——
OUTF = OUT.replace('.png', '_front.png')
order_f = ["fwd90_f", "back90_f", "fwd120_f"]
imgs_f = [bpy.data.images.load(OUT.replace('.png', f'_{t}.png')) for t in order_f]
canvas_f = np.zeros((h, w * 3, 4), dtype=np.float32)
for i, im in enumerate(imgs_f):
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    canvas_f[:, i * w:(i + 1) * w] = px
out_f = bpy.data.images.new("sheet_f", width=w * 3, height=h, alpha=True)
out_f.pixels.foreach_set(canvas_f.ravel())
out_f.filepath_raw = OUTF
out_f.file_format = 'PNG'
out_f.save()
print(f"saved {OUTF} {os.path.getsize(OUTF)}B")
print("SWING90_DONE")
