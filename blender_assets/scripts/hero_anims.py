"""主角五段程序化动画：idle/walk/run/jump/climb → Action 推独立 NLA track + 4 帧条图。
用法: blender.exe --background --factory-startup --python hero_anims.py
产出: hero_rigged.blend 增加 5 个 Action（A_Idle 60f / A_Walk 27f / A_Run 20f / A_Jump 27f / A_Climb 36f）
      + docs/milestones/M4/anim_sheet_*.png（每动作 1 行 × 4 帧）
坐标系: 面朝 +X，左=+Y，上=+Z；前后摆=绕世界 Y 轴，侧向摆臂=绕世界 X 轴。
参数幅度严格按实施计划 M4-3 参数表，不另设。
"""
import bpy, os, math, sys
import numpy as np
from mathutils import Vector, Matrix

BLEND = r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"
OUTDIR = r"E:\pro\blender_mcp\docs\milestones\M4"
FPS = 30
D = math.radians

bpy.ops.wm.open_mainfile(filepath=BLEND)
main = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print("OPEN", main.name, arm.name, len(arm.data.bones), "bones")

bpy.context.scene.render.fps = FPS

# 全骨 XYZ 欧拉（关键帧写入 rotation_euler 通道）
for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'

# —— NLA/action 清场（幂等，可重跑）——
ad = arm.animation_data if arm.animation_data else arm.animation_data_create()
for tr in list(ad.nla_tracks):
    ad.nla_tracks.remove(tr)
ANAMES = ["A_Idle", "A_Walk", "A_Run", "A_Jump", "A_Climb"]
for nm in ANAMES:
    if nm in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[nm])

# —— 姿势工具（世界轴旋转/平移，枢轴=骨根）——
def clear_pose():
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)

def wrot(bone, axis, deg):
    """相对 rest 绕世界 axis 旋转 deg°（作用在骨架空间=世界，因骨架无对象变换）"""
    pb = arm.pose.bones[bone]
    R = Matrix.Rotation(D(deg), 4, axis)
    pb.matrix_basis = pb.bone.matrix_local.inverted() @ R @ pb.bone.matrix_local

def wloc(bone, dx=0.0, dy=0.0, dz=0.0):
    """世界空间平移（覆盖式，每帧独立调用）"""
    pb = arm.pose.bones[bone]
    M = pb.matrix_basis.copy()
    M.translation = pb.bone.matrix_local.to_3x3().inverted() @ Vector((dx, dy, dz))
    pb.matrix_basis = M

def wrot2(bone, ops):
    """多轴世界旋转合成（按列表顺序依次左乘：R = Rn @ ... @ R1）"""
    pb = arm.pose.bones[bone]
    R = Matrix.Identity(4)
    for axis, deg in ops:
        R = Matrix.Rotation(D(deg), 4, axis) @ R
    pb.matrix_basis = pb.bone.matrix_local.inverted() @ R @ pb.bone.matrix_local

def walign2(bone, target_dir):
    """把骨的当前世界朝向转到 target_dir（基于当前姿态，考虑父链）"""
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    M = pb.matrix.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(target_dir).normalized())
    newM = (q.to_matrix().to_4x4() @ M.to_3x3().to_4x4()).to_4x4()
    newM.translation = M.translation
    pb.matrix = newM
    bpy.context.view_layer.update()

def nlerp(a, b, k):
    """方向向量线性插值并归一化"""
    return Vector(a).lerp(Vector(b), k).normalized()

def mir(d):
    """方向向量左右镜像（y 分量取反）"""
    return (d[0], -d[1], d[2])

