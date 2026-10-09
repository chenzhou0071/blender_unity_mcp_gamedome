"""检查 FBX：对象/材质/贴图引用与加载状态（自动重链接 .fbm 贴图包）。
用法: blender.exe --background --factory-startup --python inspect_fbx.py -- <xxx.fbx>
"""
import bpy, sys, os

argv = sys.argv
FBX = argv[argv.index("--") + 1] if "--" in argv else r"E:\pro\blender_mcp\blender_assets\export\temple\game.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)

print("=== OBJECTS ===")
tris_total = 0
for o in bpy.data.objects:
    if o.type == 'MESH':
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        tris_total += t
        mats = [ms.material.name if ms.material else None for ms in o.material_slots]
        print(f"  {o.name}  tris={t}  mats={mats}")
    else:
        print(f"  {o.name} ({o.type})")
print(f"TOTAL tris={tris_total}")

print("=== MATERIALS ===")
for m in bpy.data.materials:
    line = f"  {m.name} use_nodes={m.use_nodes}"
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                col = tuple(round(c, 3) for c in n.inputs["Base Color"].default_value)
                linked = n.inputs["Base Color"].is_linked
                line += f" base_color={col} linked={linked}"
            if n.type == 'TEX_IMAGE' and n.image:
                line += f" tex={n.image.name}"
    print(line)

print("=== IMAGES ===")
for im in bpy.data.images:
    print(f"  {im.name} {im.size[0]}x{im.size[1]} src={im.source} filepath={im.filepath} loaded={'OK' if im.size[0] > 0 else 'FAIL'}")

# 若贴图未加载，尝试从 fbx 同目录的 <name>.fbm 重链接
fbm_dir = os.path.splitext(FBX)[0] + ".fbm"
if os.path.isdir(fbm_dir):
    for im in bpy.data.images:
        if im.size[0] == 0:
            cand = os.path.join(fbm_dir, os.path.basename(im.filepath))
            if os.path.isfile(cand):
                im.filepath = cand
                im.reload()
                print(f"  RELINKED {im.name} -> {cand} loaded={'OK' if im.size[0] > 0 else 'FAIL'}")
