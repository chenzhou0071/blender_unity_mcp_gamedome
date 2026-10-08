"""M3: 生成古墓环境套件并批量导出 FBX（风格化低模，平直着色）。
headless 用法: blender.exe --background --factory-startup --python temple_kit.py [-- --render]
资产清单（计划表 A/B 变体分计共 17 件）：
  地砖×2 / 墙×2 / 柱×2 / 拱 / 台阶 / 门框 / 石门 / 压力板 / 推块 / 祭坛 / 宝物 / 火盆 / 碎石×2
"""
import bpy, bmesh, random, os, sys, math
from mathutils import Vector, Euler, Matrix

random.seed(7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
EXPORT_DIR = os.path.join(ROOT, "export", "temple")
SCENES_DIR = os.path.join(ROOT, "scenes")
RENDER_DIR = os.path.join(ROOT, "..", "docs", "milestones", "M3")
DO_RENDER = "--render" in sys.argv

# 细化目标：每件 1000-3000 tris（用户 M3-1 验收要求，取代原 50-1000 低模预算）
TRIS_MIN, TRIS_HI = 1000, 3000
# 细分后的高频细抖动幅度（默认 0.008；宝石/火盆等精修件更收敛）
FINE_AMP = {"SM_Treasure": 0.003, "SM_Brazier": 0.005}
# 沿法线凹凸幅度（次要颗粒：收敛以免糊平缝槽）
BUMP_AMP = {"SM_Treasure": 0.003, "SM_Brazier": 0.005, "SM_Debris_A": 0.022, "SM_Debris_B": 0.026}

MATERIALS = {
    "M_Stone":          dict(color=(0.47, 0.39, 0.28, 1), rough=0.90),   # 暖砂岩
    "M_Stone_Dark":     dict(color=(0.30, 0.25, 0.18, 1), rough=0.92),   # 深棕灰石
    "M_Metal_Dark":     dict(color=(0.23, 0.16, 0.11, 1), rough=0.60, metal=0.75),  # 暗锈铁
    "M_Fire":           dict(color=(1.0, 0.55, 0.15, 1), rough=1.0, emission=(1.0, 0.42, 0.06)),
    "M_Treasure_Glow":  dict(color=(1.0, 0.85, 0.35, 1), rough=0.3, emission=(1.0, 0.78, 0.25)),
    "M_Grass":          dict(color=(0.20, 0.30, 0.11, 1), rough=0.90),   # 幽暗草绿
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


def apply_transform(o):
    """把对象变换烘焙进顶点数据（位置/旋转/缩放归零）。"""
    o.data.transform(o.matrix_basis)
    o.matrix_basis.identity()


# ---------- 部件构建（bpy.ops 原语） ----------
def add_box(name, size, loc=(0, 0, 0), bevel=0.0, subdiv=0):
    bm = bmesh.new()
    ret = bmesh.ops.create_cube(bm, size=1.0)
    verts = ret["verts"]
    bmesh.ops.scale(bm, vec=size, verts=verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    if subdiv:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdiv, use_grid_fill=True)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=bevel,
                        segments=1, profile=0.5, affect='EDGES')
    return _fin(bm, name)


def add_cylinder(name, r, depth, loc, verts=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc)
    o = bpy.context.object; o.name = name
    apply_transform(o)
    return o


def add_cone(name, r1, r2, depth, loc, verts=12):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc)
    o = bpy.context.object; o.name = name
    apply_transform(o)
    return o


