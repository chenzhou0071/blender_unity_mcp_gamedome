"""M6-3 Task 10: 主角佩刀 SM_Knife（匕首）；后续角色道具（火把等）追加于此。
headless 用法: blender.exe --background --factory-startup --python hero_props.py [-- --render]
资产：
  SM_Knife  总长 0.42m = 柄 0.11（圆柱 r0.016）+ 护手 0.02（方块）+ 刃 0.29
            （5 边截面棱柱：背厚 0.014 → 刃厚 0.004 渐薄、尖端斜切）
约定：原点=柄底（便于挂 RightHand 骨骼校准）；刀沿 +Z 建 → 导出 axis_up='Y' → Unity 沿 +Y。
材质：M_Blade (0.65,0.66,0.68) rough 0.3 metal 0.9（刃+护手）；M_Grip (0.16,0.10,0.07) rough 0.8（柄）。
"""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
EXPORT_DIR = os.path.join(ROOT, "export", "hero_props")
SCENES_DIR = os.path.join(ROOT, "scenes")
RENDER_DIR = os.path.join(ROOT, "..", "docs", "milestones", "M6")
DO_RENDER = "--render" in sys.argv

MATERIALS = {
    "M_Blade": dict(color=(0.65, 0.66, 0.68, 1), rough=0.30, metal=0.90),
    "M_Grip":  dict(color=(0.16, 0.10, 0.07, 1), rough=0.80, metal=0.0),
}


# ---------- 场景与通用编辑（与 outdoor_props.py 同惯例） ----------
def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.images):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def apply_transform(o):
    """把对象变换烘焙进顶点数据（位置/旋转/缩放归零）——保证 join 后原点=世界原点。"""
    o.data.transform(o.matrix_basis)
    o.matrix_basis.identity()


def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False


def triangulate(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data); bm.free()


def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def get_material(name):
    spec = MATERIALS[name]
    m = bpy.data.materials.get(name)
    b = None
    if m and m.use_nodes and m.node_tree:
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None:  # 不存在或残留脏材质 → 重建
        if m:
            bpy.data.materials.remove(m, do_unlink=True)
        m = bpy.data.materials.new(name); m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    for s in b.inputs:
        if s.identifier == "Base Color":
            s.default_value = spec["color"]
        elif s.identifier == "Roughness":
            s.default_value = spec["rough"]
        elif s.identifier == "Metallic":
            s.default_value = spec.get("metal", 0.0)
    return m


def set_material(obj, name):
    obj.data.materials.clear()
    obj.data.materials.append(get_material(name))


def export_obj(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(EXPORT_DIR, f"{obj.name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True,
        apply_scale_options='FBX_SCALE_ALL', apply_unit_scale=True,
        axis_forward='-Z', axis_up='Y', object_types={'MESH'})
    return path


# ---------- 资产构建 ----------
def build_knife():
    """匕首：柄（圆柱）→ 护手（方块）→ 刃（5 边截面棱柱，厚度沿刃口方向渐薄、尖端斜切）。
    join 为单一网格（双材质槽 M_Grip/M_Blade），原点=柄底 (0,0,0)。"""
    # 柄：z 0-0.11
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.016, depth=0.11,
                                        location=(0, 0, 0.055))
    grip = bpy.context.object
    grip.name = "SM_Knife"
    apply_transform(grip)
    set_material(grip, "M_Grip")
    # 护手：z 0.11-0.13
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.12))
    guard = bpy.context.object
    guard.name = "KnifeGuard"
    guard.scale = (0.052, 0.020, 0.020)
    apply_transform(guard)
    set_material(guard, "M_Blade")
    # 刃：z 0.13-0.42 截面轮廓（x-z 平面，+x 为刃口侧）
    prof = [(-0.0175, 0.130), (-0.0175, 0.416), (0.0035, 0.420),
            (0.0175, 0.386), (0.0175, 0.130)]           # 背→背上→顶前→斜切至刀尖→刃下

    def thick(x):                                       # 背 0.014 → 刃 0.004
        t = (x + 0.0175) / 0.035
        return 0.007 + (0.002 - 0.007) * t

    verts = [(x, -thick(x), z) for x, z in prof] + [(x, thick(x), z) for x, z in prof]
    faces = []
    for i in range(5):
        j = (i + 1) % 5
        faces.append((i, j, j + 5, i + 5))
    faces.append((4, 3, 2, 1, 0))                       # 下端盖（层 A 逆序）
    faces.append((5, 6, 7, 8, 9))                       # 上端盖（层 B 正序）
    me = bpy.data.meshes.new("KnifeBlade")
    me.from_pydata(verts, [], faces)
    me.validate()
    blade = bpy.data.objects.new("KnifeBlade", me)
    bpy.context.scene.collection.objects.link(blade)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    me.update()
    set_material(blade, "M_Blade")
    # 合并（active=柄 → 对象名 SM_Knife，原点=柄底）
    bpy.ops.object.select_all(action='DESELECT')
    blade.select_set(True); guard.select_set(True); grip.select_set(True)
    bpy.context.view_layer.objects.active = grip
    bpy.ops.object.join()
    knife = bpy.context.object
    flat(knife)
    triangulate(knife)
    return knife


