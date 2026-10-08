# M1 验收报告：最小链路验证（石柱）

**日期**：2026-10-08 ｜ **结论**：✅ 通过——Blender 生成 → FBX 导出 → Unity 导入摆放，全链路打通。

---

## 1. 流水线与关键数据

| 环节 | 方式 | 结果 |
|---|---|---|
| 生成脚本 | `blender_assets/scripts/m1_test_pillar.py`（headless `--factory-startup`） | 两次运行输出完全一致（确定性验证 ✓） |
| 实时会话 | Blender MCP `execute_blender_code` 实时重建 | `BUILT verts 16, faces 15, tris 28`，与 headless 一致 |
| 网格健康 | 边界边 0、非流形 0 | 完全封闭，无破面 |
| FBX 导出 | `bpy.ops.export_scene.fbx`（-Z/Y、FBX_SCALE_ALL、仅选中对象） | `SM_Pillar_Broken.fbx` 15660B，导入回读仅 1 个对象、尺寸 0.8×0.8×2.99m |
| Unity 导入 | 复制至 `Assets/Art/Static/` → `refresh_unity` | Console 0 error / 0 warning |
| 场景摆放 | `manage_gameobject` 以 `prefab_path` 实例化 @ (0,0,0) | 姿态竖直站立、材质 `M_Stone` 正常、与 1m 对照 Cube 比例正确（高≈3 倍、宽≈0.8 倍） |

**石柱规格**：8 边圆柱 Ø0.8m；高 2.99m（断裂顶面下沉 0.014~0.49m 起伏）；平直着色；材质 M_Stone（灰褐、粗糙度 0.9）。

## 2. 计划偏差与处理（3 项）

1. **三角面断言笔误**：计划原稿 `40<=tris<=500`，8 边圆柱 NGON 端盖实际 28 tris → 修正下限为 20（脚本注释已记录）。
2. **`read_factory_settings` 实时会话副作用**：在 GUI 会话中执行会重载插件、切断 MCP 连接（代码中断，约 1~2 分钟后自动恢复）。已改用"逐对象删除"清场，脚本 headless 用法不受影响。
3. **顶面非平面 NGON 视觉瑕疵**（用户反馈"顶部没封顶"）：经查几何完全封闭，但从部分角度渲染出现暗斑/空洞错觉 → 对顶面做 `bmesh.ops.triangulate`（面数 10→15，tris 不变），渲染干净。**此为 M3 石柱资产的既定做法。**

## 3. 截图证据（docs/milestones/M1/）

| 文件 | 内容 |
|---|---|
| `pillar_blender.png` | headless EEVEE 渲染 800×600（断口清晰、无暗斑） |
| `pillar_blender_mcp.png` | 实时会话视口截图（含 MCP 面板 "Connected on port 9876" 状态） |
| `pillar_unity.png` | Unity 近景（石柱 + 1m 对照 Cube，比例验证） |
| `pillar_unity_overview.png` | Unity Scene 视图全景 |

## 4. Unity 导入参数结论（M3 复用）

- FBX 实例化后 `rotation.x = 270°`——**FBX 轴转换的正常表现**（Blender Z-up → Unity Y-up），实际姿态正确（竖直站立），**无需调整导入参数**。
- 导入用默认参数即可：Scale Factor 1、Use File Scale ✓；实例化方式 `manage_gameobject(prefab_path)` 稳定可用。
- 注意：`Manage Camera screenshot` 的 `scene_view` 模式不支持 `view_position`，需要定角度时用"定位截图"（game_view + view_position/view_target）。

## 5. 遗留与说明

- SampleScene 保留石柱实例作为链路证据（**不影响 M2**——M2 将使用新建 `Demo.unity`）；对照 Cube 已删除。
- `Assets/Screenshots/`（工具截图落盘目录）已加入 gitignore；正式证据统一归档 `docs/milestones/`。
- 临时测试文件 `mcp.blend` 已由用户删除，git 记录同步移除（历史版本仍可在 `b0cb6bf` 找回）。
- unityMCP 在步骤中出现过 1~2 次瞬时 "No Unity Editor instances found"（数秒后自动恢复），非阻塞。
