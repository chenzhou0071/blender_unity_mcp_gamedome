"""标定实验：在 Idle 姿态下，给脚骨（Foot）加不同角度矫正旋转，
测量鞋底跟/趾最低点差，寻找使鞋底压平的角度。

轴约定（Blender，面朝 +X，左=+Y，上=+Z）：
- 绕世界 Y 轴旋转 = "脚尖上翘/下压"（侧向轴，改变前后坡度）——就是我们要找的轴
- 脚骨整链：LeftFoot/RightFoot（+ 可选 LeftToeBase/RightToeBase 不动）

输出：每个测试角度下，左脚跟/趾三段的最低 z（左腿 y∈[0.06,0.16]）。

用法: blender.exe --background --factory-startup --python calib_feet.py
"""
import bpy
from mathutils import Matrix, Vector

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
bpy.ops.wm.open_mainfile(filepath=BLEND)

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']

def seg_min(tag):
    dg = bpy.context.evaluated_depsgraph_get()
    segs = {"heel": (-1e9, 0.02), "mid": (0.02, 0.05), "toe": (0.05, 1e9)}
    res = {}
    for m in meshes:
        ob = m.evaluated_get(dg)
        me = ob.to_mesh()
        for v in me.vertices:
            p = ob.matrix_world @ v.co
            if not (0.06 <= p.y <= 0.16):
                continue
            for k, (a, b) in segs.items():
                if a <= p.x < b and (k not in res or p.z < res[k]):
                    res[k] = p.z
        ob.to_mesh_clear()
    print(tag, {k: round(v, 4) for k, v in res.items()},
          "heel-toe gap=", round(res["heel"] - res["toe"], 4) if "heel" in res and "toe" in res else "?")

# 进入 Idle 姿态
ad = arm.animation_data
if ad is None:
    ad = arm.animation_data_create()
for tr in ad.nla_tracks:
    tr.mute = True
ad.action = bpy.data.actions["A_Idle"]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
seg_min("IDLE-baseline")

def wrot_add(bone, axis, deg):
    """在已有姿态基础上追加绕世界轴（原点）旋转（与 hero_anims.wrot 的数学一致）"""
    pb = arm.pose.bones[bone]
    R = Matrix.Rotation(deg * 3.14159265 / 180.0, 4, axis)
    pb.matrix_basis = pb.bone.matrix_local.inverted() @ R @ pb.bone.matrix_local @ pb.matrix_basis
    bpy.context.view_layer.update()

# 保存基准 basis（Idle f0 下脚骨的 basis）
foot_basis = {}
for bn in ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"):
    foot_basis[bn] = arm.pose.bones[bn].matrix_basis.copy()

def reset_feet():
    for bn, m in foot_basis.items():
        arm.pose.bones[bn].matrix_basis = m.copy()
    bpy.context.view_layer.update()

# 测试：绕世界 Y 轴（侧向轴）旋转脚骨
for deg in (10, 20, -10, -20):
    reset_feet()
    wrot_add("LeftFoot", "Y", deg)
    wrot_add("RightFoot", "Y", deg)
    seg_min(f"IDLE+FootY{deg:+d}")

# 同时转脚趾骨（保持鞋尖，转脚跟？）——先看上面结果
print("CALIB_DONE")