def knife_dims(o):
    vs = o.data.vertices
    mn = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
    mx = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
    return mn, mx - mn


# ---------- 渲染（平放三视角拼图） ----------
def render_knife(knife):
    """刀平放（绕 Y +90°：刀尖 +X、刃口朝下）渲染：侧立面 / 3/4 俯斜 / 刀尖特写 → knife.png。"""
    scene = bpy.context.scene
    knife.rotation_euler = (0, math.radians(90), 0)
    knife.location = (0, 0, 0.06)
    bpy.context.view_layer.update()
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.05, 0.06, 0.08, 1)
    bg.inputs[1].default_value = 1.0
    # 地面（承影，不导出）
    gm = bpy.data.materials.new("G"); gm.use_nodes = True
    gb = next(x for x in gm.node_tree.nodes if x.type == 'BSDF_PRINCIPLED')
    gb.inputs["Base Color"].default_value = (0.10, 0.10, 0.11, 1)
    gb.inputs["Roughness"].default_value = 0.9
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0.21, 0, 0.02))
    bpy.context.object.data.materials.append(gm)
    # 灯光（主 + 补）
    sd = bpy.data.lights.new("S", type='SUN'); sd.energy = 3.0
    sun = bpy.data.objects.new("S", sd)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.95, 0.15, 0.5)
    fd = bpy.data.lights.new("F", type='SUN'); fd.energy = 1.4
    fill = bpy.data.objects.new("F", fd)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (1.15, -0.25, -2.3)
    # 相机
    cd = bpy.data.cameras.new("C"); cd.lens = 50
    cam = bpy.data.objects.new("C", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sc = scene
    sc.render.engine = 'CYCLES'          # 与 hero_anims 同：EEVEE headless 曾有驱动崩溃史，CYCLES CPU 稳
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 32
    sc.render.resolution_x = 640
    sc.render.resolution_y = 640

    shots = [
        ((0.21, -0.85, 0.16), (0.20, 0.0, 0.06), "_tmp_knife_side.png"),
        ((0.02, -0.45, 0.55), (0.20, 0.0, 0.055), "_tmp_knife_persp.png"),
        ((0.60, -0.30, 0.20), (0.34, 0.0, 0.05), "_tmp_knife_tip.png"),
    ]
    os.makedirs(RENDER_DIR, exist_ok=True)
    tiles = []
    for loc, tgt, fn in shots:
        cam.location = loc
        d = Vector(tgt) - Vector(loc)
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(RENDER_DIR, fn)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append(p)
    imgs = [bpy.data.images.load(p) for p in tiles]
    w, h = imgs[0].size
    canvas = np.zeros((h, w * len(tiles), 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        canvas[:, i * w:(i + 1) * w] = px
    out = bpy.data.images.new("knife_sheet", width=w * len(tiles), height=h, alpha=True)
    out.pixels.foreach_set(canvas.ravel())
    outp = os.path.join(RENDER_DIR, "knife.png")
    out.filepath_raw = outp
    out.file_format = 'PNG'
    out.save()
    for im in imgs:
        bpy.data.images.remove(im)
    for p in tiles:
        os.remove(p)
    size = os.path.getsize(outp)
    assert size > 20000, f"渲染图过小: {size}B"
    print(f"RENDER ok knife.png {size}B")


def main():
    clear_scene()
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(SCENES_DIR, exist_ok=True)
    knife = build_knife()
    mn, dims = knife_dims(knife)
    assert -0.002 <= mn.z <= 0.002, f"柄底不在原点: {mn.z:.4f}"
    assert 0.40 <= dims.z <= 0.44, f"总长超预期: {dims.z:.3f}"
    assert 0.045 <= dims.x <= 0.060, f"宽度超预期: {dims.x:.3f}"    # 最宽=护手 0.052
    assert 0.025 <= dims.y <= 0.040, f"厚度超预期: {dims.y:.3f}"    # 最厚=柄直径 0.032
    tris = tris_of(knife)
    assert 50 <= tris <= 1200, f"面数超预算: {tris}"
    path = export_obj(knife)
    fsz = os.path.getsize(path)
    assert fsz > 5000, f"FBX 过小: {fsz}B"
    print(f"  SM_Knife: dims=({dims.x:.3f}, {dims.y:.3f}, {dims.z:.3f}) tris={tris} fbx={fsz}B")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES_DIR, "M6_hero_props.blend"))
    print("OK hero_props")
    if DO_RENDER:
        render_knife(knife)


main()
