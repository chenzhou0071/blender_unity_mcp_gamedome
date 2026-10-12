"""M6-1: 神庙重做资产——金字塔外壳/房间内装/壁挂火把。
headless: blender.exe --background --factory-startup --python temple_rebuild.py [-- --render]

坐标约定：部件参数一律用 Unity 语义 (x, 高度 y, z 北正)，落 bmesh 时转 Blender Z-up (x, -z, 高度)；
导出 axis_up='Y' 后即回 Unity 坐标（与 canyon_terrain / temple_kit 同惯例）。
金字塔 SM_Pyramid（原点=底边中心）：竖直厚墙基座（外 30×36 高 15；内腔 x±13 / z' -17~16 容纳放大房间+
楼梯间；北墙厚 2 中央开 4m×4.5m 门洞）+ 第 1/2 层收分台（24×30→18×24→12×18，坡度 0.5）+ 层顶檐口盖板
（逐层出挑 1m）+ 北立面门洞两侧对称装饰陡梯（坡 50° 不可上）与梯顶尽端浮雕门。
注：计划"外斜面收分"与"内腔 x±13 恒定"数学上不可共存（外斜面 y>10 处已收窄到 x<13），收分只在第 1/2 层。
其余 6 件（原点见各 build 注释）：HallFloor 顶面 y=0 / GrandStair 低端底面=原点，向 -z 爬升。
"""
import bpy, bmesh, random, os, sys, math
from mathutils import Vector, Euler

random.seed(23)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
EXPORT_DIR = os.path.join(ROOT, "export", "temple")
SCENES_DIR = os.path.join(ROOT, "scenes")
RENDER_DIR = os.path.join(ROOT, "..", "docs", "milestones", "M6")
DO_RENDER = "--render" in sys.argv

MATERIALS = {
    "M_Stone":      dict(color=(0.47, 0.39, 0.28, 1), rough=0.90),   # 暖砂岩（同 temple_kit）
    "M_Stone_Dark": dict(color=(0.30, 0.25, 0.18, 1), rough=0.92),   # 深棕灰石
    "M_TorchWood":  dict(color=(0.26, 0.16, 0.09, 1), rough=0.78),   # 深色木柄（新增）
    "M_Metal_Dark": dict(color=(0.23, 0.16, 0.11, 1), rough=0.60, metal=0.75),  # 暗锈铁（火盆口）
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


# ---------- 基础部件（Blender 坐标 / Unity 语义包装） ----------
def add_box(name, size, loc=(0, 0, 0), subdiv_cuts=0):
    """Blender 语义盒：size=(宽x, 深y_b, 高z_b)。"""
    bm = bmesh.new()
    ret = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=ret["verts"])
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    if subdiv_cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdiv_cuts, use_grid_fill=True)
    return _fin(bm, name)


def ubox(name, size, loc, **kw):
    """Unity 语义盒：size=(宽x, 高y, 深z)，loc=(x, 高度, 北坐标)。"""
    w, h, d = size
    x, y, z = loc
    return add_box(name, (w, d, h), (x, -z, y), **kw)


def frustum(name, w0, d0, w1, d1, y0, y1):
    """棱台体（Unity 语义）：底 w0×d0 @y0 → 顶 w1×d1 @y1，原点=底面中心。"""
    bm = bmesh.new()
    ring = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    vb = [bm.verts.new((sx * w0 / 2, -(sz * d0 / 2), y0)) for sx, sz in ring]
    vt = [bm.verts.new((sx * w1 / 2, -(sz * d1 / 2), y1)) for sx, sz in ring]
    bm.faces.new(vb)
    bm.faces.new(list(reversed(vt)))
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # 封闭体统一朝外（布尔差集前提）
    return _fin(bm, name)


def join_objs(objs, name):
    """合并多个对象（面 material_index 随 from_mesh 保留）为单个 mesh。"""
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    merged = _fin(bm, name)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return merged


