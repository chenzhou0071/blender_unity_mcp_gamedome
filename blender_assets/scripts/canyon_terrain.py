"""M6-1: 峡谷地形生成——七段剖面高度场 + 噪声 + SM_Step 台阶件 + FBX 导出。
headless 用法: blender.exe --background --factory-startup --python canyon_terrain.py [-- --render]
段落（沿路径轴，世界坐标已烘焙，Unity 里放置在原点）:
  z  24- 34  出口平台 y=0（接神庙地台）
  z  34- 46  下行坡道 y=0 → -1.5（视觉铺 SM_Step 台阶）
  z  46- 96  草原缓起伏 y≈-1.5±0.6
  z  96-126  岩缝段 y=-1.5 平底（|x|>1.4 升壁 3m，缝顶另摆横石）
  z 126-176  河谷下切（河床 y=-3.5，水面 y=-2.6，宽 18m）
  z 176-194  南岸高台 y=-1.5（深渊边缘可走行；爬绳段起点）
  z 194-208  深渊带（底 y=-32 全黑不可达，坠入即死；斜绳横越其上）
  z 208-216  对岸崖壁（35m 升至崖顶 y=3）
  z 216-254  崖顶平台 y=3（30×30 平坦，smoothstep 收边）
两侧崖壁：|x|>20 渐升 +15~+35（各段参数略不同）；噪声三频叠加（路径带 |x|<3 减半保可走性）。
坐标约定：Blender 里几何存 (x, -z, 高度)（Z-up 自然），导出（axis_up='Y'）后即 Unity 的 (x, 高度, z)。
"""
import bpy, bmesh, random, os, sys, math
from mathutils import Vector, noise

random.seed(11)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
EXPORT_DIR = os.path.join(ROOT, "export", "outdoor")
SCENES_DIR = os.path.join(ROOT, "scenes")
RENDER_DIR = os.path.join(ROOT, "..", "docs", "milestones", "M6")
DO_RENDER = "--render" in sys.argv

X_MIN, X_MAX, Z_MIN, Z_MAX = -40.0, 40.0, 24.0, 254.0
GRID = 1.25                       # 顶点间距（米）

MATERIALS = {
    "M_Terrain":    dict(color=(0.36, 0.30, 0.21, 1), rough=0.95),   # 岩土棕（峡谷地表）
    "M_Step_Stone": dict(color=(0.42, 0.41, 0.38, 1), rough=0.90),   # 石板灰（出口台阶）
}


# ---------- 场景与落地 ----------
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


# ---------- 高度场 ----------
def sstep(a, b, t):
    t = max(0.0, min(1.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def path_height(z):
    """路径中心线高度（分段 + smoothstep 过渡）。"""
    if z < 34:   return 0.0
    if z < 46:   return -1.5 * sstep(34, 46, z)                  # 出口坡道
    if z < 96:   return -1.5                                      # 草原
    if z < 126:  return -1.5                                      # 岩缝平底
    if z < 176:                                                  # 河谷下切
        k = sstep(126, 140, z) * (1 - sstep(164, 176, z))
        return -1.5 - 2.0 * k                                     # 河床 -3.5 → 回 -1.5
    if z < 194:  return -1.5                                      # 南岸高台（深渊边缘）
    if z < 208:  return -1.5 - 30.5 * sstep(194, 206, z)          # 断崖直落：深渊底 -32（全黑不可达）
    return -32.0 + 35.0 * sstep(208, 216, z)                      # 对岸崖壁 35m 升至崖顶 +3


def gorge_wall(x, z):
    """岩缝段两侧升壁：缝底 |x|<=1.4 平，向外渐升至 3m（沿 z 出入口 4m 内渐入渐出）。"""
    kz = sstep(96, 100, z) * (1.0 - sstep(122, 126, z))
    if kz <= 0.0:
        return 0.0
    ax = abs(x)
    if ax <= 1.4:
        return 0.0
    k = min(1.0, (ax - 1.4) / 2.6)
    return 3.0 * sstep(0.0, 1.0, k) * kz


def wall_height(x, z):
    """两侧崖壁抬升（|x|>20 渐升）。"""
    ax = abs(x)
    if ax < 20: return 0.0
    base = min(35.0, (ax - 20) * 1.4)
    wob = noise.noise(Vector((x * 0.05, z * 0.05, 7.3))) * 6.0    # 崖壁起伏
    return base + wob


def height(x, z):
    h = path_height(z) + gorge_wall(x, z) + wall_height(x, z)
    ax = abs(x)
    mask = 0.35 if ax < 3.0 else (1.0 if ax > 6.0 else 0.65)      # 路径带噪声减半
    h += noise.noise(Vector((x * 0.02, z * 0.02, 1.1))) * 3.0 * mask
    h += noise.noise(Vector((x * 0.08, z * 0.08, 2.2))) * 0.8 * mask
    h += noise.noise(Vector((x * 0.30, z * 0.30, 3.3))) * 0.15 * mask
    return h


def build_terrain():
    nx = int((X_MAX - X_MIN) / GRID) + 1        # 65
    nz = int((Z_MAX - Z_MIN) / GRID) + 1        # 185
    me = bpy.data.meshes.new("SM_CanyonTerrain")
    verts, faces = [], []
    for j in range(nz):
        z = Z_MIN + j * GRID
        for i in range(nx):
            x = X_MIN + i * GRID
            verts.append((x, -z, height(x, z)))   # Blender Z-up：(-y=路径轴, z=高度) → 导出即 Unity (x,y,z)
    for j in range(nz - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + nx, a + nx + 1, a + 1))   # 绕序：法线朝上（单面剔除兼容）
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = False
    obj = bpy.data.objects.new("SM_CanyonTerrain", me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ---------- 出口台阶件 ----------
def add_box(name, size, loc=(0, 0, 0), subdiv_cuts=0):
    bm = bmesh.new()
    ret = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=ret["verts"])
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    if subdiv_cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdiv_cuts, use_grid_fill=True)
    return _fin(bm, name)


