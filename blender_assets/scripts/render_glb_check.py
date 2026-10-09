"""导入检查 + 渲染外部 GLB（4 视角拼图 + 特写，支持 meshopt 压缩）。
用法: blender.exe --background --factory-startup --python render_glb_check.py -- <in.glb> <out.png>
"""
import bpy, os, sys
import numpy as np
from mathutils import Vector

argv = sys.argv
if "--" in argv:
    GLB = argv[argv.index("--") + 1]
    OUT = argv[argv.index("--") + 2]
else:
    GLB = r"E:\pro\blender_mcp\blender_assets\import\tripo_f872130d_meshopt.glb"
    OUT = r"E:\pro\blender_mcp\docs\milestones\M4\tripo_highpoly_check.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

print("=== OBJECTS ===")
tris_total = 0
for o in bpy.data.objects:
    if o.type == 'MESH':
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        tris_total += t
        mats = [ms.material.name if ms.material else None for ms in o.material_slots]
        print(f"  {o.name}  tris={t}  mats={mats}")
print(f"TOTAL tris={tris_total}")

print("=== MATERIALS ===")
for m in bpy.data.materials:
    desc = f"  {m.name}"
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                desc += f" tex={n.image.name}({n.image.size[0]}x{n.image.size[1]})"
            if n.type == 'BSDF_PRINCIPLED':
                desc += f" base_color_linked={n.inputs['Base Color'].is_linked}"
    print(desc)

print(f"=== IMAGES ({len(bpy.data.images)}) ===")
for im in bpy.data.images:
    print(f"  {im.name} {im.size[0]}x{im.size[1]} packed={im.packed_file is not None}")

scene = bpy.context.scene
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
pts = []
for o in meshes:
    for c in o.bound_box:
        pts.append(o.matrix_world @ Vector(c))
minx = min(p.x for p in pts); maxx = max(p.x for p in pts)
miny = min(p.y for p in pts); maxy = max(p.y for p in pts)
minz = min(p.z for p in pts); maxz = max(p.z for p in pts)
cx, cy, cz = (minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2
size = max(maxx - minx, maxy - miny, maxz - minz)
print(f"BBOX x[{minx:.2f},{maxx:.2f}] y[{miny:.2f},{maxy:.2f}] z[{minz:.2f},{maxz:.2f}] size={size:.2f}")

# 地面
bpy.ops.mesh.primitive_plane_add(size=size * 10, location=(cx, cy, minz - 0.001))
ground = bpy.context.object
gm = bpy.data.materials.new("CheckGround"); gm.use_nodes = True
gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
gb.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1)
gb.inputs["Roughness"].default_value = 0.95
ground.data.materials.append(gm)

# 灯光
sd = bpy.data.lights.new("S", type='SUN'); sd.energy = 3.2
sun = bpy.data.objects.new("S", sd); scene.collection.objects.link(sun)
sun.rotation_euler = (0.95, 0.15, 0.5)
fd = bpy.data.lights.new("F", type='SUN'); fd.energy = 1.1
fill = bpy.data.objects.new("F", fd); scene.collection.objects.link(fill)
fill.rotation_euler = (1.15, -0.25, -2.3)

# 相机
cd = bpy.data.cameras.new("C"); cd.lens = 50
cam = bpy.data.objects.new("C", cd); scene.collection.objects.link(cam)
scene.camera = cam

engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in engines:
        scene.render.engine = cand
        break
scene.render.resolution_x = 480
scene.render.resolution_y = 640

def shoot(loc, target, lens, path):
    cam.location = loc
    cam.data.lens = lens
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
D = size * 1.9
target = Vector((cx, cy, cz))
views = [("front", (cx, cy + D, cz)),
         ("side", (cx + D, cy, cz)),
         ("back", (cx, cy - D, cz)),
         ("quarter", (cx + D * 0.7, cy + D * 0.7, cz + size * 0.45))]
paths = []
for name, loc in views:
    p = OUT.replace('.png', f'_{name}.png')
    shoot(loc, target, 50, p)
    paths.append(p)

# 头部特写（前 3/4）
head = Vector((cx, cy, cz + size * 0.30))
cl = (cx + D * 0.35, cy + D * 0.55, cz + size * 0.45)
cp = OUT.replace('.png', '_closeup.png')
shoot(cl, head, 85, cp)

# 4 视角拼图
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
