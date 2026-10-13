"""M6-2 Task 9: 户外道具——巨石岗石件（SM_GorgeRock_A/B/C/D）；后续户外道具（藤帘/木筏等）追加于此。
headless 用法: blender.exe --background --factory-startup --python outdoor_props.py [-- --render]
资产：
  SM_GorgeRock_A  3.5m 不规则巨石（基座垫石/补隙）
  SM_GorgeRock_B  5m 扁石（顶盖压顶/横石）
  SM_GorgeRock_C  9m 级超大扁圆巨石（2026-10-13 巨石岗重做：基座巨岩/顶盖）
  SM_GorgeRock_D  7m 级高楔形石（斜靠层：成对相向斜倚，垒出低矮 V 形夹缝）
约定：几何中心=对象原点（Unity 按中心摆位，缩放与碰撞一致）；导出 axis_up='Y' → Unity (x, 高度, z)。
"""
import bpy, bmesh, random, os, sys, math
from mathutils import Vector, Matrix

random.seed(23)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
EXPORT_DIR = os.path.join(ROOT, "export", "outdoor")
SCENES_DIR = os.path.join(ROOT, "scenes")
RENDER_DIR = os.path.join(ROOT, "..", "docs", "milestones", "M6")
DO_RENDER = "--render" in sys.argv

MATERIALS = {
    "M_Cliff":         dict(color=(0.35, 0.30, 0.24, 1), rough=0.90),   # 岩缝巨石（峡谷岩壁同族）
    "M_Ground_Render": dict(color=(0.22, 0.19, 0.15, 1), rough=0.95),   # 仅渲染地面衬托（不导出）
}
# 面数预算（计划上限）：A ≤1600 / B ≤2200 / C ≤3200 / D ≤2400
TRIS_BUDGET = {"SM_GorgeRock_A": 1600, "SM_GorgeRock_B": 2200,
               "SM_GorgeRock_C": 3200, "SM_GorgeRock_D": 2400}


# ---------- 场景与落地 ----------
def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.images):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def apply_transform(o):
    """把对象变换烘焙进顶点数据（位置/旋转/缩放归零）。"""
    o.data.transform(o.matrix_basis)
    o.matrix_basis.identity()


def add_ico(name, r, loc, subdiv=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    apply_transform(o)
    return o


# ---------- 通用编辑 ----------
def jitter(obj, amp, zmin=None, amp_z=None):
    """顶点随机抖动（风化/破损感）。zmin: 仅处理 z>=zmin 的顶点。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    az = amp if amp_z is None else amp_z
    for v in bm.verts:
        if zmin is not None and v.co.z < zmin:
            continue
        v.co.x += random.uniform(-amp, amp)
        v.co.y += random.uniform(-amp, amp)
        v.co.z += random.uniform(-az, az)
    bm.to_mesh(obj.data); bm.free()


def subdiv(obj, cuts=1):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.to_mesh(obj.data); bm.free()


def subdiv_partial(obj, ratio):
    """对随机部分面细分（避免面数一步跳档超上限）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    faces = [f for f in bm.faces if random.random() < ratio]
    edges = list({e for f in faces for e in f.edges})
    if edges:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=False)
    bm.to_mesh(obj.data); bm.free()


def refine(obj, lo, hi, pr=0.5):
    """细分逼近 [lo, hi]：先全量×4，再部分细分（pr=部分细分面比例；大石调小防面数跳档）。"""
    guard = 0
    while tris_of(obj) < lo and guard < 12:
        if tris_of(obj) * 4 <= hi:
            subdiv(obj, 1)
        else:
            subdiv_partial(obj, pr)
        guard += 1


def bump(obj, amp):
    """沿顶点法线凹凸：粗糙石面颗粒感（比全向抖动更显质感）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * random.uniform(-amp, amp)
    bm.to_mesh(obj.data); bm.free()


def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False


def triangulate(obj):
    """导出前全量三角化：非平面面经顶点位移后可成"蝴蝶结"形，Unity 判自交丢弃（M3 教训）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data); bm.free()


def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def soften_top(obj, thr):
    """顶部软化：高于 thr×max_z 的顶点按 0.45 系数压缩——低模 ico 尖顶在大尺寸下显突兀。"""
    vs = obj.data.vertices
    zmax = max(v.co.z for v in vs)
    cut = zmax * thr
    for v in vs:
        if v.co.z > cut:
            v.co.z = cut + (v.co.z - cut) * 0.45


