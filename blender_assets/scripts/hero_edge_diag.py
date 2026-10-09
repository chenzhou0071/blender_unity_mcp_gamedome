"""90°摆臂下肩区最差边的定位诊断: 对 PRE(修复前) / POST(修复后) 两个 blend 施加相同 fwd90 pose,
打印 ratio top10 边的 rest/pose 长度、绝对伸长、位置与两端权重; 统计"实际可见瑕疵"(ratio>5 且伸长>5mm)。只读。
"""
import bpy
import numpy as np
from mathutils import Vector, Matrix

CASES = [
    ("PRE ", r"E:\pro\blender_mcp\blender_assets\export\hero\_backup\hero_rigged_pre_shoulderfix.blend"),
    ("POST", r"E:\pro\blender_mcp\blender_assets\export\hero\hero_rigged.blend"),
]

def walign2(arm, bone, target_dir):
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    M = pb.matrix.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(target_dir).normalized())
    newM = (q.to_matrix().to_4x4() @ M.to_3x3().to_4x4()).to_4x4()
    newM.translation = M.translation
    pb.matrix = newM
    bpy.context.view_layer.update()

FWD90 = ['LeftArm', (1.0, 0.12, 0.06)]

for tag, blend in CASES:
    bpy.ops.wm.open_mainfile(filepath=blend)
    main = next(o for o in bpy.data.objects if o.type == 'MESH')
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    n = len(main.data.vertices)
    co0 = np.empty(n * 3)
    main.data.vertices.foreach_get("co", co0)
    co0 = co0.reshape(n, 3)
    ne = len(main.data.edges)
    ea = np.empty(ne * 2, dtype=np.int32)
    main.data.edges.foreach_get("vertices", ea)
    ea = ea.reshape(ne, 2)
    rest_len = np.linalg.norm(co0[ea[:, 0]] - co0[ea[:, 1]], axis=1)

    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    walign2(arm, "LeftArm", (1.0, 0.12, 0.06))
    walign2(arm, "RightArm", (1.0, -0.12, 0.06))
    walign2(arm, "LeftForeArm", (0.82, 0.10, 0.56))
    walign2(arm, "RightForeArm", (0.82, -0.10, 0.56))

    dg = bpy.context.evaluated_depsgraph_get()
    ev = main.evaluated_get(dg)
    me = ev.to_mesh()
    m = len(me.vertices)
    co = np.empty(m * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(m, 3)
    ev.to_mesh_clear()

    pose_len = np.linalg.norm(co[ea[:, 0]] - co[ea[:, 1]], axis=1)
    ratio = pose_len / (rest_len + 1e-12)
    stretch = pose_len - rest_len
    mid = 0.5 * (co0[ea[:, 0]] + co0[ea[:, 1]])
    mE = ((mid[:, 2] > 0.24) & (mid[:, 2] < 0.42) & (np.abs(mid[:, 1]) > 0.02)
          & (np.abs(mid[:, 1]) < 0.28) & (np.abs(mid[:, 0]) < 0.2))
    r = ratio.copy()
    r[~mE] = 0.0

    print(f"== {tag} fwd90 shoulder-zone edge analysis ==")
    order = np.argsort(-r)[:10]
    for i in order:
        a, b = int(ea[i, 0]), int(ea[i, 1])
        print(f"  ratio={ratio[i]:7.2f} rest={rest_len[i]*1000:6.2f}mm pose={pose_len[i]*1000:7.2f}mm "
              f"stretch={stretch[i]*1000:7.2f}mm mid=({mid[i,0]:+.3f},{mid[i,1]:+.3f},{mid[i,2]:+.3f})")
        for vi in (a, b):
            wl = sorted([(main.vertex_groups[g.group].name, round(g.weight, 2))
                         for g in main.data.vertices[vi].groups], key=lambda x: -x[1])[:3]
            print(f"      v{vi} {wl}")
    hard = (r > 5) & (stretch > 0.005)
    print(f"  [{tag}] edges ratio>5: {int((r > 5).sum())}, of which stretch>5mm: {int(hard.sum())}")
    s = stretch.copy()
    s[~mE] = 0.0
    j = int(np.argmax(s))
    print(f"  [{tag}] max-stretch edge: stretch={stretch[j]*1000:.2f}mm rest={rest_len[j]*1000:.2f}mm "
          f"ratio={ratio[j]:.2f} mid=({mid[j,0]:+.3f},{mid[j,1]:+.3f},{mid[j,2]:+.3f})")
print("EDGE_DIAG_DONE")
