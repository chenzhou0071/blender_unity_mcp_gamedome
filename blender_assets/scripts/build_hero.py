"""M4-1: 主角低模人形网格（风格化方块探险者）。
headless 用法: blender.exe --background --factory-startup --python build_hero.py
部件表（记法：坐标=(x 左右, z 高, y 前后)，尺寸=(宽x, 高z, 厚y)，单位米）：
  头   box (0, 1.62, 0)    0.22x0.24x0.24 倒角.03          M_Skin
  躯干 box (0, 1.24, 0)    0.42x0.55x0.24 倒角.04 顶面x1.08 M_Shirt
  上臂 cyl (+-0.27, 1.27, 0)   r.06 L.32 垂放15度外摆        M_Shirt
  前臂 cyl (+-0.30, 0.97, 0.02) r.055 L.28                  M_Skin
  大腿 cyl (+-0.11, 0.72, 0)   r.09 L.45                    M_Pants
  小腿 cyl (+-0.11, 0.29, 0)   r.075 L.42                   M_Pants
  脚   box (+-0.11, 0.05, 0.04) 0.16x0.10x0.26              M_Boots
产出：scenes/M4_hero.blend + docs/milestones/M4/hero_model.png（4 视角拼图）
"""
import bpy, bmesh, math, os
from mathutils import Vector, Euler, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
SCENES_DIR = os.path.join(ROOT, "scenes")
M4_DIR = os.path.join(ROOT, "..", "docs", "milestones", "M4")
M4_BLEND = os.path.join(SCENES_DIR, "M4_hero.blend")

# 材质槽顺序固定（M4 Interfaces 约定，索引 0-3 即 S kin/Shirt/Pants/Boots）
MAT_ORDER = ["M_Skin", "M_Shirt", "M_Pants", "M_Boots"]
HERO_MATS = {
    "M_Skin":  dict(color=(0.66, 0.48, 0.36, 1), rough=0.78),  # 晒棕肤色
    "M_Shirt": dict(color=(0.58, 0.52, 0.38, 1), rough=0.92),  # 卡其亚麻衬衫
    "M_Pants": dict(color=(0.33, 0.28, 0.22, 1), rough=0.92),  # 深棕长裤
    "M_Boots": dict(color=(0.20, 0.15, 0.11, 1), rough=0.70),  # 深棕皮革靴
}


# ---------- 场景与落地（模式同 temple_kit.py） ----------
def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.images):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def _fin(bm, name):
    """bmesh 落地为对象（几何进顶点，对象 transform 归零，平直着色）。"""
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = False
    return obj


def get_material(name):
    spec = HERO_MATS[name]
    m = bpy.data.materials.get(name)
    if m and not m.use_nodes:
        bpy.data.materials.remove(m, do_unlink=True)
        m = None
    if m is None:
        m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = spec["color"]
    b.inputs["Roughness"].default_value = spec["rough"]
    return m