def taper(obj, kx_top, ky_top):
    """底部→顶部横向收缩（kx/ky=顶部保留比例）：楔形石坯（2026-10-13，SM_GorgeRock_D 斜靠石）。"""
    vs = obj.data.vertices
    zmax = max(v.co.z for v in vs) or 1.0
    for v in vs:
        t = max(0.0, min(1.0, v.co.z / zmax))
        v.co.x *= 1.0 - (1.0 - kx_top) * t
        v.co.y *= 1.0 - (1.0 - ky_top) * t


def center_origin(obj):
    """几何包围盒中心移到原点（Unity 按中心摆位），返回原始尺寸。"""
    vs = obj.data.vertices
    mn = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
    mx = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
    obj.data.transform(Matrix.Translation(-(mn + mx) * 0.5))
    obj.data.update()
    return mx - mn


# ---------- 材质 ----------
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


# ---------- 导出 ----------
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
def build_rock(name, size, ry, rz, amp_xy, amp_z, bump_amp, soften=None,
               taper_xy=None, refine_lo=1200, refine_pr=0.5):
    """不规则巨石：单位 ico 球（底 z=0 顶 z=1）→ 非均匀缩放 → 大扰动定形 →
    细分逼近预算 → 法线颗粒 → 平直着色/三角化 → 几何中心归原点。
    taper_xy=(kx, ky)：顶部横向收缩比（楔形石）；refine_lo/refine_pr：细分下限与部分细分比例。"""
    o = add_ico(name, 0.5, (0, 0, 0.5), subdiv=1)      # 80 tris 基底
    o.scale = (size, size * ry, size * rz)
    apply_transform(o)
    jitter(o, amp_xy, amp_z=amp_z)                      # 大扰动（不规则轮廓，0.12×size 级）
    if taper_xy is not None:
        taper(o, taper_xy[0], taper_xy[1])
    if soften is not None:
        soften_top(o, soften)
    refine(o, refine_lo, TRIS_BUDGET[name], refine_pr)  # 细分逼近目标区间（预期落 1280~2900）
    bump(o, bump_amp)                                   # 沿法线颗粒（石面风化）
    jitter(o, 0.01, amp_z=0.01)                         # 细微二次扰动
    flat(o)
    triangulate(o)
    dims = center_origin(o)
    return o, dims