# ---------- bmesh 编辑 ----------
def jitter(obj, amp, zmin=None, amp_z=None):
    """顶点随机抖动（风化感）。zmin: 仅处理高度 z>=zmin 的顶点。"""
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
    bm = bmesh.new(); bm.from_mesh(obj.data)
    faces = [f for f in bm.faces if random.random() < ratio]
    edges = list({e for f in faces for e in f.edges})
    if edges:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=False)
    bm.to_mesh(obj.data); bm.free()


def refine(obj, lo, hi):
    """细分逼近 [lo,hi]：先全量×4，再部分细分（照 temple_kit 思路）。
    末尾部分细分用 0.3（最坏 ×1.9）：从 <lo 起跳的终值必 ≤ lo×1.9 < hi，防随机撞上限。"""
    guard = 0
    while tris_of(obj) < lo and guard < 12:
        if tris_of(obj) * 4 <= hi:
            subdiv(obj, 1)
        else:
            subdiv_partial(obj, 0.3)
        guard += 1


def bump(obj, amp):
    """沿顶点法线凹凸：粗糙石面颗粒感。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * random.uniform(-amp, amp)
    bm.to_mesh(obj.data); bm.free()


def recess(obj, face_filter, thickness=0.1, depth=-0.05):
    """对满足条件的面组做 inset 凹陷（浮雕槽/砖面）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    faces = [f for f in bm.faces if face_filter(f)]
    if faces:
        bmesh.ops.inset_region(bm, faces=faces, thickness=thickness,
                               depth=depth, use_even_offset=True)
    bm.to_mesh(obj.data); bm.free()


def brickify(obj, face_filter, thick=0.035, depth=-0.024):
    """选定大面做砌缝分割：板面保持原位，板间缝槽沿面法线凹入（石板缝）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    sel = [f for f in bm.faces if f.calc_area() > 0.15 and face_filter(f)]
    if not sel:
        bm.free(); return
    bm.normal_update()
    ret = bmesh.ops.inset_individual(bm, faces=sel, thickness=thick, depth=0.0, use_even_offset=True)
    bm.normal_update()
    groove = -depth
    # 缝槽沿环带面平均法线推入（非逐顶点法线）——逐顶点会把板角斜法线顶点横向拖动，
    # 产生反向绕序面；Blender 双面渲染看不出，Unity 单面剔除下呈现透光细缝。
    v_n = {}
    for f in ret["faces"]:
        for v in f.verts:
            v_n[v] = v_n.get(v, Vector((0, 0, 0))) + Vector(f.normal)
    for v, n in v_n.items():
        if n.length_squared > 1e-12:
            v.co -= n.normalized() * groove
    bm.to_mesh(obj.data); bm.free()


def recalc(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data); bm.free()


def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False


def triangulate(obj):
    """导出前全量三角化：非平面 quad 会被 Unity 判自交丢弃（M3 教训）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data); bm.free()


def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def boolean_cut(obj, cutter):
    """布尔差集并应用（EXACT 求解器；cutter 用完即删）。"""
    bpy.context.view_layer.update()
    mod = obj.modifiers.new("bool", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    old = obj.data
    obj.data = me
    obj.modifiers.clear()
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter, do_unlink=True)
    for p in obj.data.polygons:
        p.use_smooth = False


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


