"""姿势测试渲染器 v2：清理碎权重 → 4 组动作姿势（走/蹲/瞄/扭）× 2 视角 → 拼图 + 位移异常检测。
用法: blender.exe --background --factory-startup --python hero_pose_render.py
输出: docs/milestones/M4/hero_rig_pose.png（4 列=姿势，上排 side / 下排 quarter 或 front）
"""
import bpy, os, math
import numpy as np
from mathutils import Vector, Matrix

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
OUT = r"E:\pro\blender_mcp\docs\milestones\M4\hero_rig_pose.png"

bpy.ops.wm.open_mainfile(filepath=BLEND)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
n0 = len(main.data.vertices)
co0 = np.empty(n0 * 3)
main.data.vertices.foreach_get("co", co0)
co0 = co0.reshape(n0, 3)
print("OPEN verts", n0)

# —— 0) 碎权重清理 + 归一化（资产小修，保存）——
bpy.ops.object.select_all(action='DESELECT')
main.select_set(True)
bpy.context.view_layer.objects.active = main
main.vertex_groups.active_index = 0
try:
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.03, keep_single=True)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("CLEAN+NORMALIZE OK")
except Exception as e:
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass
    print("CLEAN FAILED", e)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(f"SAVED {BLEND} {os.path.getsize(BLEND)}B")

# —— 场景 ——
size = 0.995
bpy.ops.mesh.primitive_plane_add(size=size * 12, location=(0, 0, -0.5005))
ground = bpy.context.object
gm = bpy.data.materials.new("CheckGround"); gm.use_nodes = True
gb = next(x for x in gm.node_tree.nodes if x.type == 'BSDF_PRINCIPLED')
gb.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1)
gb.inputs["Roughness"].default_value = 0.95
ground.data.materials.append(gm)

sd = bpy.data.lights.new("S", type='SUN'); sd.energy = 3.2
sun = bpy.data.objects.new("S", sd); bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (0.95, 0.15, 0.5)
fd = bpy.data.lights.new("F", type='SUN'); fd.energy = 1.1
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

D = size * 2.0
target = (0, 0, 0.0)
def cam_loc(kind):
    if kind == 'side':
        return (0, D, size * 0.10)      # 相机在 +Y（左侧）：前后方向动作最清晰
    if kind == 'front':
        return (D, 0, size * 0.10)      # 相机在 +X（面朝方向）
    return (D * 0.62, D * 0.72, size * 0.42)  # quarter

# —— 姿势工具：绕世界轴 / 对齐到目标方向 ——
def wrot(bone, axis, deg):
    pb = arm.pose.bones[bone]
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    pb.matrix_basis = pb.bone.matrix_local.inverted() @ R @ pb.bone.matrix_local

def walign(bone, target_dir):
    pb = arm.pose.bones[bone]
    rest = (pb.bone.tail_local - pb.bone.head_local).normalized()
    q = rest.rotation_difference(Vector(target_dir).normalized())
    R = q.to_matrix().to_4x4()
    pb.matrix_basis = pb.bone.matrix_local.inverted() @ R @ pb.bone.matrix_local

def clear_pose():
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)

POSES = [
    ("walk",
     [('rot', 'LeftUpLeg', 'Y', -40), ('rot', 'LeftLeg', 'Y', 35),
      ('rot', 'RightUpLeg', 'Y', 18), ('rot', 'RightLeg', 'Y', 8),
      ('align', 'LeftArm', (-0.25, 0.30, -0.92)),
      ('align', 'RightArm', (0.30, -0.30, -0.90)),
      ('rot', 'LeftForeArm', 'Y', -20), ('rot', 'RightForeArm', 'Y', -20)],
     ['side', 'quarter']),
    ("crouch",
     [('rot', 'LeftUpLeg', 'Y', -70), ('rot', 'LeftLeg', 'Y', 100), ('rot', 'LeftFoot', 'Y', -30),
      ('rot', 'RightUpLeg', 'Y', -70), ('rot', 'RightLeg', 'Y', 100), ('rot', 'RightFoot', 'Y', -30),
      ('rot', 'Spine1', 'Y', 20),
      ('align', 'LeftArm', (0.60, 0.35, 0.30)),
      ('align', 'RightArm', (0.60, -0.35, 0.30)),
      ('rot', 'LeftForeArm', 'Z', -30), ('rot', 'RightForeArm', 'Z', 30)],
     ['side', 'quarter']),
    ("aim",
     [('align', 'LeftArm', (0.85, 0.25, 0.10)),
      ('align', 'RightArm', (0.85, -0.25, 0.10)),
      ('rot', 'LeftForeArm', 'Z', -15), ('rot', 'RightForeArm', 'Z', 15),
      ('rot', 'Head', 'Z', 10)],
     ['side', 'quarter']),
    ("twist",
     [('rot', 'Spine2', 'Z', 35), ('rot', 'Neck', 'Z', -15), ('rot', 'Head', 'Z', -25)],
     ['front', 'quarter']),
]

tiles = []
for name, ops, views in POSES:
    clear_pose()
    for op in ops:
        if op[0] == 'rot':
            wrot(op[1], op[2], op[3])
        else:
            walign(op[1], op[2])
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = main.evaluated_get(dg)
    me = ev.to_mesh()
    m = len(me.vertices)
    co = np.empty(m * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(m, 3)
    ev.to_mesh_clear()
    disp = np.linalg.norm(co - co0, axis=1)
    k = int(disp.argmax())
    print(f"POSE {name:6s} disp mean={disp.mean():.3f} max={disp.max():.3f} "
          f"max_at={tuple(round(v, 3) for v in co0[k])}")
    for vk in views:
        p = OUT.replace('.png', f'_{name}_{vk}.png')
        shoot(cam_loc(vk), target, p)
        tiles.append(p)

# —— 拼图 4 列(姿势) × 2 行(视角) ——
imgs = [bpy.data.images.load(p) for p in tiles]
w, h = imgs[0].size
canvas = np.zeros((h * 2, w * 4, 4), dtype=np.float32)
for i, im in enumerate(imgs):
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    col = i // 2
    r0 = h if i % 2 == 0 else 0  # 每姿势第 1 视角放上排
    canvas[r0:r0 + h, col * w:(col + 1) * w] = px
out = bpy.data.images.new("sheet", width=w * 4, height=h * 2, alpha=True)
out.pixels.foreach_set(canvas.ravel())
out.filepath_raw = OUT
out.file_format = 'PNG'
out.save()
print(f"saved {OUT} {os.path.getsize(OUT)}B")
print("POSE_DONE")