def render_rocks(rocks):
    """两件并排总览（仅内存操作，不影响已保存的 blend 与已导出 FBX）。"""
    import mathutils
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.05, 0.06, 0.08, 1)
    bg.inputs[1].default_value = 1.0
    # 并排摆位（底部贴地、微沉；宽度自适应，供 4 件并排总览）
    x_cursor = 0.0
    total_w = sum(d.x for _, d in rocks) + 1.0 * (len(rocks) - 1)
    for o, d in rocks:
        o.location = (x_cursor + d.x * 0.5 - total_w * 0.5, 0, d.z * 0.48)
        x_cursor += d.x + 1.0
    # 地面（承影，不导出）
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.02))
    set_material(bpy.context.object, "M_Ground_Render")
    # 相机
    cam_data = bpy.data.cameras.new("RockCam")
    cam_data.lens = 38
    cam = bpy.data.objects.new("RockCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -30.0, 9.0)
    direction = mathutils.Vector((0.0, 0.0, 2.2)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    # 灯光（主 + 补）
    sun_data = bpy.data.lights.new("RockSun", type='SUN')
    sun_data.energy = 2.4
    sun = bpy.data.objects.new("RockSun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.75, 0.15, 0.5)
    fill_data = bpy.data.lights.new("RockFill", type='SUN')
    fill_data.energy = 0.7
    fill = bpy.data.objects.new("RockFill", fill_data)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (1.2, -0.3, -2.2)
    # 引擎（EEVEE 优先，回退 CYCLES）
    engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        if cand in engines:
            scene.render.engine = cand
            break
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    os.makedirs(RENDER_DIR, exist_ok=True)
    out = os.path.join(RENDER_DIR, "gorge_rocks.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    size = os.path.getsize(out) if os.path.exists(out) else 0
    assert size > 20000, f"渲染图过小: {size}B"
    print(f"RENDER ok gorge_rocks.png {size}B engine={scene.render.engine}")


def render_portal(rocks):
    """门户试摆（2026-10-13 巨石岗重做）：两块 D 相向斜靠成 V（各倾 14°、缝底 ~1.9m）+ B 压顶
    （底面 ~1.42m）——校验斜靠层/顶盖尺度与采光 V 缝观感（仅内存操作，不保存）。"""
    import mathutils
    scene = bpy.context.scene
    d_o, d_d = rocks[3]
    b_o, b_d = rocks[1]
    d2 = d_o.copy(); d2.data = d_o.data.copy()
    b2 = b_o.copy(); b2.data = b_o.data.copy()
    for o in (d2, b2):
        scene.collection.objects.link(o)

    def lean_place(o, x, tilt):
        o.location = (0, 0, 0)
        o.rotation_euler = (0, tilt, 0)
        bpy.context.view_layer.update()
        zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
        o.location = (x, 0, -0.15 - min(zs))

    lean_place(d_o, -3.2, 0.244)     # 左石向内倾 14°（底缝 ~1.9m）
    lean_place(d2, 3.2, -0.244)      # 右石镜像
    b2.scale = (0.6, 0.6, 0.6)
    b2.location = (0, 0, 0)
    b2.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    zs = [(b2.matrix_world @ v.co).z for v in b2.data.vertices]
    b2.location = (0, 0, 1.42 - min(zs))    # 压顶底面 ≈1.42m（蹲行净高）
    # 相机：缝口低视角看门户（顶部 V 形天窗应可见）
    cam = bpy.data.objects["RockCam"]
    cam.data.lens = 30
    cam.location = (0.0, -15.0, 2.6)
    direction = mathutils.Vector((0.0, 0.5, 2.8)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    out = os.path.join(RENDER_DIR, "gorge_rocks_portal.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    size = os.path.getsize(out) if os.path.exists(out) else 0
    assert size > 20000, f"渲染图过小: {size}B"
    print(f"RENDER ok gorge_rocks_portal.png {size}B")


def main():
    clear_scene()
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(SCENES_DIR, exist_ok=True)
    rocks = [
        build_rock("SM_GorgeRock_A", 3.5, 0.82, 0.92, 0.42, 0.34, 0.030, soften=0.78),
        build_rock("SM_GorgeRock_B", 5.0, 0.84, 0.48, 0.52, 0.20, 0.026),
        build_rock("SM_GorgeRock_C", 10.0, 0.78, 0.52, 1.15, 0.55, 0.050,
                   soften=0.80, refine_lo=2400, refine_pr=0.25),
        build_rock("SM_GorgeRock_D", 5.4, 0.57, 1.34, 0.55, 0.40, 0.028,
                   taper_xy=(0.45, 0.75), refine_lo=1600, refine_pr=0.12),
    ]
    dims_expect = {
        "SM_GorgeRock_C": ((7.5, 9.8), (6.0, 9.2), (4.2, 6.6)),
        "SM_GorgeRock_D": ((3.8, 5.8), (2.2, 4.4), (5.8, 8.8)),
    }
    for o, dims in rocks:
        if o.name in dims_expect:
            ex = dims_expect[o.name]
            assert (ex[0][0] <= dims.x <= ex[0][1] and ex[1][0] <= dims.y <= ex[1][1]
                    and ex[2][0] <= dims.z <= ex[2][1]), \
                f"{o.name} 尺寸超预期: ({dims.x:.2f}, {dims.y:.2f}, {dims.z:.2f})"
    total = 0
    for o, dims in rocks:
        set_material(o, "M_Cliff")                      # 岩缝巨石同族材质（2026-10-13 修复：此前遗漏 → 导出无材质、Unity 回退默认 Lit）
        tris = tris_of(o)
        assert 1000 <= tris <= TRIS_BUDGET[o.name], \
            f"{o.name} 面数超预算: {tris} (预算≤{TRIS_BUDGET[o.name]})"
        total += tris
        path = export_obj(o)
        fsz = os.path.getsize(path)
        assert fsz > 5000, f"{o.name} FBX 过小: {fsz}B"
        print(f"  {o.name}: dims=({dims.x:.2f}, {dims.y:.2f}, {dims.z:.2f}) "
              f"tris={tris} fbx={fsz}B")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES_DIR, "M6_outdoor_props.blend"))
    print(f"OK rocks={len(rocks)} total_tris={total}")
    if DO_RENDER:
        render_rocks(rocks)
        render_portal(rocks)


main()