# ---------- 部件构建 ----------
def make_box(name, size, bevel=0.0, taper_top_x=1.0):
    """size=(宽x, 厚y, 高z) 的箱体；taper_top_x: 顶面 x 缩放（上宽下窄）。"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
    if taper_top_x != 1.0:
        zmax = max(v.co.z for v in bm.verts)
        for v in bm.verts:
            if abs(v.co.z - zmax) < 1e-6:
                v.co.x *= taper_top_x
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=bevel,
                        segments=1, profile=0.5, affect='EDGES')
    return _fin(bm, name)


def make_cyl(name, r, depth, verts=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth)
    o = bpy.context.object
    o.name = name
    o.data.transform(o.matrix_basis)   # 变换烘焙进顶点
    o.matrix_basis.identity()
    return o


def place(o, center, rot_y_deg=0.0):
    """center 表记法 (cx, cz高, cy前后) → 平移进 Blender 世界；rot_y_deg 绕前后轴外摆。"""
    cx, cz, cy = center
    if rot_y_deg:
        o.data.transform(Euler((0.0, math.radians(rot_y_deg), 0.0)).to_matrix().to_4x4())
    o.data.transform(Matrix.Translation((cx, cy, cz)))
    return o


def join_parts(parts, name):
    """合并部件（每部件已带材质名），按 MAT_ORDER 统一材质槽与 material_index。"""
    bm = bmesh.new()
    for o, mat in parts:
        before = len(bm.faces)
        bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        idx = MAT_ORDER.index(mat)
        for f in bm.faces[before:]:
            f.material_index = idx
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = False
    for mn in MAT_ORDER:
        me.materials.append(get_material(mn))
    for o, _ in parts:
        bpy.data.objects.remove(o, do_unlink=True)
    return obj


def subdiv(o, cuts=1):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free()


def tris_of(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


# ---------- 本体 ----------
def build_body():
    parts = []
    o = make_box("h_head", (0.22, 0.24, 0.24), bevel=0.03)
    place(o, (0.0, 1.62, 0.0))
    parts.append((o, "M_Skin"))
    o = make_box("h_torso", (0.42, 0.24, 0.55), bevel=0.04, taper_top_x=1.08)
    place(o, (0.0, 1.24, 0.0))
    parts.append((o, "M_Shirt"))
    for s, tag in ((1, "R"), (-1, "L")):
        o = make_cyl(f"h_uparm_{tag}", 0.06, 0.32)
        place(o, (s * 0.27, 1.27, 0.0), rot_y_deg=-15 * s)   # 垂放 15° 外摆
        parts.append((o, "M_Shirt"))
        o = make_cyl(f"h_loarm_{tag}", 0.055, 0.28)
        place(o, (s * 0.30, 0.97, 0.02))
        parts.append((o, "M_Skin"))
        o = make_cyl(f"h_thigh_{tag}", 0.09, 0.45)
        place(o, (s * 0.11, 0.72, 0.0))
        parts.append((o, "M_Pants"))
        o = make_cyl(f"h_shin_{tag}", 0.075, 0.42)
        place(o, (s * 0.11, 0.29, 0.0))
        parts.append((o, "M_Pants"))
        o = make_box(f"h_foot_{tag}", (0.16, 0.26, 0.10))
        place(o, (s * 0.11, 0.05, 0.04))
        parts.append((o, "M_Boots"))
    o = join_parts(parts, "SK_Explorer")
    # 焊接邻近部件接缝（便于后续自动权重）
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)
    bm.to_mesh(o.data); bm.free()
    return o


# ---------- 渲染（4 视角拼图） ----------
def render_variants(path):
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.001))   # 承影地面
    ground = bpy.context.object
    gm = bpy.data.materials.new("HeroGround"); gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    gb.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1)
    gb.inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(gm)
    cam_data = bpy.data.cameras.new("HeroCam"); cam_data.lens = 50
    cam = bpy.data.objects.new("HeroCam", cam_data)
    scene.collection.objects.link(cam); scene.camera = cam
    sun_data = bpy.data.lights.new("HeroSun", type='SUN'); sun_data.energy = 3.2
    sun = bpy.data.objects.new("HeroSun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.95, 0.15, 0.5)
    fill_data = bpy.data.lights.new("HeroFill", type='SUN'); fill_data.energy = 1.1
    fill = bpy.data.objects.new("HeroFill", fill_data)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (1.15, -0.25, -2.3)
    engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        if cand in engines:
            scene.render.engine = cand
            break
    scene.render.resolution_x = 480
    scene.render.resolution_y = 640
    os.makedirs(M4_DIR, exist_ok=True)
    views = [
        ("front",   (0.0, -4.0, 1.05)),
        ("side",    (4.0, 0.0, 1.05)),
        ("back",    (0.0, 4.0, 1.05)),
        ("quarter", (2.9, -2.9, 1.9)),
    ]
    target = Vector((0.0, 0.0, 0.88))
    paths = []
    for name, loc in views:
        cam.location = loc
        d = target - Vector(loc)
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(M4_DIR, f"hero_model_{name}.png")
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    # 2×2 拼图（image.pixels 行序自下而上：前排视图占拼图上排）
    import numpy as np
    tiles = [bpy.data.images.load(p) for p in paths]
    w, h = tiles[0].size
    canvas = np.zeros((h * 2, w * 2, 4), dtype=np.float32)
    for i, im in enumerate(tiles):
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        r0 = h if i < 2 else 0
        c0 = 0 if i % 2 == 0 else w
        canvas[r0:r0 + h, c0:c0 + w] = px
    out = bpy.data.images.new("hero_sheet", width=w * 2, height=h * 2, alpha=True)
    out.pixels.foreach_set(canvas.ravel())
    out.filepath_raw = path
    out.file_format = 'PNG'
    out.save()
    size = os.path.getsize(path) if os.path.exists(path) else 0
    assert size > 30000, f"拼图过小: {size}B"
    print(f"RENDER ok {size}B engine={scene.render.engine}")


def main():
    clear_scene()
    os.makedirs(SCENES_DIR, exist_ok=True)
    os.makedirs(M4_DIR, exist_ok=True)
    o = build_body()
    while tris_of(o) < 1000:                 # 细分至 1000-6000 tris 区间
        subdiv(o, cuts=1)
        for p in o.data.polygons:
            p.use_smooth = False
    tris = tris_of(o)
    assert 1000 <= tris <= 6000, f"面数超范围: {tris}"
    assert 1.6 <= o.dimensions.z <= 1.9, f"身高异常: {o.dimensions.z}"
    counts = {}
    for p in o.data.polygons:
        counts[p.material_index] = counts.get(p.material_index, 0) + 1
    print("  mats:", {o.data.materials[i].name: c for i, c in sorted(counts.items())})
    bpy.ops.wm.save_as_mainfile(filepath=M4_BLEND)
    render_variants(os.path.join(M4_DIR, "hero_model.png"))
    print(f"OK hero tris={tris} h={o.dimensions.z:.2f}")


main()
