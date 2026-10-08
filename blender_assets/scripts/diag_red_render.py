"""诊断 v2 渲染：重建"朝内异常面"的红色标记对象并渲染（正视/掠射）。

用法: blender.exe --background --factory-startup --python diag_red_render.py
"""
import bpy, bmesh, os
from mathutils import Vector

BLEND = r"E:\pro\blender_mcp\blender_assets\scenes\M3_kit.blend"
OUT = r"E:\pro\blender_mcp\docs\milestones\M3"
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene

engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in engines:
        scene.render.engine = cand
        break

w = bpy.data.worlds.new("DiagWorld2")
scene.world = w
w.use_nodes = True
bg = next((n for n in w.node_tree.nodes if n.type == 'BACKGROUND'), None)
if bg:
    bg.inputs[0].default_value = (0.15, 0.15, 0.16, 1.0)  # 深灰背景突出红色
    bg.inputs[1].default_value = 1.0

# 红色材质
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

# 为每面墙重建红色异常面对象；同时把原墙保留（半灰）以便对照
for name in ("SM_Wall_A", "SM_Wall_B", "SM_Wall_C", "SM_Wall_D"):
    o = bpy.data.objects.get(name)
    if o is None:
        continue
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    bad = [f for f in bm.faces
           if f.material_index == 0
           and f.calc_center_median().y < -0.15
           and f.normal.y > 0.2]
    bm2 = bmesh.new()
    vmap = {}
    for f in bad:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm2.verts.new(v.co)
            vs.append(vmap[v])
        try:
            bm2.faces.new(vs)
        except ValueError:
            pass
    me2 = bpy.data.meshes.new("DIAG_" + name)
    bm2.to_mesh(me2); bm2.free()
    ob2 = bpy.data.objects.new("DIAG_" + name, me2)
    scene.collection.objects.link(ob2)
    me2.materials.append(red)
    bm.free()
    print(f"[RED] {name}: bad={len(bad)}")

# 相机
cam_data = bpy.data.cameras.new("DiagCam2")
cam_data.lens = 35
cam = bpy.data.objects.new("DiagCam2", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.resolution_x = 1000
scene.render.resolution_y = 750
os.makedirs(OUT, exist_ok=True)


def shoot(target_name, tag, cam_pos):
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            ob.hide_render = not (ob.name == target_name or ob.name == "DIAG_" + target_name)
    o = bpy.data.objects[target_name]
    me = o.data
    zs = [v.co.z for v in me.vertices]
    cz = (min(zs) + max(zs)) / 2.0
    d = Vector((cam_pos[0], cam_pos[1] + 3.0, cz)) - Vector(cam_pos)
    cam.location = cam_pos
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    path = os.path.join(OUT, f"diag_red_{target_name[-1]}_{tag}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[RED] shot {path} {os.path.getsize(path)}B")


for nm, cx, ymin in (("SM_Wall_A", -0.95, -0.60), ("SM_Wall_B", -0.09, -0.60),
                     ("SM_Wall_C", 1.09, -0.55), ("SM_Wall_D", 0.16, -0.60)):
    shoot(nm, "front", (cx, ymin - 3.6, 1.5))
    shoot(nm, "graze", (cx + 3.4, ymin - 0.8, 1.5))
print("[RED] done")
