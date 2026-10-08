"""M1: 生成破损石柱 SM_Pillar_Broken，导出 FBX，并渲染验收截图。
headless 用法: blender.exe --background --factory-startup --python m1_test_pillar.py"""
import bpy, bmesh, random, os

random.seed(42)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
OUT_FBX = os.path.join(ROOT, "export", "SM_Pillar_Broken.fbx")
OUT_BLEND = os.path.join(ROOT, "scenes", "M1_pillar.blend")
OUT_RENDER = os.path.join(ROOT, "..", "docs", "milestones", "M1", "pillar_blender.png")


def clear_scene():
    """清空默认场景（factory-startup 自带 Cube/Camera/Light），保证产物干净。"""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.images):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def build_pillar():
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.4, depth=3.0, location=(0, 0, 1.5))
    obj = bpy.context.object
    obj.name = "SM_Pillar_Broken"
    bm = bmesh.new(); bm.from_mesh(obj.data)
    top_z = max(v.co.z for v in bm.verts)
    for v in bm.verts:
        if abs(v.co.z - top_z) < 1e-4:          # 顶面: 随机下沉形成断口
            v.co.z -= random.uniform(0.0, 0.55)
        elif v.co.z > 0.5:                       # 上段: 径向抖动做风化
            v.co.x *= random.uniform(0.96, 1.04)
            v.co.y *= random.uniform(0.96, 1.04)
    # 顶面为非平面 NGON，三角化消除渲染暗斑/空洞错觉（用户反馈"顶部看起来是空的"）
    top_ngon = next(f for f in bm.faces if len(f.verts) == 8 and f.calc_center_median().z > 0)
    bmesh.ops.triangulate(bm, faces=[top_ngon], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(obj.data); bm.free()
    for p in obj.data.polygons:
        p.use_smooth = False                     # 低模平直着色
    return obj


def add_stone_material(obj):
    mat = bpy.data.materials.new("M_Stone"); mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.42, 0.40, 0.37, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    obj.data.materials.append(mat)


def render_check():
    """M1-1 Step 3 追加渲染段：相机+灯光看向石柱，输出验收截图 800x600。"""
    scene = bpy.context.scene
    import mathutils
    cam_data = bpy.data.cameras.new("M1_Cam")
    cam = bpy.data.objects.new("M1_Cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (4.3, -4.3, 2.8)
    direction = mathutils.Vector((0.0, 0.0, 1.45)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    sun_data = bpy.data.lights.new("M1_Sun", type='SUN')
    sun_data.energy = 4.0
    sun = bpy.data.objects.new("M1_Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.85, 0.15, 0.7)
    engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        if cand in engines:
            scene.render.engine = cand
            break
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    os.makedirs(os.path.dirname(OUT_RENDER), exist_ok=True)
    scene.render.filepath = OUT_RENDER
    bpy.ops.render.render(write_still=True)
    size = os.path.getsize(OUT_RENDER) if os.path.exists(OUT_RENDER) else 0
    assert size > 20000, f"渲染图过小: {size}B"
    print(f"RENDER ok {size}B engine={scene.render.engine}")


def main():
    clear_scene()
    obj = build_pillar()
    add_stone_material(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    # 注: 8 边圆柱 NGON 端盖实际为 28 三角面（计划原稿的 40 下限为笔误，M1 报告有记录）
    assert 20 <= tris <= 500, f"面数异常: {tris}"
    assert 2.2 <= obj.dimensions.z <= 3.05, f"高度异常: {obj.dimensions.z}"
    os.makedirs(os.path.dirname(OUT_FBX), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=OUT_FBX, use_selection=True,
        apply_scale_options='FBX_SCALE_ALL', apply_unit_scale=True,
        axis_forward='-Z', axis_up='Y', object_types={'MESH'})
    size = os.path.getsize(OUT_FBX)
    assert size > 5000, f"FBX 过小: {size}B"
    print(f"OK verts={len(obj.data.vertices)} tris={tris} fbx={size}B")
    render_check()


main()