# ---------- 资产构建 ----------
def build_pyramid():
    """竖直厚墙基座 + 两层收分台 + 檐口平台 + 北门洞 + 装饰陡梯 + 尽端浮雕门（原点=底边中心）。

    第 0 层（含房间/楼梯间）必须竖直厚墙：内腔 x±13 / z' -17~16 恒定（3B 的 RoomHalfX=12 +
    周墙 + 楼梯间贴此布置），外斜面在 y>10 处已收窄到 x<13，斜壳与恒定内腔不可共存。
    收分放第 1/2 层（实心台，玩家不可达）。北墙厚 2 = 计划 z22~24 世界坐标，门洞 4×4.5。
    """
    # 第 0 层：实体盒 − 内腔盒 − 门洞（竖直厚墙一体壳；北墙厚 2 / 南墙厚 1 / 东西厚 2）
    s0 = ubox("pyr_s0", (30, 14.7, 36), (0, 7.35, 0))
    boolean_cut(s0, ubox("cav0", (26, 15.7, 33), (0, 7.35, -0.5)))      # 内腔 x±13 / z' -17~16
    boolean_cut(s0, ubox("door_cut", (4, 4.5, 2.6), (0, 2.25, 17)))    # 北墙门洞 4×4.5
    # 第 1/2 层：收分实心台（坡度 0.5 = 3m/6m；底面沉入下层檐板 0.2m 防共面闪烁）
    s1 = frustum("pyr_s1", 24, 30, 18, 24, 14.7, 20.7)
    s2 = frustum("pyr_s2", 18, 24, 12, 18, 20.7, 26.7)
    # 层顶檐口盖板（每侧出挑 1m；cap0 兼作内腔顶盖，底面 y14.3 即室内天花之上 0.1）
    caps = [ubox("cap0", (32, 0.6, 38), (0, 14.6, 0)),
            ubox("cap1", (20, 0.6, 26), (0, 20.6, 0)),
            ubox("cap2", (14, 0.6, 20), (0, 26.6, 0))]
    # 北立面装饰陡梯：门洞两侧对称（中央 4.4m 槽保出门通路；rise0.6/run0.5 ≈50° 不可上）
    steps = []
    for i in range(24):
        y_c = 0.30 + 0.6 * i
        for sx in (1, -1):
            steps.append(ubox(f"dec_st{i}_{sx}", (3.6, 0.6, 0.5),
                              (sx * 4.0, y_c, 18.2)))
    # 尽端浮雕门：陡梯顶部中央（y 9.6~14.2）贴北墙面凸出 0.2；正面双层凹浮雕
    gate = ubox("dec_gate", (4.6, 4.6, 0.9), (0, 11.9, 17.75))
    recess(gate, lambda f: f.normal.y < -0.7, thickness=0.4, depth=-0.1)
    recess(gate, lambda f: f.normal.y < -0.7 and abs(f.calc_center_median().x) < 1.6,
           thickness=0.5, depth=-0.07)
    o = join_objs([s0, s1, s2] + caps + steps + [gate], "SM_Pyramid")
    # 处理链：布尔 n-gon → 三角化 → 自适应细分到 ~24k 上限 → 风化 → 法线重算
    triangulate(o)
    while tris_of(o) * 4 <= 24000:
        subdiv(o, 1)
    bump(o, 0.03)
    jitter(o, 0.05, zmin=0.25)
    recalc(o)
    flat(o)
    return o


def build_hall_floor():
    """房间大地板 24×20×0.5（顶面 y=0，原点=顶面中心）。"""
    o = ubox("SM_HallFloor", (24, 0.5, 20), (0, -0.25, 0), subdiv_cuts=1)
    recess(o, lambda f: f.normal.z > 0.9, thickness=0.10, depth=-0.02)      # 顶面微凹
    brickify(o, lambda f: f.normal.z > 0.9, thick=0.045, depth=-0.03)       # 顶面板缝
    return o


def build_ceiling():
    """天花梁板件 6×4（板下两道横梁沿 x 跨；拼铺房间顶 y=14，原点=顶面中心）。"""
    parts = [ubox("cl_slab", (6, 0.4, 4), (0, -0.2, 0), subdiv_cuts=1)]
    for sz in (1, -1):
        parts.append(ubox(f"cl_beam{sz}", (6, 0.5, 0.4), (0, -0.65, sz * 1.0)))
    o = join_objs(parts, "SM_Ceiling_A")
    brickify(o, lambda f: f.normal.z < -0.9, thick=0.04, depth=-0.02)       # 底面（朝房间）板缝
    return o