# 手臂基础姿态：rest 为 T-pose（水平），绕世界 X 放下 90° 成贴身垂臂（左负右正，约留 5° 自然外张）
ARM_DROP_L, ARM_DROP_R = -90.0, +90.0
# 腿部收拢：rest 站距偏宽（双脚间距约 0.36m），绕世界 X 向内收 8°（左负右正）
LEG_IN_L, LEG_IN_R = -8.0, +8.0
# M4-7 反馈：走路/跑步时腿再收拢（8°→12°，向前后摆时仍保持侧向并拢）
LEG_MV_L, LEG_MV_R = -12.0, +12.0
# 脚部矫正：鞋底前后坡度压平（M4 验收反馈"高台悬空"）。
# Blender 标定实验（calib_feet.py）：Idle 姿态下绕世界 Y 轴 -10° 可将跟/趾底高差
# 由 1.04cm 降至 0.09cm（模型单位），左右脚同向。
FOOT_FIX = -10.0

def key_all(frame):
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_euler", frame=frame)
        pb.keyframe_insert("location", frame=frame)

def begin(name):
    clear_pose()
    act = bpy.data.actions.new(name)
    ad.action = act
    return act

# —— 五段动画（幅度/帧数按计划参数表）——
def make_idle():
    """60f 正弦循环：呼吸 ±1.5°；Hips 上下 ±0.012m 双频；垂臂微晃 ±2° + 肘微屈 8°"""
    act = begin("A_Idle"); n = 60
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        wrot("Spine1", "Y", 1.5 * math.sin(ph))
        wrot("LeftUpLeg", "X", LEG_IN_L)                       # 收腿基分（消除 rest 宽站距）
        wrot("RightUpLeg", "X", LEG_IN_R)
        s2 = 2.0 * math.sin(ph)
        wrot2("LeftArm", [("X", ARM_DROP_L), ("Y", s2)])
        wrot2("RightArm", [("X", ARM_DROP_R), ("Y", s2)])
        wrot("LeftForeArm", "Z", -8)
        wrot("RightForeArm", "Z", 8)
        wrot("LeftFoot", "Y", FOOT_FIX)                        # 脚部矫正：压平鞋底坡度
        wrot("RightFoot", "Y", FOOT_FIX)
        wloc("Hips", dz=0.012 * math.sin(2 * ph))
        key_all(f)
    return act

def make_walk():
    """27f 正弦循环：大腿 ±28° 左右反相（收腿 12°）；小腿 0~35° 滞后 0.6rad；垂臂 ∓20° 反相（肘微屈15°）；Hips ±0.03m 双频"""
    act = begin("A_Walk"); n = 27
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        wrot2("LeftUpLeg", [("X", LEG_MV_L), ("Y", -28 * math.sin(ph))])          # 内收+前摆（负角=前摆）
        wrot2("RightUpLeg", [("X", LEG_MV_R), ("Y", -28 * math.sin(ph + math.pi))])
        wrot("LeftLeg", "Y", 35 * max(0.0, math.sin(ph + 0.6)))       # 正角=屈膝（仅半波）
        wrot("RightLeg", "Y", 35 * max(0.0, math.sin(ph + math.pi + 0.6)))
        wrot2("LeftArm", [("X", ARM_DROP_L), ("Y", 20 * math.sin(ph))])           # 垂臂，与同侧腿反相
        wrot2("RightArm", [("X", ARM_DROP_R), ("Y", 20 * math.sin(ph + math.pi))])
        wrot("LeftForeArm", "Z", -15)
        wrot("RightForeArm", "Z", 15)
        wrot("LeftFoot", "Y", FOOT_FIX)                        # 脚部矫正：压平鞋底坡度
        wrot("RightFoot", "Y", FOOT_FIX)
        wloc("Hips", dz=0.03 * math.sin(2 * ph))
        key_all(f)
    return act

