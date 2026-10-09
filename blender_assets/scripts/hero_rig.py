"""主角绑定：减面(0.30) → Mixamo 标准 Humanoid 骨架 → 自动权重 → 保存 blend。
用法: blender.exe --background --factory-startup --python hero_rig.py
朝向: 面朝 +X，左=+Y，上=+Z（关节常数来自 hero_rig_probe 顶点分布统计）
"""
import bpy, os
from mathutils import Vector

GLB = r"E:\pro\blender_mcp\blender_assets\import\hero_highpoly.glb"
SAVE = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print("MESHES", [(o.name, len(o.data.vertices)) for o in meshes])

# —— 解除导入层级（Tripo 常带空父级），保持世界变换 ——
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if any(o.parent for o in meshes):
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
for o in [o for o in bpy.data.objects if o.type not in ('MESH', 'ARMATURE')]:
    bpy.data.objects.remove(o, do_unlink=True)

# —— 应用对象变换（世界=局部，骨骼坐标统一）——
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# —— 减面到最终几何（ratio 0.30，沿臂展轴对称）——
def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

mn0, mx0 = bbox(meshes)
d0 = mx0 - mn0
sym_axis = 'X' if d0.x >= d0.y else 'Y'
for o in meshes:
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    mod = o.modifiers.new("dec", 'DECIMATE')
    mod.ratio = 0.30
    mod.use_collapse_triangulate = True
    mod.use_symmetry = True
    mod.symmetry_axis = sym_axis
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"DEC {o.name} verts={len(o.data.vertices)}")

# —— 骨架：Mixamo 标准命名 ——
Z_HIPS, Z_SPINE, Z_SPINE1, Z_SPINE2 = 0.010, 0.055, 0.130, 0.230
Z_NECK, Z_HEAD, Z_TOP = 0.336, 0.376, 0.500
Y_SHO_IN, Y_SHO, Y_ELBOW, Y_WRIST, Y_HAND = 0.045, 0.155, 0.260, 0.360, 0.410
Z_SHO, Z_ELBOW, Z_WRIST = 0.310, 0.318, 0.328
Y_LEG = 0.105
Z_KNEE, Z_ANKLE, Z_SOLE = -0.220, -0.450, -0.500

arm_data = bpy.data.armatures.new("HeroArmature")
arm_obj = bpy.data.objects.new("HeroRig", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
bpy.ops.object.select_all(action='DESELECT')
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

def add(name, head, tail, parent=None, connect=False):
    b = eb.new(name)
    b.head, b.tail = head, tail
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    return b

add("Hips", (0, 0, Z_HIPS), (0, 0, Z_SPINE))
add("Spine", (0, 0, Z_SPINE), (0, 0, Z_SPINE1), "Hips", True)
add("Spine1", (0, 0, Z_SPINE1), (0, 0, Z_SPINE2), "Spine", True)
add("Spine2", (0, 0, Z_SPINE2), (0, 0, Z_NECK), "Spine1", True)
add("Neck", (0, 0, Z_NECK), (0, 0, Z_HEAD), "Spine2", True)
add("Head", (0, 0, Z_HEAD), (0, 0, Z_TOP), "Neck", True)
for s, sgn in (("Left", 1), ("Right", -1)):
    add(f"{s}Shoulder", (0, sgn * Y_SHO_IN, Z_SHO), (0, sgn * Y_SHO, Z_SHO), "Spine2")
    add(f"{s}Arm", (0, sgn * Y_SHO, Z_SHO), (0, sgn * Y_ELBOW, Z_ELBOW), f"{s}Shoulder", True)
    add(f"{s}ForeArm", (0, sgn * Y_ELBOW, Z_ELBOW), (0, sgn * Y_WRIST, Z_WRIST), f"{s}Arm", True)
    add(f"{s}Hand", (0, sgn * Y_WRIST, Z_WRIST), (0, sgn * Y_HAND, Z_WRIST + 0.004), f"{s}ForeArm", True)
    add(f"{s}UpLeg", (0, sgn * Y_LEG, Z_HIPS), (0, sgn * Y_LEG, Z_KNEE), "Hips")
    add(f"{s}Leg", (0, sgn * Y_LEG, Z_KNEE), (0, sgn * Y_LEG, Z_ANKLE), f"{s}UpLeg", True)
    add(f"{s}Foot", (0, sgn * Y_LEG, Z_ANKLE), (0.085, sgn * Y_LEG, Z_SOLE), f"{s}Leg", True)
    add(f"{s}ToeBase", (0.085, sgn * Y_LEG, Z_SOLE), (0.135, sgn * Y_LEG, Z_SOLE), f"{s}Foot", True)
bpy.ops.object.mode_set(mode='OBJECT')
print(f"BONES n={len(arm_data.bones)}")

# 打印骨局部轴（X/Z 轴，Y=骨方向），供姿势脚本判断旋转轴
for b in arm_data.bones:
    m = b.matrix_local.to_3x3()
    xa = tuple(round(v, 2) for v in m.col[0])
    za = tuple(round(v, 2) for v in m.col[2])
    yd = tuple(round(v, 2) for v in (b.tail_local - b.head_local).normalized())
    print(f"AX {b.name:14s} Ydir={yd} Xax={xa} Zax={za}")

# —— 自动权重绑定 ——
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
print("PARENT_OK")

# —— 权重统计（确认无空骨）——
for o in meshes:
    vg = {g.index: g.name for g in o.vertex_groups}
    counts = {n: 0 for n in vg.values()}
    for v in o.data.vertices:
        for g in v.groups:
            if g.weight > 0.05:
                counts[vg[g.group]] += 1
    print("WG", o.name, {k: v for k, v in sorted(counts.items())})

os.makedirs(os.path.dirname(SAVE), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=SAVE)
print(f"SAVED {SAVE} {os.path.getsize(SAVE)}B")
print("RIG_DONE")
