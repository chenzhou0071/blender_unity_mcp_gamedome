# M0 工具笔记（双端 MCP 连通验证与工具登记）

> 日期：2026-10-08 · 状态：M0-4 完成 · 证据截图：`M0-blender-screenshot.png`、`M0-unity-screenshot.png`

## 1. 环境事实（实测）

| 项 | 实测值 |
|---|---|
| Blender | **5.2.2 LTS**（Steam 版） |
| Blender 插件 | mcp-for-blender addon **1.8**，协议 13 = 13（`up_to_date`），端口 **9876** |
| Unity 编辑器 | **6000.3.21f1**（URP 17.3.0） |
| Unity MCP 包 | com.coplaydev.unity-mcp **v10.3.0**（git main） |
| Unity 工程实际路径 | **`E:\pro\blender_mcp\game\3D-Demo`**（注意：比计划多一层"3D-Demo"） |
| Unity 场景 | `SampleScene`（Main Camera / Directional Light / Global Volume） |
| Blender 场景 | 空场景（`Scene`，0 对象）——M1 起开始生产 |

## 2. 关键配置要点（易踩坑）

1. **Unity 侧 Transport 必须为 `stdio`**（MCP for Unity 窗口 → Transport 下拉 → `stdio` → Start Session）。
   - Qoder 的 unityMCP 以 stdio 包装器运行，靠扫描 `C:\Users\windows\.unity-mcp\unity-mcp-status-*.json` 发现 Unity 实例（TTL 5 秒自动刷新，**无需重启 Qoder**）；
   - 该状态文件仅由 Unity 内部 stdio bridge（默认端口 **6400**）写出；HTTP Local 模式（8080）不写，会导致 "No Unity Editor instances found"。
2. mcp.json 中 uvx 用**全路径**（GUI 进程 PATH 不继承）；首次启动依赖已预下载，恢复期如需缓存可重跑 `uvx --from mcpforunityserver mcp-for-unity --help`。
3. Blender 插件 1.8 打开 Blender 时**自动启动** server（面板显示 "Connected on port 9876" 即正常，无需找 Start 按钮）。
4. **后续所有计划中 `game/Assets/...` 引用一律解释为 `game/3D-Demo/Assets/...`。**

## 3. blender 侧工具（9 个，实测可用）

| 工具 | 用途 | 要点 |
|---|---|---|
| `get_addon_status` | 状态自检 | 已实测通过（up_to_date=true） |
| `get_scene_info` | 读场景文本信息 | fields: placement/contents/health/settings；已实测 |
| `look` | 多视角截图/渲染 | mode: viewport/camera/angles/frames；图返回对话内；已实测（viewport） |
| `execute_blender_code` | 执行 bpy 代码 | 已实测（保存视口截图到文件）；**执行前确认不破坏用户数据** |
| `generate_3d` | AI 生成 3D | 需外部 API key，本次不用 |
| `search_assets` / `import_asset` | PolyHaven/Sketchfab 等库 | 当前均 off，本项目不用外部库 |
| `record_trajectory_feedback` | 轨迹反馈 | 用不到 |
| `disable_telemetry` | 关遥测 | 遥测已关（consent=false） |

## 4. unityMCP 侧工具（48 个，v10.3.0）

按后续里程碑用途分组（**M1-M5 引用此清单**）：

**场景与对象（M1/M2/M3 主力）**
`manage_scene`（get_hierarchy/create/load/save/validate —— 已实测 get_hierarchy）、`manage_gameobject`、`manage_components`、`manage_prefabs`、`find_gameobjects`

**物理与玩法（M2）**
`manage_physics`（Rigidbody/Collider/CharacterController 等）

**脚本（M2-M4）**
`create_script`、`manage_script`、`apply_text_edits`、`script_apply_edits`、`validate_script`、`execute_code`、`manage_script_capabilities`、`delete_script`、`get_sha`

**资产与材质（M1/M3）**
`manage_asset`、`manage_material`、`import_model`、`import_model_file`、`manage_texture`、`manage_shader`、`manage_graphics`

**相机与截图（全程验证用）**
`manage_camera`（screenshot 已实测：默认 ScreenCapture 全层捕获，可 output_folder/screenshot_file_name 落盘，include_image=true 返回内嵌 PNG）

**编辑器与诊断（全程）**
`read_console`（每次改动后查报错）、`manage_editor`（play/pause/stop/undo 等）、`refresh_unity`、`execute_menu_item`、`unity_docs`、`unity_reflect`、`debug_request_context`、`set_active_instance`（多实例路由，单实例暂不用）

**其他（暂不用）**
`manage_animation`（M4 可能用）、`manage_ui`（M5）、`manage_audio` 无（用 generate_audio？——音效走程序化 WAV+`manage_asset` 导入，M5 定）、`manage_build`（M5 可选打包）、`run_tests`/`get_test_job`、`manage_profiler`（M5 性能）、`manage_probuilder`、`manage_vfx`、`manage_packages`、`manage_scriptable_object`、`generate_image`/`generate_model`/`generate_audio`（生成式，暂不用）、`blender_bridge`（未探索）、`manage_tools`、`batch_execute`、`find_in_file`

## 5. M0 验证证据记录

| 验证项 | 调用 | 结果 |
|---|---|---|
| Blender 状态 | `get_addon_status` | up_to_date=true, 协议 13/13 |
| Blender 读场景 | `get_scene_info` | Scene 空场景，0 对象 |
| Blender 截图 | `look` (viewport) + `execute_blender_code` 落盘 | 视口截图正常，已存 `M0-blender-screenshot.png` |
| Unity 读场景 | `manage_scene get_hierarchy` | SampleScene 3 根对象（已含 URP 组件） |
| Unity 截图 | `manage_camera screenshot` | 已存 `M0-unity-screenshot.png`（768×387，game_view） |

## 6. 遗留事项

- Unity 工程（`game/3D-Demo`）尚未纳入 git 管理（文件数量大，待用户确认提交策略；.gitignore 已适配嵌套路径 `game/**/...`）。
- `game/Assets/Screenshots/` 为 unityMCP 截图默认落盘目录，运行时产生，不入 git（未加忽略规则，遇到再定）。
