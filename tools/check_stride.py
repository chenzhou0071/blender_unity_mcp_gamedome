"""测量 A_Walk / A_Run 中脚趾骨相对自身的前后（X）位移幅度，推算动画自然移动速度。
另外检查 Hips 的 X 波动（判断是否 in-place）。
用法: blender.exe --background --factory-startup --python check_stride.py
"""
import bpy

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
fps = bpy.context.scene.render.fps
print("scene fps =", fps)

ad = arm.animation_data
if ad is None:
    ad = arm.animation_data_create()
for tr in ad.nla_tracks:
    tr.mute = True


def sample(action_name):
    act = bpy.data.actions[action_name]
    ad.action = act
    fs, fe = act.frame_range
    dur = (fe - fs) / fps
    print(f"== {action_name}: frames {fs:.0f}-{fe:.0f}, duration {dur:.3f}s")
    names = ("LeftToeBase", "RightToeBase", "LeftFoot", "RightFoot", "Hips")
    minx = {}
    maxx = {}
    for f in range(int(fs), int(fe) + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        for bn in names:
            pb = arm.pose.bones[bn]
            w = arm.matrix_world @ pb.head
            minx[bn] = min(minx.get(bn, 1e9), w.x)
            maxx[bn] = max(maxx.get(bn, -1e9), w.x)
    hips_amp = maxx["Hips"] - minx["Hips"]
    print(f" Hips x amplitude: {hips_amp:.4f} (in-place if small)")
    for bn in ("LeftToeBase", "RightToeBase", "LeftFoot", "RightFoot"):
        print(f" {bn}: x amp {maxx[bn]-minx[bn]:.4f}")
    stride = max(maxx["LeftToeBase"] - minx["LeftToeBase"],
                 maxx["RightToeBase"] - minx["RightToeBase"])
    print(f" stride~{stride:.4f} -> implied speed {stride/(dur/2):.3f} m/s (per Blender unit)")
    return dur


sample("A_Walk")
sample("A_Run")
print("STRIDE_DONE")