def build_pilaster():
    """壁柱 0.8 宽×0.5 凸×6 高（座+柱身+帽，正面竖凹槽；原点=底面中心，正面朝 Unity +z）。"""
    parts = [ubox("pl_base", (1.0, 0.4, 0.65), (0, 0.2, 0)),
             ubox("pl_body", (0.8, 5.2, 0.5), (0, 3.0, 0), subdiv_cuts=1),
             ubox("pl_cap", (1.0, 0.4, 0.6), (0, 5.8, 0))]
    o = join_objs(parts, "SM_Pilaster")
    recess(o, lambda f: f.normal.y < -0.9 and 0.6 < f.calc_center_median().z < 5.4
           and abs(f.calc_center_median().x) < 0.25, thickness=0.12, depth=-0.02)  # 正面中槽
    brickify(o, lambda f: f.normal.y < -0.9 and 0.6 < f.calc_center_median().z < 5.4,
             thick=0.04, depth=-0.02)
    return o


def build_floor_inlay():
    """中央浮雕地板 4×4×0.06（双层凹框+芯面；原点=底面中心）。"""
    o = ubox("SM_FloorInlay", (4, 0.06, 4), (0, 0.03, 0), subdiv_cuts=1)
    recess(o, lambda f: f.normal.z > 0.9, thickness=0.22, depth=-0.012)
    recess(o, lambda f: f.normal.z > 0.9 and abs(f.calc_center_median().x) < 1.55
           and abs(f.calc_center_median().y) < 1.55, thickness=0.3, depth=-0.01)
    return o


def build_grand_stair():
    """大楼梯：宽 4、高差 6、30 级×0.3 步深（水平 9m）、两侧 0.3 石沿；
    原点=低端底面中心、向 -z 爬升。"""
    parts = []
    for i in range(30):
        h = 0.2 * (i + 1)
        zc = -(i + 0.5) * 0.3
        parts.append(ubox(f"gs_{i}", (4.0, h, 0.3), (0, h / 2, zc)))
        for sx in (1, -1):
            hb = h + 0.35
            parts.append(ubox(f"gsr_{i}_{sx}", (0.3, hb, 0.3), (sx * 2.15, hb / 2, zc)))
    return join_objs(parts, "SM_GrandStair")


def build_torch():
    """壁挂火把：石托+木柄+火盆口（火心 y≈0.95，Unity 侧火焰球摆局部 +1.15 高）；
    原点=贴墙点，正面朝 Unity +z 伸出。材质槽 0=石 1=木 2=铁。"""
    wall = ubox("to_wall", (0.4, 0.5, 0.24), (0, 0.25, 0.12))               # 贴墙石托
    # 木柄：长 0.57，绕 x 转 38° 后中心平移到 (0,-0.325,0.525)——两端≈托内 (0,-0.15,0.30) → 碗底 (0,-0.50,0.75)
    # （Blender：前伸 = -y_b，上 = +z_b）
    shaft = add_box("to_shaft", (0.09, 0.09, 0.57))
    shaft.rotation_euler = Euler((math.radians(38), 0, 0))
    shaft.location = (0, -0.325, 0.525)
    shaft.data.transform(shaft.matrix_basis); shaft.matrix_basis.identity()
    bowl = ubox("to_bowl", (0.34, 0.22, 0.34), (0, 0.85, 0.55))             # 火盆口（上开）
    coal = ubox("to_coal", (0.26, 0.06, 0.26), (0, 0.95, 0.55))             # 炭火面
    for p in shaft.data.polygons:
        p.material_index = 1
    for ob in (bowl, coal):
        for p in ob.data.polygons:
            p.material_index = 2
    o = join_objs([wall, shaft, bowl, coal], "SM_Torch")
    o.data.materials.append(get_material("M_Stone"))
    o.data.materials.append(get_material("M_TorchWood"))
    o.data.materials.append(get_material("M_Metal_Dark"))
    return o


# ---------- 导出与处理 ----------
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


def finish(o, lo, hi, bump_amp, jit_amp):
    """通用处理链：细分到区间 → 风化 → 法线重算 → 平直 → 三角化。"""
    refine(o, lo, hi)
    bump(o, bump_amp)
    jitter(o, jit_amp, zmin=0.03)
    recalc(o)
    flat(o)
    triangulate(o)
    t = tris_of(o)
    assert lo <= t <= hi, f"{o.name} 面数超范围: {t} (期望 {lo}-{hi})"
    path = export_obj(o)
    size = os.path.getsize(path)
    assert size > 5000, f"{o.name} FBX 过小: {size}B"
    print(f"OK {o.name} tris={t} fbx={size}B")
    return t