def make_run():
    """20f 正弦循环：大腿 ±48°（含收腿 12° 基分）；摆臂=贴身直给方向（大臂前后摆+肘屈约90°）；躯干前倾 8°；Hips ±0.05m 双频"""
    act = begin("A_Run"); n = 20
    ARM_F, ARM_B = (0.66, 0.10, -0.74), (-0.50, 0.10, -0.86)   # 大臂：前摆端点/后摆端点（y=贴身侧偏）
    FA_F, FA_B = (0.99, 0.09, 0.13), (0.42, 0.09, -0.90)       # 前臂：前摆近水平前伸（肘约125°展开）/后摆垂落髋侧
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        wrot("Spine", "Y", 8)                                  # 固定前倾（上向骨正角=前倾）
        wrot2("LeftUpLeg", [("X", LEG_MV_L), ("Y", -48 * math.sin(ph))])
        wrot2("RightUpLeg", [("X", LEG_MV_R), ("Y", -48 * math.sin(ph + math.pi))])
        wrot("LeftLeg", "Y", 60 * max(0.0, math.sin(ph + 0.6)))
        wrot("RightLeg", "Y", 60 * max(0.0, math.sin(ph + math.pi + 0.6)))
        kL = (1 - math.sin(ph)) / 2                            # 左臂相位（与左腿反相：0=后摆 1=前摆）
        kR = (1 + math.sin(ph)) / 2                            # 右臂相位
        walign2("LeftArm", nlerp(ARM_B, ARM_F, kL))
        walign2("RightArm", nlerp(mir(ARM_B), mir(ARM_F), kR))
        walign2("LeftForeArm", nlerp(FA_B, FA_F, kL))
        walign2("RightForeArm", nlerp(mir(FA_B), mir(FA_F), kR))
        wrot("LeftFoot", "Y", FOOT_FIX)                        # 脚部矫正：压平鞋底坡度
        wrot("RightFoot", "Y", FOOT_FIX)
        wloc("Hips", dz=0.05 * math.sin(2 * ph))
        key_all(f)
    return act

def make_jump():
    """27f 关键姿态（6 帧重做）：站→下蹲蓄力→蹬伸起跳→空中收腿→落地缓冲→回站；双臂不举高（M4-7 反馈：自然摆臂）"""
    act = begin("A_Jump")
    # (frame, hips_dz, spine前倾, 大腿, 屈膝, 大臂方向, 前臂方向)；腿部始终含收腿基分
    K = [
        (0,   0.00,  0,   0,   0, (0.00, 0.06, -1.00), (0.00, 0.06, -1.00)),   # 站（垂臂贴身）
        (4,  -0.16, 14, -50,  72, (-0.42, 0.10, -0.90), (-0.60, 0.08, -0.79)), # 下蹲蓄力：屈膝/臀降/躯干前倾/双臂后摆
        (9,   0.06,  4,   8,   4, (0.88, 0.12, 0.46), (0.82, 0.08, 0.57)),     # 蹬伸起跳：腿伸直/双臂前摆至胸前高度（不举过头）
        (16,  0.02,  6, -42,  72, (0.30, 0.10, -0.95), (0.35, 0.08, -0.93)),   # 空中收腿：大腿前收/屈膝/双臂自然垂放身侧
        (21, -0.12, 10, -28,  50, (0.45, 0.10, -0.85), (0.30, 0.08, -0.95)),   # 落地缓冲：屈膝吸收/双臂前下压
        (27,  0.00,  0,   0,   0, (0.00, 0.06, -1.00), (0.00, 0.06, -1.00)),   # 回站
    ]
    for f, dz, sp, th, kn, ua, fa in K:
        clear_pose()
        wloc("Hips", dz=dz)
        wrot("Spine", "Y", sp)
        wrot2("LeftUpLeg", [("X", LEG_IN_L), ("Y", th)])
        wrot2("RightUpLeg", [("X", LEG_IN_R), ("Y", th)])
        wrot("LeftLeg", "Y", kn)
        wrot("RightLeg", "Y", kn)
        walign2("LeftArm", ua)
        walign2("RightArm", mir(ua))
        walign2("LeftForeArm", fa)
        walign2("RightForeArm", mir(fa))
        wrot("LeftFoot", "Y", FOOT_FIX)                        # 脚部矫正：压平鞋底坡度
        wrot("RightFoot", "Y", FOOT_FIX)
        key_all(f)
    return act

