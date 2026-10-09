"""肩部骨骼位置核查: 打印肩带骨坐标 vs 网格肩部结构(臂轴/腋窝/肩顶/外缘), 渲染骨骼标记球。
目的: 核实"肩关节转轴是否超出肩膀、超出多少"。
标记: 红=Arm.head(肩转轴) 绿=Shoulder.head(胸端) 蓝=Arm.tail(肘); 网格半透明显示。
只读不保存。用法: blender.exe --background --factory-startup --python hero_shoulder_bone_probe.py
输出: docs/milestones/M4/hero_bone_probe_f.png/_q.png/_s.png
"""
import bpy, os
import numpy as np
from mathutils import Vector

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
OUT = r"E:\pro\blender_mcp\docs\milestones\M4\hero_bone_probe.png"

bpy.ops.wm.open_mainfile(filepath=BLEND)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

# —— 1) 骨骼坐标 ——
BONES = ("Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
         "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
         "RightShoulder", "RightArm", "RightForeArm", "RightHand")
for nm in BONES:
    b = arm.data.bones.get(nm)
    if b:
        h, t = b.head_local, b.tail_local
        print(f"BONE {nm:14s} head=({h.x:+.3f},{h.y:+.3f},{h.z:+.3f}) "
              f"tail=({t.x:+.3f},{t.y:+.3f},{t.z:+.3f}) len={b.length:.3f}")

# —— 2) 网格肩部解剖结构（修正口径: z>0.22 防腿混入, y<0.34 防手混入）——
n = len(main.data.vertices)
co = np.empty(n * 3)
main.data.vertices.foreach_get("co", co)
co = co.reshape(n, 3)
# 沿手臂的截面剖面（每 2cm 一片）
for y0 in np.arange(0.06, 0.34, 0.02):
    m = ((co[:, 1] >= y0) & (co[:, 1] < y0 + 0.02) & (np.abs(co[:, 0]) < 0.12)
         & (co[:, 2] > 0.22) & (co[:, 2] < 0.46))
    if m.sum() > 10:
        print(f"SLICE y[{y0:.2f},{y0+0.02:.2f}) n={m.sum():5d} "
              f"z={co[m,2].min():.3f}~{co[m,2].max():.3f} h={co[m,2].max()-co[m,2].min():.3f}")
# 三角肌区域质心（z>0.29 的肩头部分）
mD = ((co[:, 2] > 0.29) & (co[:, 1] > 0.0) & (co[:, 1] < 0.28) & (np.abs(co[:, 0]) < 0.12))
print(f"DELTOID n={mD.sum()} centroid=({co[mD,0].mean():.3f},{co[mD,1].mean():.3f},{co[mD,2].mean():.3f}) "
      f"y_range={co[mD,1].min():.3f}~{co[mD,1].max():.3f} z_top={co[mD,2].max():.3f}")
# 腋窝：y[.10,.20] 内的最低皮肤点（z<0.32 限定在腋下区）
mA = ((co[:, 1] > 0.10) & (co[:, 1] < 0.20) & (np.abs(co[:, 0]) < 0.12) & (co[:, 2] > 0.22) & (co[:, 2] < 0.32))
ia = np.where(mA)[0][np.argmin(co[mA, 2])]
print(f"ARMPIT    n={mA.sum()} min_z={co[ia,2]:.3f} at ({co[ia,0]:.3f},{co[ia,1]:.3f},{co[ia,2]:.3f})")

# —— 3) 标记球 + 骨骼线（自发光）——
def emit_mat(name, color, strength=1.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        if nd.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(nd)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1.0)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs['Emission'], nt.nodes['Material Output'].inputs['Surface'])
    return m

def make_ball(loc, color, name):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.013, location=loc, segments=16, ring_count=12)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(emit_mat(name + "M", color))
    return o

def make_stick(head, tail, radius, color, name):
    h, t = Vector(head), Vector(tail)
    d = t - h
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=d.length, location=(h + t) / 2,
                                        vertices=12)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(emit_mat(name + "M", color, 0.8))
    return o

# 球: 红=Arm.head(肩转轴) 绿=Shoulder.head(胸端) 蓝=Arm.tail(肘)
for s in ("Left", "Right"):
    bA = arm.data.bones[f"{s}Arm"]
    bS = arm.data.bones[f"{s}Shoulder"]
    make_ball(bA.head_local, (1.0, 0.05, 0.05), f"ball_{s}_armhead")
    make_ball(bS.head_local, (0.05, 1.0, 0.05), f"ball_{s}_shead")
    make_ball(bA.tail_local, (0.1, 0.3, 1.0), f"ball_{s}_elbow")
# 骨骼线: 黄=Shoulder 橙=Arm 青=ForeArm 紫=Hand 白=脊柱链
STICK = {"Left": (("Shoulder", (1.0, 0.85, 0.1)), ("Arm", (1.0, 0.45, 0.05)),
                  ("ForeArm", (0.1, 0.8, 1.0)), ("Hand", (0.8, 0.3, 1.0))),
         "Right": (("Shoulder", (1.0, 0.85, 0.1)), ("Arm", (1.0, 0.45, 0.05)),
                   ("ForeArm", (0.1, 0.8, 1.0)), ("Hand", (0.8, 0.3, 1.0)))}
for s, items in STICK.items():
    for nm, col in items:
        b = arm.data.bones[f"{s}{nm}"]
        make_stick(b.head_local, b.tail_local, 0.006, col, f"stick_{s}{nm}")
for nm in ("Hips", "Spine", "Spine1", "Spine2", "Neck"):
    b = arm.data.bones[nm]
    make_stick(b.head_local, b.tail_local, 0.005, (0.95, 0.95, 0.95), f"stick_{nm}")
print("BALLS+STICKS placed")

# —— 4) 网格半透明 ——
for m in main.data.materials:
    if m.use_nodes:
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                try:
                    nd.inputs['Alpha'].default_value = 0.35
                except Exception:
                    pass
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    try:
        m.blend_method = 'BLEND'
    except Exception:
        pass
print("TRANSPARENT set")

# —— 5) 场景 + 渲染 ——
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
cd = bpy.data.cameras.new("C"); cd.lens = 55
cam = bpy.data.objects.new("C", cd); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in engines:
        bpy.context.scene.render.engine = cand
        break
sc = bpy.context.scene
sc.render.resolution_x = 1024
sc.render.resolution_y = 1024

def shoot(loc, target, path):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

shoot((1.00, 0.0, 0.40), (0.0, 0.05, 0.33), OUT.replace('.png', '_f.png'))
shoot((0.62, 0.55, 0.60), (0.01, 0.16, 0.32), OUT.replace('.png', '_q.png'))
shoot((0.10, 1.05, 0.40), (0.01, 0.16, 0.32), OUT.replace('.png', '_s.png'))
print("BONE_PROBE_DONE")