def build_step():
    """单级台阶：宽 4m × 高 0.2m × 深 0.6m，原点在底面中心（Unity 直接按 z 摆放）。"""
    o = add_box("SM_Step", (4.0, 0.6, 0.2), loc=(0, 0, 0.1), subdiv_cuts=1)
    jitter(o, 0.008, zmin=0.03)
    return o


# ---------- 通用编辑 ----------
def jitter(obj, amp, zmin=None, amp_z=None):
    """顶点随机抖动（风化感）。zmin: 仅处理 z>=zmin 的顶点（保底面平整）。"""
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


def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False


def triangulate(obj):
    """导出前全量三角化：非平面 quad 会被 Unity 判自交丢弃（M3 教训，同 temple_kit）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data); bm.free()


def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


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


# ---------- 渲染验证 ----------
def render_views():
    """顶视 + 两个透视（仅内存操作，不影响已保存的 blend/已导出 FBX）。"""
    import mathutils
    scene = bpy.context.scene
    # 世界背景深色（地形之外不留白底；不用地面衬托——persp 视图大平面会穿帮）
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.05, 0.06, 0.08, 1)
    bg.inputs[1].default_value = 1.0
    # 相机
    cam_data = bpy.data.cameras.new("SurveyCam")
    cam_data.lens = 40
    cam = bpy.data.objects.new("SurveyCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    # 灯光
    sun_data = bpy.data.lights.new("SurveySun", type='SUN')
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("SurveySun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.75, 0.15, 0.5)
    fill_data = bpy.data.lights.new("SurveyFill", type='SUN')
    fill_data.energy = 1.0
    fill = bpy.data.objects.new("SurveyFill", fill_data)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (1.2, -0.3, -2.2)
    # 引擎
    engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        if cand in engines:
            scene.render.engine = cand
            break
    os.makedirs(RENDER_DIR, exist_ok=True)

    def shoot(path, loc, target, lens, rx, ry):
        cam_data.lens = lens
        cam.location = loc
        direction = mathutils.Vector(target) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        assert size > 20000, f"渲染图过小: {path} {size}B"
        print(f"RENDER ok {os.path.basename(path)} {size}B engine={scene.render.engine}")

    # 顶视：七段可辨
    shoot(os.path.join(RENDER_DIR, "terrain_top.png"),
          (0, -139, 340), (0, -139, 0), 32, 1024, 1536)
    # 透视 1：河谷中段回望——两侧崖壁夹持的峡谷纵深（草原→岩缝→河谷下切）
    shoot(os.path.join(RENDER_DIR, "terrain_persp1.png"),
          (6, -60, 5), (-2, -150, -2), 42, 1280, 960)
    # 透视 2：南岸高台边缘俯瞰——深渊断面→对岸崖壁→崖顶平台
    shoot(os.path.join(RENDER_DIR, "terrain_persp2.png"),
          (0, -160, 16), (0, -210, -4), 42, 1280, 960)


def main():
    clear_scene()
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(SCENES_DIR, exist_ok=True)
    terrain = build_terrain()
    set_material(terrain, "M_Terrain")
    flat(terrain)
    triangulate(terrain)
    verts = len(terrain.data.vertices)
    assert verts == 185 * 65, f"地形顶点数不符: {verts}"     # 185×65=12025
    tris_t = tris_of(terrain)
    assert tris_t <= 30000, f"地形面数超预算: {tris_t}"
    p1 = export_obj(terrain)
    s1 = os.path.getsize(p1)
    assert s1 > 20480, f"地形 FBX 过小: {s1}B"
    print(f"OK terrain verts={verts} tris={tris_t} fbx={s1}B")

    step = build_step()
    set_material(step, "M_Step_Stone")
    flat(step)
    triangulate(step)
    tris_s = tris_of(step)
    p2 = export_obj(step)
    s2 = os.path.getsize(p2)
    assert s2 > 2000, f"SM_Step FBX 过小: {s2}B"
    print(f"OK SM_Step tris={tris_s} fbx={s2}B")

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES_DIR, "M6_canyon.blend"))
    if DO_RENDER:
        render_views()


main()