def make_climb():
    """36f 循环：抓握交替（一手高举过顶抓握，一手屈肘收于胸口）+ 腿交替屈膝踩墙 + 躯干轻摆"""
    act = begin("A_Climb"); n = 36
    # 上臂目标方向：高举（上前偏侧）/ 垂下前收（胸口侧）；前臂：上手跟随 / 下手收向胸口
    UP_L, DN_L = (0.30, 0.22, 0.93), (0.28, 0.42, -0.86)
    UF_L, DF_L = (0.42, 0.16, 0.89), (0.78, -0.32, 0.42)
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        kL = (1 + math.cos(ph)) / 2                # cos 相位：f0 即"左手高举/右手收胸"极端姿势（消除首帧居中过渡态）
        kR = (1 + math.cos(ph + math.pi)) / 2
        walign2("LeftArm", nlerp(UP_L, DN_L, kL))
        walign2("RightArm", nlerp(mir(UP_L), mir(DN_L), kR))
        walign2("LeftForeArm", nlerp(UF_L, DF_L, kL))
        walign2("RightForeArm", nlerp(mir(UF_L), mir(DF_L), kR))
        wrot2("LeftUpLeg", [("X", LEG_IN_L), ("Y", -30 * math.sin(ph + 0.5 * math.pi))])
        wrot2("RightUpLeg", [("X", LEG_IN_R), ("Y", -30 * math.sin(ph + 1.5 * math.pi))])
        wrot("LeftLeg", "Y", 45 + 20 * math.sin(ph + 0.5 * math.pi))    # 屈膝踩墙（交替加深）
        wrot("RightLeg", "Y", 45 + 20 * math.sin(ph + 1.5 * math.pi))
        wrot("LeftFoot", "Y", FOOT_FIX)                        # 脚部矫正：压平鞋底坡度
        wrot("RightFoot", "Y", FOOT_FIX)
        wloc("Hips", dy=0.03 * math.sin(ph))
        key_all(f)
    return act

# —— 制作 + 断言（fcurve 非空 / 帧范围 / 循环闭合）——
def act_fcurves(act):
    """兼容新旧 Action 数据模型：4.3- legacy fcurves / 4.4+ layered(channelbag)"""
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out

acts = [make_idle(), make_walk(), make_run(), make_jump(), make_climb()]
EXPECT = {"A_Idle": 60, "A_Walk": 27, "A_Run": 20, "A_Jump": 27, "A_Climb": 36}
for act in acts:
    fr = act.frame_range
    fcs = act_fcurves(act)
    nfc = len(fcs)
    md = 0.0
    for fc in fcs:
        md = max(md, abs(fc.evaluate(fr[0]) - fc.evaluate(fr[1])))
    print(f"ACT {act.name:7s} fcurves={nfc:4d} range={tuple(round(v, 1) for v in fr)} loop_maxdiff={md:.6f}")
    assert nfc > 0, act.name
    assert abs(fr[1] - EXPECT[act.name]) < 0.01, act.name
    assert md < 1e-4, f"{act.name} loop gap {md}"

# —— push 独立 NLA track（供 M4-4 FBX 全量导出）——
ad.action = None
for act in acts:
    tr = ad.nla_tracks.new()
    tr.name = act.name
    tr.strips.new(act.name, 0, act)
print("NLA tracks:", [t.name for t in ad.nla_tracks])

# —— 保存（含动画；渲染场景不入库）——
clear_pose()
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(f"SAVED {BLEND} {os.path.getsize(BLEND)}B")

