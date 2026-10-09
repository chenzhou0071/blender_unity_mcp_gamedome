"""主角减面对比测试：原版(66.5万面) vs Decimate(ratio=0.30) 并排渲染。
用法: blender.exe --background --factory-startup --python hero_decimate_test.py
"""
import bpy, os, sys
import numpy as np
from mathutils import Vector

GLB = r"E:\pro\blender_mcp\blender_assets\import\hero_highpoly.glb"
OUT = r"E:\pro\blender_mcp\docs\milestones\M4\hero_decimate_compare.png"
RATIO = 0.30

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

src = next(o for o in bpy.data.objects if o.type == 'MESH')
orig_tris = sum(len(p.vertices) - 2 for p in src.data.polygons)

def world_bbox(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

mn, mx = world_bbox([src])
dims = mx - mn
# 并排错开轴 = 最薄轴（身体厚度方向）；对称轴 = 水平两轴中较大者（手展方向）
thin_axis = min(range(3), key=lambda i: dims[i])
sym_axis = 0 if dims[0] >= dims[1] else 1
print(f"ORIG tris={orig_tris} dims={tuple(round(d, 3) for d in dims)} thin_axis={'XYZ'[thin_axis]} sym_axis={'XYZ'[sym_axis]}")

# 复制减面版并错开摆放
dec = src.copy(); dec.data = src.data.copy(); dec.name = "hero_decimated"
bpy.context.scene.collection.objects.link(dec)
offset = Vector((0, 0, 0)); offset[thin_axis] = dims[thin_axis] + 0.45
dec.location += offset

# Decimate（对称、保留 UV）
bpy.ops.object.select_all(action='DESELECT')
dec.select_set(True)
bpy.context.view_layer.objects.active = dec
mod = dec.modifiers.new("dec", 'DECIMATE')
mod.ratio = RATIO
mod.use_collapse_triangulate = True
mod.use_symmetry = True
mod.symmetry_axis = 'XYZ'[sym_axis]
bpy.ops.object.modifier_apply(modifier=mod.name)
dec_tris = sum(len(p.vertices) - 2 for p in dec.data.polygons)
print(f"DEC tris={dec_tris}")

# 场景 bbox（两个模型）
mn2, mx2 = world_bbox([src, dec])
c = (mn2 + mx2) / 2
size = max(mx2 - mn2)

# 地面
bpy.ops.mesh.primitive_plane_add(size=size * 10, location=(c.x, c.y, mn2.z - 0.001))
ground = bpy.context.object
gm = bpy.data.materials.new("CheckGround"); gm.use_nodes = True
gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
gb.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1)
gb.inputs["Roughness"].default_value = 0.95
ground.data.materials.append(gm)

# 灯光
sd = bpy.data.lights.new("S", type='SUN'); sd.energy = 3.2
sun = bpy.data.objects.new("S", sd); bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (0.95, 0.15, 0.5)
fd = bpy.data.lights.new("F", type='SUN'); fd.energy = 1.1
fill = bpy.data.objects.new("F", fd); bpy.context.scene.collection.objects.link(fill)
fill.rotation_euler = (1.15, -0.25, -2.3)

# 相机
cd = bpy.data.cameras.new("C"); cd.lens = 50
cam = bpy.data.objects.new("C", cd); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in engines:
        bpy.context.scene.render.engine = cand
        break
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 640

def shoot(loc, target, lens, path):
    cam.location = loc
    cam.data.lens = lens
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
D = size * 1.75
views = [("front", (c.x, c.y + D, c.z)),
         ("side", (c.x + D, c.y, c.z)),
         ("back", (c.x, c.y - D, c.z)),
         ("quarter", (c.x + D * 0.7, c.y + D * 0.7, c.z + size * 0.35))]
paths = []
for name, loc in views:
    p = OUT.replace('.png', f'_{name}.png')
    shoot(loc, c, 50, p)
    paths.append(p)

# 特写：减面版头部（验证细节保留）
dmn, dmx = world_bbox([dec])
dc = (dmn + dmx) / 2
head = Vector((dc.x, dc.y, dc.z + (dmx.z - dmn.z) * 0.22))
cl = (dc.x + D * 0.30, dc.y + D * 0.50, dc.z + size * 0.40)
cp = OUT.replace('.png', '_closeup.png')
shoot(cl, head, 85, cp)

# 拼图
tiles = [bpy.data.images.load(p) for p in paths]
w, h = tiles[0].size
canvas = np.zeros((h * 2, w * 2, 4), dtype=np.float32)
for i, im in enumerate(tiles):
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    r0 = h if i < 2 else 0
    c0 = 0 if i % 2 == 0 else w
    canvas[r0:r0 + h, c0:c0 + w] = px
out = bpy.data.images.new("sheet", width=w * 2, height=h * 2, alpha=True)
out.pixels.foreach_set(canvas.ravel())
out.filepath_raw = OUT
out.file_format = 'PNG'
out.save()
print(f"saved {OUT} {os.path.getsize(OUT)}B")
print(f"saved {cp} {os.path.getsize(cp)}B")