def add_ico(name, r, loc, subdiv=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    apply_transform(o)
    return o


def join_objs(objs, name):
    """合并多个对象（几何已在顶点层、transform 全零）为单个 mesh。"""
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    merged = _fin(bm, name)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return merged


# ---------- bmesh 编辑 ----------
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


def tris_of(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def subdiv_partial(obj, ratio):
    """对随机部分面细分（两级细节推进，避免面数跳档超上限）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    faces = [f for f in bm.faces if random.random() < ratio]
    edges = list({e for f in faces for e in f.edges})
    if edges:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=False)
    bm.to_mesh(obj.data); bm.free()


def refine(obj, lo=TRIS_MIN + 100, hi=TRIS_HI - 100):
    """细分逼近目标区间 [1000,3000]：先全量×4，再部分细分。"""
    guard = 0
    while tris_of(obj) < lo and guard < 12:
        if tris_of(obj) * 4 <= hi:
            subdiv(obj, 1)
        else:
            subdiv_partial(obj, 0.5)
        guard += 1


def bump(obj, amp):
    """沿顶点法线凹凸：粗糙石面颗粒感（比全向抖动更显质感）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * random.uniform(-amp, amp)
    bm.to_mesh(obj.data); bm.free()


def brickify(obj, face_filter, cuts=0, thick=0.035, depth=-0.024):
    """对选定大面做砌块分割：板面保持原位，仅板间缝槽沿法线凹入（石板缝）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    sel = [f for f in bm.faces if f.calc_area() > 0.15 and face_filter(f)]
    if not sel:
        bm.free(); return
    if cuts > 0:
        edges = list({e for f in sel for e in f.edges})
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
        bm.normal_update()
        sel = [f for f in bm.faces if f.calc_area() > 0.15 and face_filter(f)]
    bm.normal_update()
    ret = bmesh.ops.inset_individual(bm, faces=sel, thickness=thick, depth=0.0, use_even_offset=True)
    bm.normal_update()
    groove = -depth  # 参数沿用负值语义：缝槽下沉深度
    ring_verts = set(v for f in ret["faces"] for v in f.verts)
    for v in ring_verts:
        v.co -= v.normal * groove
    bm.to_mesh(obj.data); bm.free()


def ring_bands(obj, zs, band_h=0.07, shrink=0.86, r_max=0.45):
    """柱身分节：双水平环切并收腰，形成凸起腰线（石柱分节线脚）。"""
    for zc in zs:
        bm = bmesh.new(); bm.from_mesh(obj.data)
        for z in (zc, zc + band_h):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1),
                                   clear_outer=False, clear_inner=False)
        for v in bm.verts:
            if (abs(v.co.z - zc) < 1e-4 or abs(v.co.z - (zc + band_h)) < 1e-4) \
                    and v.co.xy.length < r_max:
                v.co.x *= shrink; v.co.y *= shrink
        bm.to_mesh(obj.data); bm.free()


def refine_region(obj, face_filter, cuts=2):
    """对选定区域面做一轮网格加密（为裂缝/雕带提供顶点密度）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.normal_update()
    sel = [f for f in bm.faces if face_filter(f)]
    if sel:
        edges = list({e for f in sel for e in f.edges})
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
    bm.to_mesh(obj.data); bm.free()


def _seg_dist2(p, a, b):
    """点 p 到线段 ab 的距离（x-z 平面内）。"""
    pa = Vector((p.x - a.x, 0, p.z - a.z))
    ab = Vector((b.x - a.x, 0, b.z - a.z))
    t = 0.0 if ab.length_squared < 1e-9 else max(0.0, min(1.0, pa.dot(ab) / ab.length_squared))
    return (pa - ab * t).length


def crack_line(obj, face_filter, start, angle_deg, length=2.0, width=0.09, depth=0.06,
               seed=1, branches=1):
    """在选定面上生成随机折线裂缝：局部加密后按距离场沿法线 V 形推入。"""
    rnd = random.Random(seed)
    n = max(3, int(length / 0.35))
    ang = math.radians(angle_deg)
    pts = [Vector(start)]
    for _ in range(n):
        ang += rnd.uniform(-0.45, 0.45)
        pts.append(pts[-1] + Vector((math.cos(ang), 0, math.sin(ang)))
                   * (length / n * rnd.uniform(0.7, 1.3)))
    paths = [pts]
    for _ in range(branches):
        i0 = int(len(pts) * rnd.uniform(0.4, 0.7))
        ba = ang + rnd.choice([-1, 1]) * rnd.uniform(0.7, 1.2)
        bp = [pts[i0]]
        for _ in range(3):
            ba += rnd.uniform(-0.4, 0.4)
            bp.append(bp[-1] + Vector((math.cos(ba), 0, math.sin(ba))) * (length / n * 0.9))
        paths.append(bp)
    segs = [s for p in paths for s in zip(p[:-1], p[1:])]
    xs = [v.x for p in paths for v in p]
    zs = [v.z for p in paths for v in p]
    lo_x, hi_x = min(xs) - width - 0.25, max(xs) + width + 0.25
    lo_z, hi_z = min(zs) - width - 0.25, max(zs) + width + 0.25

    def in_box(f):
        c = f.calc_center_median()
        return lo_x < c.x < hi_x and lo_z < c.z < hi_z

    def near_path(f):
        c = f.calc_center_median()
        return min(_seg_dist2(c, a, b) for a, b in segs) < width + 0.15

    refine_region(obj, lambda f: face_filter(f) and in_box(f), cuts=2)      # 区域整体加密
    refine_region(obj, lambda f: face_filter(f) and near_path(f), cuts=2)   # 缝带二次加密

    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.normal_update()
    sel = [f for f in bm.faces if face_filter(f) and in_box(f)]
    tgt = set(v for f in sel for v in f.verts)
    for v in tgt:
        d = min(_seg_dist2(v.co, a, b) for a, b in segs)
        if d < width:
            v.co -= v.normal * (depth * (1.0 - d / width))
    bm.to_mesh(obj.data); bm.free()


def molding_band(obj, z0, height=0.30, inset=0.09, out=0.03, y_dir=-1):
    """水平装饰雕带：切出带区后整体外凸，上下缘斜面过渡形成阴影。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    for z in (z0, z0 + height):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1),
                               clear_outer=False, clear_inner=False)
    bm.normal_update()
    sel = [f for f in bm.faces
           if f.normal.y * y_dir > 0.9
           and z0 + 0.02 < f.calc_center_median().z < z0 + height - 0.02]
    if sel:
        bmesh.ops.inset_region(bm, faces=sel, thickness=inset, depth=out, use_even_offset=True)
    bm.to_mesh(obj.data); bm.free()


def add_grass(obj, xs, y_base=-0.27):
    """墙脚放射状草簇（双面细叶，材质槽 1 = M_Grass）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    rnd = random.Random(7)
    for x0 in xs:
        base = Vector((x0 + rnd.uniform(-0.25, 0.25), y_base, 0.0))
        for _ in range(rnd.randint(5, 7)):
            a = rnd.uniform(0, math.tau)
            h = rnd.uniform(0.16, 0.30)
            w = rnd.uniform(0.03, 0.05)
            d = Vector((math.cos(a), 0, math.sin(a))) * w
            tip = base + Vector((math.cos(a) * rnd.uniform(0.06, 0.15),
                                 rnd.uniform(-0.16, -0.05), h))
            v1 = bm.verts.new(base - d)
            v2 = bm.verts.new(base + d)
            v3 = bm.verts.new(tip)
            f = bm.faces.new((v1, v2, v3))
            f.material_index = 1
            off = Vector((math.sin(a), 0, -math.cos(a))) * 0.002  # 背面片微偏移防重合
            vb1 = bm.verts.new(base - d + off)
            vb2 = bm.verts.new(base + d + off)
            vb3 = bm.verts.new(tip + off)
            f2 = bm.faces.new((vb1, vb3, vb2))
            f2.material_index = 1
    bm.to_mesh(obj.data); bm.free()


def add_ivy(obj, x0, y_face=-0.27, rise=2.4, sway=0.32, seed=5, leaf_n=28, branches=2):
    """墙正面攀爬藤蔓：蜿蜒主茎 + 侧枝 + 沿途双面菱形叶片（材质槽 1 = M_Grass）。"""
    rnd = random.Random(seed)
    bm = bmesh.new(); bm.from_mesh(obj.data)

    def ribbon(pts, lw=0.018):
        for p, q in zip(pts[:-1], pts[1:]):
            dx = Vector((lw, 0, 0))
            a1 = bm.verts.new(p - dx); a2 = bm.verts.new(p + dx)
            b1 = bm.verts.new(q + dx); b2 = bm.verts.new(q - dx)
            f = bm.faces.new((a1, a2, b1, b2)); f.material_index = 1
            off = Vector((0, -0.002, 0))
            o1 = bm.verts.new(p - dx + off); o2 = bm.verts.new(q - dx + off)
            o3 = bm.verts.new(q + dx + off); o4 = bm.verts.new(p + dx + off)
            f2 = bm.faces.new((o1, o2, o3, o4)); f2.material_index = 1

    def leaf(pos, angle, ln, wd, droop):
        tip = pos + Vector((math.cos(angle) * ln, -rnd.uniform(0.02, 0.05),
                            math.sin(angle) * ln - droop))
        side = Vector((-math.sin(angle), 0, math.cos(angle))) * wd
        mid1 = pos + (tip - pos) * 0.45 + side
        mid2 = pos + (tip - pos) * 0.45 - side
        va = bm.verts.new(pos); vb = bm.verts.new(tip)
        vc = bm.verts.new(mid1); vd = bm.verts.new(mid2)
        f = bm.faces.new((va, vc, vb)); f.material_index = 1
        f2 = bm.faces.new((va, vb, vd)); f2.material_index = 1
        off = Vector((0, -0.002, 0))
        va2 = bm.verts.new(pos + off); vb2 = bm.verts.new(tip + off)
        vc2 = bm.verts.new(mid1 + off); vd2 = bm.verts.new(mid2 + off)
        f3 = bm.faces.new((va2, vb2, vc2)); f3.material_index = 1
        f4 = bm.faces.new((va2, vd2, vb2)); f4.material_index = 1

    def grow(x_start, z_start, height, lean, seed_off, nleaf):
        r2 = random.Random(seed + seed_off)
        n = max(6, int(height / 0.18))
        pts = []
        for i in range(n + 1):
            t = i / n
            x = x_start + lean * t + sway * math.sin(t * 4.2 + seed_off) * (0.3 + t)
            pts.append(Vector((x, y_face + 0.012, z_start + t * height)))
        ribbon(pts)
        for i in range(1, n):
            for _ in range(max(1, nleaf // n)):
                ang = r2.uniform(0, math.tau)
                p = pts[i] + Vector((r2.uniform(-0.05, 0.05), 0, r2.uniform(-0.04, 0.04)))
                leaf(p, ang, r2.uniform(0.07, 0.12), r2.uniform(0.03, 0.05),
                     r2.uniform(0.02, 0.06))
        return pts

    pts = grow(x0, 0.0, rise, 0.0, 0, leaf_n)
    for b in range(branches):
        i0 = int(len(pts) * rnd.uniform(0.35, 0.7))
        bp = pts[i0]
        grow(bp.x, bp.z, rise * rnd.uniform(0.25, 0.45),
             rnd.choice([-1, 1]) * 0.25, 10 + b, max(6, leaf_n // 3))
    bm.to_mesh(obj.data); bm.free()


def recess(obj, face_filter, thickness=0.1, depth=-0.05):
    """对满足条件的面组做 inset 凹陷（浮雕槽/裂纹/砖面）。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    faces = [f for f in bm.faces if face_filter(f)]
    if faces:
        bmesh.ops.inset_region(bm, faces=faces, thickness=thickness,
                               depth=depth, use_even_offset=True)
    bm.to_mesh(obj.data); bm.free()


def chip_corner(obj, co, no, depth=0.15):
    """斜切一角并封口、切面推入（崩口）。co/no: 切平面点与法线。"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=bm.edges[:])
    for v in bm.verts:
        if abs((v.co - Vector(co)).dot(Vector(no))) < 1e-5:
            v.co -= Vector(no).normalized() * depth
            v.co.z -= depth * 0.4
    bm.to_mesh(obj.data); bm.free()


def boolean_cut(obj, cutter):
    """布尔差集并应用（EXACT 求解器）。"""
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


def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False


# ---------- 材质 ----------
def get_material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    spec = MATERIALS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = spec["color"]
    b.inputs["Roughness"].default_value = spec["rough"]
    b.inputs["Metallic"].default_value = spec.get("metal", 0.0)
    em = spec.get("emission")
    if em:
        val = (em[0], em[1], em[2], 1.0)
        for key in ("Emission Color", "Emission"):
            if key in b.inputs:
                b.inputs[key].default_value = val
                break
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = 2.0
    return m


def set_material(obj, name):
    obj.data.materials.clear()
    obj.data.materials.append(get_material(name))


# ---------- 资产构建 ----------
def build_floor_tile(name, broken):
    o = add_box(name, (2, 2, 0.3), loc=(0, 0, 0.15), subdiv=1)
    recess(o, lambda f: f.normal.z > 0.9, thickness=0.10, depth=-0.02)  # 砖面微凹
    brickify(o, lambda f: f.normal.z > 0.9, cuts=0, thick=0.045, depth=-0.03)  # 顶面板缝
    if broken:
        chip_corner(o, Vector((0.7, 0.7, 0.35)), Vector((1, 1, -0.35)).normalized(), depth=0.16)
        jitter(o, 0.045, zmin=0.24)
    else:
        jitter(o, 0.025, zmin=0.24)
    set_material(o, "M_Stone")
    return o


def build_wall(name, cracked):
    o = add_box(name, (4, 0.5, 3), loc=(0, 0, 1.5), bevel=0.025, subdiv=1)
    brickify(o, lambda f: abs(f.normal.y) > 0.9, cuts=0, thick=0.05, depth=-0.032)  # 正反面大板缝
    molding_band(o, z0=2.2, height=0.30)  # 上部水平装饰雕带（外凸线脚）
    if cracked:
        # 主斜裂（自上向右下贯通）+ 两条分叉 + 顶部崩口
        crack_line(o, lambda f: f.normal.y < -0.9, start=(-0.5, -0.25, 2.9), angle_deg=-62,
                   length=2.4, width=0.10, depth=0.07, seed=31, branches=2)
        chip_corner(o, Vector((1.6, -0.25, 2.88)), Vector((0.5, -0.3, 0.8)).normalized(), depth=0.16)
        jitter(o, 0.018, zmin=0.06)
    else:
        # 两条浅细风化纹
        crack_line(o, lambda f: f.normal.y < -0.9, start=(-1.3, -0.25, 2.55), angle_deg=-78,
                   length=1.5, width=0.06, depth=0.03, seed=11, branches=1)
        crack_line(o, lambda f: f.normal.y < -0.9, start=(0.9, -0.25, 0.7), angle_deg=-35,
                   length=0.9, width=0.05, depth=0.022, seed=12, branches=0)
        jitter(o, 0.012, zmin=0.06)
    set_material(o, "M_Stone")
    o.data.materials.append(get_material("M_Grass"))
    add_grass(o, [-1.5, 0.2, 1.7] if not cracked else [-0.9, 1.2])  # 墙脚草簇
    if cracked:
        add_ivy(o, x0=0.6, rise=2.2, sway=0.34, seed=15, leaf_n=26)   # 主藤（绕开裂口）
        add_ivy(o, x0=-1.9, rise=1.5, sway=0.22, seed=21, leaf_n=18)  # 副藤
    else:
        add_ivy(o, x0=-2.3, rise=2.5, sway=0.30, seed=5, leaf_n=30)   # 主藤（爬至雕带）
        add_ivy(o, x0=1.9, rise=1.8, sway=0.24, seed=9, leaf_n=20)    # 副藤
    return o


def build_pillar_whole():
    body = add_cylinder("pw_body", 0.25, 2.4, (0, 0, 1.2), verts=10)
    subdiv(body, cuts=2)
    base = add_box("pw_base", (0.7, 0.7, 0.3), (0, 0, 0.15), bevel=0.02)
    cap = add_box("pw_cap", (0.7, 0.7, 0.3), (0, 0, 2.55), bevel=0.02)
    top = add_box("pw_top", (0.8, 0.8, 0.3), (0, 0, 2.85), bevel=0.02)
    o = join_objs([body, base, cap, top], "SM_Pillar_Whole")
    ring_bands(o, (1.0, 2.0))  # 柱身两圈分节腰线
    jitter(o, 0.008, zmin=0.2)
    set_material(o, "M_Stone")
    return o


def build_pillar_broken():
    o = add_cylinder("SM_Pillar_Broken", 0.25, 3.0, (0, 0, 1.5), verts=10)
    bm = bmesh.new(); bm.from_mesh(o.data)
    top_z = max(v.co.z for v in bm.verts)
    for v in bm.verts:
        if abs(v.co.z - top_z) < 1e-4:            # 顶面随机下沉形成断口
            v.co.z -= random.uniform(0.0, 0.55)
        elif v.co.z > 2.0:                         # 上段径向风化
            v.co.x *= random.uniform(0.96, 1.04)
            v.co.y *= random.uniform(0.96, 1.04)
    bm.to_mesh(o.data); bm.free()
    subdiv(o, cuts=1)
    bm = bmesh.new(); bm.from_mesh(o.data)
    tops = [f for f in bm.faces if f.calc_center_median().z > 2.2 and f.normal.z > 0.3]
    if tops:
        bmesh.ops.triangulate(bm, faces=tops, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(o.data); bm.free()
    ring_bands(o, (1.0, 2.0))
    jitter(o, 0.01, zmin=2.1)
    set_material(o, "M_Stone")
    return o


def build_arch():
    col_l = add_box("arch_l", (0.8, 0.6, 3.2), (1.6, 0, 1.6), bevel=0.03, subdiv=1)
    col_r = add_box("arch_r", (0.8, 0.6, 3.2), (-1.6, 0, 1.6), bevel=0.03, subdiv=1)
    top = add_box("arch_top", (4.0, 0.6, 0.8), (0, 0, 3.6), bevel=0.03, subdiv=1)
    o = join_objs([col_l, col_r, top], "SM_Arch")
    brickify(o, lambda f: abs(f.normal.y) > 0.9, cuts=0, thick=0.045, depth=-0.03)  # 前后大板缝
    # 门洞: 下部矩形 + 上部半圆（圆柱横放）
    cut1 = add_box("cut_rect", (2.4, 1.4, 2.2), (0, 0, 1.1))
    boolean_cut(o, cut1)
    cut2 = add_cylinder("cut_arc", 1.2, 1.4, (0, 0, 2.0), verts=16)
    cut2.rotation_euler = Euler((math.radians(90), 0, 0))  # 轴向转 y（横放）
    apply_transform(cut2)
    boolean_cut(o, cut2)
    jitter(o, 0.01, zmin=0.1)
    set_material(o, "M_Stone")
    return o


def build_stairs():
    parts = []
    for i in range(5):
        h = 0.3 * (i + 1)
        y = -0.45 + 0.3 * i
        parts.append(add_box(f"st_{i}", (3.0, 0.3, h), (0, y, h / 2), bevel=0.012))
    o = join_objs(parts, "SM_Stairs")
    brickify(o, lambda f: f.normal.z > 0.9, cuts=0, thick=0.035, depth=-0.022)  # 各级踏面缝线
    jitter(o, 0.01, zmin=0.05)
    set_material(o, "M_Stone")
    return o


def build_door_frame():
    parts = [
        add_box("df_l", (0.5, 0.6, 4.2), (1.45, 0, 2.1), bevel=0.03),
        add_box("df_r", (0.5, 0.6, 4.2), (-1.45, 0, 2.1), bevel=0.03),
        add_box("df_t", (3.4, 0.6, 0.6), (0, 0, 3.9), bevel=0.03),
    ]
    o = join_objs(parts, "SM_DoorFrame")
    brickify(o, lambda f: abs(f.normal.y) > 0.9, cuts=1, thick=0.035, depth=-0.026)  # 框体面分块
    # 立柱内缘（朝向门洞中心）浅凹线脚
    recess(o, lambda f: f.normal.x < -0.9 and f.calc_center_median().x > 0 and f.calc_center_median().z < 3.6,
           thickness=0.06, depth=-0.025)
    recess(o, lambda f: f.normal.x > 0.9 and f.calc_center_median().x < 0 and f.calc_center_median().z < 3.6,
           thickness=0.06, depth=-0.025)
    jitter(o, 0.01, zmin=0.1)
    set_material(o, "M_Stone")
    return o


def build_stone_door():
    o = add_box("SM_StoneDoor", (3, 0.4, 4), (0, 0, 2.0), bevel=0.02, subdiv=1)
    # 双层浮雕：外缘一层 + 内芯一层（正面 -y）
    recess(o, lambda f: f.normal.y < -0.9, thickness=0.22, depth=-0.05)
    recess(o, lambda f: f.normal.y < -0.9 and abs(f.calc_center_median().x) < 1.15
           and 0.45 < f.calc_center_median().z < 3.3, thickness=0.35, depth=-0.04)
    brickify(o, lambda f: f.normal.y < -0.9, cuts=0, thick=0.055, depth=-0.045)  # 门板分块缝
    jitter(o, 0.012, zmin=0.15)
    set_material(o, "M_Stone_Dark")
    return o


def build_pressure_plate():
    o = add_box("SM_PressurePlate", (1.2, 1.2, 0.12), (0, 0, 0.06), subdiv=1)
    recess(o, lambda f: f.normal.z > 0.9, thickness=0.10, depth=-0.018)
    brickify(o, lambda f: f.normal.z > 0.9, cuts=0, thick=0.03, depth=-0.022)
    jitter(o, 0.006, zmin=0.05)
    set_material(o, "M_Metal_Dark")
    return o


def build_push_block():
    o = add_box("SM_PushBlock", (1, 1, 1), (0, 0, 0.5), bevel=0.03, subdiv=1)
    chip_corner(o, Vector((0.6, 0.6, 0.85)), Vector((0.6, 0.6, 1)).normalized(), depth=0.12)
    brickify(o, lambda f: True, cuts=0, thick=0.04, depth=-0.03)  # 各面分块凿面
    jitter(o, 0.018)
    set_material(o, "M_Stone")
    return o


def build_altar():
    parts = [
        add_box("alt_base", (2.0, 1.0, 0.55), (0, 0, 0.275), bevel=0.03, subdiv=1),
        add_box("alt_top", (1.6, 0.8, 0.45), (0, 0, 0.775), bevel=0.03, subdiv=1),
    ]
    o = join_objs(parts, "SM_Altar")
    recess(o, lambda f: f.normal.z > 0.9, thickness=0.12, depth=-0.02)  # 台面浅凹
    brickify(o, lambda f: f.calc_center_median().z > 0.05, cuts=0, thick=0.04, depth=-0.028)
    jitter(o, 0.008, zmin=0.1)
    set_material(o, "M_Stone")
    return o


def build_treasure():
    base = add_cylinder("tr_base", 0.14, 0.35, (0, 0, 0.175), verts=10)
    gem = add_ico("tr_gem", 0.3, (0, 0, 0.85), subdiv=1)
    gem.scale = (1.0, 1.0, 1.45)
    apply_transform(gem)
    o = join_objs([base, gem], "SM_Treasure")
    o.data.materials.append(get_material("M_Stone_Dark"))
    o.data.materials.append(get_material("M_Treasure_Glow"))
    for p in o.data.polygons:
        p.material_index = 1 if p.center.z > 0.5 else 0
    jitter(o, 0.005, zmin=0.05, amp_z=0.005)
    return o


def build_brazier():
    base = add_cylinder("br_base", 0.13, 0.55, (0, 0, 0.275), verts=10)
    bowl = add_cone("br_bowl", 0.14, 0.36, 0.40, (0, 0, 0.75), verts=12)
    # 挖空成开口碗：内锥略小且上移（口部敞开、底留 2cm 壁厚）
    inner = add_cone("br_bowl_in", 0.10, 0.335, 0.42, (0, 0, 0.78), verts=12)
    boolean_cut(bowl, inner)
    fire = add_cylinder("br_fire", 0.28, 0.06, (0, 0, 0.91), verts=12)  # 嵌在碗口内的炭火
    o = join_objs([base, bowl, fire], "SM_Brazier")
    o.data.materials.append(get_material("M_Metal_Dark"))
    o.data.materials.append(get_material("M_Fire"))
    for p in o.data.polygons:
        r = math.hypot(p.center.x, p.center.y)
        p.material_index = 1 if (p.center.z > 0.84 and r < 0.30) else 0
    jitter(o, 0.005, zmin=0.05, amp_z=0.005)
    return o


def build_debris(name, size):
    o = add_ico(name, 0.5, (0, 0, size * 0.45), subdiv=1)
    o.scale = (size, size * 0.82, size * 0.9)
    apply_transform(o)
    jitter(o, 0.1 * size)
    set_material(o, "M_Stone")
    return o


def build_all():
    objs = []
    objs.append(build_floor_tile("SM_FloorTile_A", broken=False))
    objs.append(build_floor_tile("SM_FloorTile_B", broken=True))
    objs.append(build_wall("SM_Wall_A", cracked=False))
    objs.append(build_wall("SM_Wall_B", cracked=True))
    objs.append(build_pillar_whole())
    objs.append(build_pillar_broken())
    objs.append(build_arch())
    objs.append(build_stairs())
    objs.append(build_door_frame())
    objs.append(build_stone_door())
    objs.append(build_pressure_plate())
    objs.append(build_push_block())
    objs.append(build_altar())
    objs.append(build_treasure())
    objs.append(build_brazier())
    objs.append(build_debris("SM_Debris_A", 0.5))
    objs.append(build_debris("SM_Debris_B", 0.9))
    return objs


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


def render_overview(objs):
    """陈列墙总览渲染（仅内存操作，不影响已保存的 blend/已导出 FBX）。"""
    import mathutils
    scene = bpy.context.scene
    for i, o in enumerate(objs):
        col, row = i % 6, i // 6
        o.location = (-6.5 + col * 2.6, -row * 4.5, 0)
    # 地面（承影，不导出）
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, -4.5, -0.02))
    ground = bpy.context.object
    set_material(ground, "M_Stone_Dark")
    # 相机
    cam_data = bpy.data.cameras.new("KitCam")
    cam_data.lens = 42
    cam = bpy.data.objects.new("KitCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.5, -23.5, 13.5)
    direction = mathutils.Vector((0.0, -4.8, 1.15)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    # 灯光
    sun_data = bpy.data.lights.new("KitSun", type='SUN')
    sun_data.energy = 2.6
    sun = bpy.data.objects.new("KitSun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.9, 0.1, 0.6)
    fill_data = bpy.data.lights.new("KitFill", type='SUN')
    fill_data.energy = 0.8
    fill = bpy.data.objects.new("KitFill", fill_data)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (1.1, -0.2, -2.4)
    # 引擎/分辨率
    engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        if cand in engines:
            scene.render.engine = cand
            break
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    os.makedirs(RENDER_DIR, exist_ok=True)
    out = os.path.join(RENDER_DIR, "kit_overview.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    size = os.path.getsize(out) if os.path.exists(out) else 0
    assert size > 20000, f"渲染图过小: {size}B"
    print(f"RENDER ok {size}B engine={scene.render.engine}")
    # 特写: 拱门/门框/石门一排
    cam.location = (2.5, -15, 4.5)
    direction = mathutils.Vector((-2.0, -4.5, 1.8)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    out2 = os.path.join(RENDER_DIR, "kit_arch_closeup.png")
    scene.render.filepath = out2
    bpy.ops.render.render(write_still=True)
    size2 = os.path.getsize(out2) if os.path.exists(out2) else 0
    assert size2 > 20000, f"特写渲染图过小: {size2}B"
    print(f"RENDER ok closeup {size2}B")
    # 特写2: 火盆（低角度验证开口碗与炭火）
    cam.location = (-1.3, -10.4, 1.7)
    direction = mathutils.Vector((-1.3, -9.0, 0.82)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    out3 = os.path.join(RENDER_DIR, "kit_brazier_closeup.png")
    scene.render.filepath = out3
    bpy.ops.render.render(write_still=True)
    size3 = os.path.getsize(out3) if os.path.exists(out3) else 0
    assert size3 > 20000, f"火盆特写渲染过小: {size3}B"
    print(f"RENDER ok brazier {size3}B")
    # 特写3: Wall_B 正面（裂纹/雕带/草簇/崩口验证，相机置于陈列排间空隙）
    cam_data.lens = 28
    cam.location = (1.3, -3.7, 1.8)
    direction = mathutils.Vector((1.3, 0.0, 1.5)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    out4 = os.path.join(RENDER_DIR, "kit_wall_closeup.png")
    scene.render.filepath = out4
    bpy.ops.render.render(write_still=True)
    size4 = os.path.getsize(out4) if os.path.exists(out4) else 0
    assert size4 > 20000, f"墙特写渲染过小: {size4}B"
    print(f"RENDER ok wall {size4}B")
    cam_data.lens = 42


def main():
    clear_scene()
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(SCENES_DIR, exist_ok=True)
    objs = build_all()
    # 计划表 A/B 变体分计共 17 件（16 类；计划正文"16"为计数笔误）
    assert len(objs) == 17, f"资产数量不符: {len(objs)}"
    total = 0
    for o in objs:
        refine(o)                                        # 细分至 1000-3000 面
        bump(o, BUMP_AMP.get(o.name, 0.008))             # 沿法线凹凸（次要颗粒）
        jitter(o, FINE_AMP.get(o.name, 0.004))           # 细微全向扰动
        flat(o)
        tris = tris_of(o)
        assert TRIS_MIN <= tris <= TRIS_HI, f"{o.name} 面数超范围: {tris}"
        total += tris
        path = export_obj(o)
        size = os.path.getsize(path)
        assert size > 5000, f"{o.name} FBX 过小: {size}B"
        print(f"  {o.name}: tris={tris} fbx={size}B")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES_DIR, "M3_kit.blend"))
    print(f"OK assets={len(objs)} total_tris={total}")
    if DO_RENDER:
        render_overview(objs)


main()
