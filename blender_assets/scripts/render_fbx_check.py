"""渲染外部 FBX 检查图：4 视角拼图 + 头部特写（自适应相机，自动重链接 .fbm 贴图）。
用法: blender.exe --background --factory-startup --python render_fbx_check.py -- <in.fbx> <out.png>
"""
import bpy, os, sys
import numpy as np
from mathutils import Vector

argv = sys.argv
if "--" in argv:
    FBX = argv[argv.index("--") + 1]
    OUT = argv[argv.index("--") + 2]
else:
    FBX = r"E:\pro\blender_mcp\blender_assets\export\temple\game.fbx"
    OUT = r"E:\pro\blender_mcp\docs\milestones\M4\hero_textured_check.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)

# 贴图重链接保险（若 .fbm 自动加载失败）
fbm_dir = os.path.splitext(FBX)[0] + ".fbm"
if os.path.isdir(fbm_dir):
    for im in bpy.data.images:
        if im.size[0] == 0:
            cand = os.path.join(fbm_dir, os.path.basename(im.filepath))
            if os.path.isfile(cand):
                im.filepath = cand
                im.reload()

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