# —— FBX 导出（含 5 段动画：NLA 逐轨烘焙为 clip，供 Unity Humanoid 导入）——
FBX = r"E:\pro\blender_mcp\blender_assets\export\characters\SK_Explorer.fbx"
os.makedirs(os.path.dirname(FBX), exist_ok=True)
# packed 贴图无磁盘文件，先存为 PNG 供 FBX 外置引用（COPY 模式才能拷走）
TEXDIR = os.path.join(os.path.dirname(FBX), "textures")
os.makedirs(TEXDIR, exist_ok=True)
for im in bpy.data.images:
    if im.size and im.size[0] >= 512:
        p = os.path.join(TEXDIR, im.name + ".png")
        im.filepath_raw = p
        im.file_format = 'PNG'
        im.save()
        print("TEX_SAVED", p)
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
main.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(
    filepath=FBX, use_selection=True,
    apply_scale_options='FBX_SCALE_ALL', apply_unit_scale=True,
    axis_forward='-Z', axis_up='Y',
    object_types={'ARMATURE', 'MESH'},
    bake_anim=True, bake_anim_use_nla_strips=True, bake_anim_use_all_actions=False,
    add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
    path_mode='COPY', embed_textures=False)
fbsz = os.path.getsize(FBX)
print(f"EXPORTED {FBX} {fbsz}B")
assert fbsz > 50 * 1024, "FBX too small"

if "--skip-render" in sys.argv:
    print("EXPORT_DONE_SKIP_RENDER")
    raise SystemExit(0)

# —— 渲染场景（swing90 同款）——
gm = bpy.data.materials.new("G"); gm.use_nodes = True
gb = next(x for x in gm.node_tree.nodes if x.type == 'BSDF_PRINCIPLED')
gb.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1)
gb.inputs["Roughness"].default_value = 0.95
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, -0.5005))
bpy.context.object.data.materials.append(gm)

sd = bpy.data.lights.new("S", type='SUN'); sd.energy = 3.2
sun = bpy.data.objects.new("S", sd); bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (0.95, 0.15, 0.5)
fd = bpy.data.lights.new("F", type='SUN'); fd.energy = 1.6
fill = bpy.data.objects.new("F", fd); bpy.context.scene.collection.objects.link(fill)
fill.rotation_euler = (1.15, -0.25, -2.3)

cd = bpy.data.cameras.new("C"); cd.lens = 50
cam = bpy.data.objects.new("C", cd); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
engines = list(bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys())
for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    if cand in engines:
        bpy.context.scene.render.engine = cand
        break
sc = bpy.context.scene
sc.render.resolution_x = 640
sc.render.resolution_y = 640

def shoot(loc, target, path):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

# 采样帧（jump 取 5 个关键姿态的前 4+末尾；其余四等分）
SHOTS = {
    "A_Idle":  [0, 15, 30, 45],
    "A_Walk":  [0, 6, 13, 20],
    "A_Run":   [0, 5, 10, 15],
    "A_Jump":  [4, 9, 16, 21],
    "A_Climb": [0, 9, 18, 27],
}
CS = (2.3, 0.0, 0.85) if "--front" in sys.argv else (0.0, 2.3, 0.85)   # 默认侧视（前后摆）；--front 正视（腿侧向开合）
TGT = (0.0, 0.0, 0.05)

for act in acts:
    for tr in ad.nla_tracks:                    # 单轨激活（NLA 混合隔离）
        tr.mute = (tr.name != act.name)
    tiles = []
    for f in SHOTS[act.name]:
        bpy.context.scene.frame_set(f)
        p = os.path.join(OUTDIR, f"_tmp_{act.name}_{f}.png")
        shoot(CS, TGT, p)
        tiles.append(p)
    imgs = [bpy.data.images.load(p) for p in tiles]
    w, h = imgs[0].size
    canvas = np.zeros((h, w * 4, 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        canvas[:, i * w:(i + 1) * w] = px
    out = bpy.data.images.new(f"sheet_{act.name}", width=w * 4, height=h, alpha=True)
    out.pixels.foreach_set(canvas.ravel())
    outp = os.path.join(OUTDIR, f"anim_sheet_{act.name[2:].lower()}{'_front' if '--front' in sys.argv else ''}.png")
    out.filepath_raw = outp
    out.file_format = 'PNG'
    out.save()
    for im in imgs:
        bpy.data.images.remove(im)
    for p in tiles:
        os.remove(p)                            # 清理临时帧图
    print(f"saved {outp} {os.path.getsize(outp)}B")

print("ANIMS_DONE")