# ---------- 渲染验证 ----------
def render_views(pyr, items):
    """金字塔外观（北面 3/4 + 顶视）、内装件总览、火把特写（仅内存操作）。"""
    import mathutils
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.05, 0.06, 0.08, 1)
    bg.inputs[1].default_value = 1.0
    cam_data = bpy.data.cameras.new("SurveyCam")
    cam = bpy.data.objects.new("SurveyCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
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

    # 图1/2 金字塔（内装件先移远；金字塔在构建原点：Blender x±15 / y_b±18 / 高 0~27；北=Blender -y）
    for o in items:
        o.location = (200, 200, 0)
    # 图1：北面 3/4 掠视（拉远看整体：门洞+装饰梯带+三层收分）
    shoot(os.path.join(RENDER_DIR, "temple_pyramid.png"),
          (26, -54, 26), (0, -3, 11), 40, 1280, 960)
    # 图2：正北立面（收分比例/层线/门洞与装饰梯带对称）
    shoot(os.path.join(RENDER_DIR, "temple_pyramid_front.png"),
          (0, -85, 13.5), (0, 0, 13.5), 65, 1024, 1024)
    # 图3：顶视（三层轮廓+檐口平台线）
    shoot(os.path.join(RENDER_DIR, "temple_pyramid_top.png"),
          (0, -2, 104), (0, -2, 7), 60, 1024, 1024)
    # 图4 内装件总览（金字塔移远；相机在北侧——正对 GrandStair 台阶面与朝北火把）
    pyr.location = (-220, 100, 0)
    hall, ceil, pil, inlay, stair, torch = items   # 顺序同 main 的 specs
    hall.location = (0, 0, 0)
    inlay.location = (2, -6, 0.01)
    pil.location = (-10, -4, 0)
    ceil.location = (8, -8, 0.45)
    stair.location = (0, -12, 0)
    torch.location = (-7, -9, 0)
    shoot(os.path.join(RENDER_DIR, "temple_interior.png"),
          (10, -34, 12), (0, -7, 3), 40, 1280, 960)
    # 图5 火把特写（其余全移远，火把回原点）
    hall.location = (200, 0, 0); inlay.location = (200, 0, 0)
    pil.location = (200, 0, 0); ceil.location = (200, 0, 0)
    stair.location = (200, 0, 0)
    torch.location = (0, 0, 0); torch.rotation_euler = (0, 0, 0)
    shoot(os.path.join(RENDER_DIR, "temple_torch.png"),
          (1.3, -2.8, 1.35), (0, -0.35, 0.85), 55, 1280, 960)


def main():
    clear_scene()
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(SCENES_DIR, exist_ok=True)
    pyr = build_pyramid()
    set_material(pyr, "M_Stone")
    t = tris_of(pyr)
    assert 2000 <= t <= 25000, f"金字塔面数超预算: {t}"
    p = export_obj(pyr)
    s = os.path.getsize(p)
    assert s > 5000, f"金字塔 FBX 过小: {s}B"
    print(f"OK SM_Pyramid tris={t} fbx={s}B")

    specs = [(build_hall_floor, "M_Stone", 0.006, 0.010),
             (build_ceiling, "M_Stone", 0.006, 0.008),
             (build_pilaster, "M_Stone", 0.006, 0.008),
             (build_floor_inlay, "M_Stone", 0.004, 0.005),
             (build_grand_stair, "M_Stone", 0.008, 0.012),
             (build_torch, None, 0.003, 0.004)]
    items = []
    for fn, mat, ba, ja in specs:
        o = fn()
        if mat:
            set_material(o, mat)
        finish(o, 1000, 1950, ba, ja)   # 预算 ≤2000（计划），留 50 余量给随机细分
        items.append(o)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES_DIR, "M6_temple.blend"))
    print(f"OK assets={len(items) + 1}")
    if DO_RENDER:
        render_views(pyr, items)


main()
