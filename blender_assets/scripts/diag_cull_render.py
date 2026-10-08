"""诊断：模拟 Unity 单面剔除渲染 4 面墙正视图（背面剔除 ON，淡蓝背景）。
用途：若图上出现"透背景色的带子"，即在 Blender 内复现 Unity 透光白带，
     之后修复迭代可直接在 Blender 内完成，最后才过 Unity 验证。
用法: blender.exe --background --factory-startup --python diag_cull_render.py
"""
import bpy, os
from mathutils import Vector

BLEND = r"E:\pro\blender_mcp\blender_assets\scenes\M3_kit.blend"
OUT = r"E:\pro\blender_mcp\docs\milestones\M3"
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene

# 引擎
engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in engines:
        scene.render.engine = cand
        break

# 背面剔除 ON（EEVEE 材质属性）——模拟 Unity 单面剔除
for m in bpy.data.materials:
    m.use_backface_culling = True

# 淡蓝亮背景，便于识别透光
w = bpy.data.worlds.new("DiagWorld")
scene.world = w
w.use_nodes = True
bg = next((n for n in w.node_tree.nodes if n.type == 'BACKGROUND'), None)
if bg:
    bg.inputs[0].default_value = (0.82, 0.90, 1.0, 1.0)
    bg.inputs[1].default_value = 1.0

# 相机
cam_data = bpy.data.cameras.new("DiagCam")
cam_data.lens = 35
cam = bpy.data.objects.new("DiagCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# 太阳光
sd = bpy.data.lights.new("DiagSun", type='SUN')
sd.energy = 3.5
sun = bpy.data.objects.new("DiagSun", sd)
scene.collection.objects.link(sun)
sun.rotation_euler = (0.9, 0.2, 0.7)

scene.render.resolution_x = 1000
scene.render.resolution_y = 750
os.makedirs(OUT, exist_ok=True)

for name in ("SM_Wall_A", "SM_Wall_B", "SM_Wall_C", "SM_Wall_D"):
    o = bpy.data.objects.get(name)
    if o is None:
        print(f"[CULL] {name}: NOT FOUND")
        continue
    # 单独显示该墙
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            ob.hide_render = (ob.name != name)
    me = o.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    cx = (min(xs) + max(xs)) / 2.0
    cz = (min(zs) + max(zs)) / 2.0
    ymin = min(ys)
    cam.location = (cx, ymin - 3.6, cz)
    d = Vector((cx, ymin, cz)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    path = os.path.join(OUT, f"diag_cull_{name[-1]}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    size = os.path.getsize(path)
    print(f"[CULL] {name} -> {path} {size}B")
print("[CULL] done")
