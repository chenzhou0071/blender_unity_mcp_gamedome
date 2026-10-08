# 3D 游戏 Demo 实施计划（Blender MCP + Unity MCP）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **中文执行说明：** 本计划按里程碑 M0→M5 顺序执行。每个里程碑有"门禁"：开工前必须已获得用户明确指令；完成后停下汇报（截图 + 验收清单），等待用户确认后才可进入下一里程碑。**禁止自动连推。** 每个 Task 内的检查步骤即时执行、即时验证；每个 Task 结束时本地 git commit（不 push）。

**Goal:** 使用 Qoder 作为 MCP 客户端，操控 Blender MCP 建模 + Unity MCP 组装，产出一个「古墓丽影风格」可玩垂直切片（推石块开机关门 → 攀爬上高台 → 取得宝物完成）。

**Architecture:** 灰盒优先——先用 Unity primitives 跑通玩法（控制器/攀爬/机关），再由 Blender 生成正式资产逐个替换；主角模型、绑骨、动画、音效全部程序化/脚本化生成，不依赖外部素材；资产经 FBX 从 `blender_assets/export/` 流入 `game/Assets/Art/`。

**Tech Stack:** Blender 5.2（Steam 版）+ mcp-for-blender、Unity 6.3（6000.3.21f1，URP）+ CoplayDev/unity-mcp、Python（bpy 脚本 + 音效合成）、C#（游戏逻辑）、Git（本地仓库）。

**Spec:** `docs/superpowers/specs/2026-10-08-3d-game-demo-design.md`（一切细节以本 spec 为准）

## Global Constraints

- **门禁纪律**：每个里程碑须用户明确下达开工指令；完成后停下汇报等确认（用户记忆：逐任务确认，不自动连推）。
- **git**：仅本地 commit，不推送；导师指南文档不入库（已在 .gitignore）。
- **固定路径**（来自 spec 第 3 节）：
  - Blender：`E:\SteamLibrary\steamapps\common\Blender\blender.exe`（版本 5.2）
  - Unity 编辑器：`D:\Unity\Hub\Editor\6000.3.21f1\Editor\Unity.exe`
  - uvx 全路径：`C:\Users\windows\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uvx.exe`
  - Qoder MCP 配置：`C:\Users\windows\.qoder\mcp.json`
  - Qoder MCP 工具（schema 缓存）：`C:\Users\windows\AppData\Roaming\Qoder\SharedClientCache\projects\e--pro-blender_mcp\mcps\`
  - 工作区：`e:\pro\blender_mcp`（git 根）
- **目录约定**：`blender_assets/{scripts,scenes,export}`、`game/`（Unity 工程）、`tools/`（音效合成等脚本）、`docs/milestones/`（阶段证据）、`docs/superpowers/{specs,plans}`。
- **资产规范**：1 单位 = 1 m；命名 `SM_/SK_/M_/A_` 前缀；静态资产几百~几千面；主角 3-6k 面；FBX 导出 apply scale、Y-up（forward -Z, up Y）。
- **Blender MCP 纪律**：端口 9876；同一时间仅一个 MCP server 实例；执行脚本小步前进，每步用 `look` 截图验证；`execute_blender_code` 前先确认不会误删用户已有场景数据（先在空场景/新 scene 中操作）。
- **Unity MCP 纪律**：一切场景改动通过 MCP 工具或 `Assets/Editor/` 脚本（可复现）；每次改动后检查 Console 无报错。
- **调用 MCP 工具前**：必须先读对应 schema 文件（`mcps/<server>/tools/<tool>.json`），用 CallMcpTool 调用，不猜测参数。
- **版本注意**：Blender 5.2 的 FBX 导出 API 若与脚本中参数名不符（如算子改名），以实际 API 为准做等价调整，并在里程碑报告中记录。
- **工具名登记**：unityMCP 的准确工具名在 M0-4 完成后登记到 `docs/milestones/M0-tool-notes.md`，后续所有任务引用该文件中的名称。

---

## 文件结构总览（File Map）

| 文件 | 职责 | 产生于 |
|---|---|---|
| `C:\Users\windows\.qoder\mcp.json` | Qoder MCP 双 server 配置（blender + unityMCP） | M0-1 |
| `docs/milestones/M0-tool-notes.md` | 双端 MCP 工具名/schema 要点登记 | M0-4 |
| `docs/milestones/M<N>-report.md` | 各里程碑证据与结论 | 各阶段末 |
| `blender_assets/scripts/m1_test_pillar.py` | 破损石柱生成 + headless 自测 + FBX 导出 | M1-1 |
| `blender_assets/export/SM_Pillar_Broken.fbx` | M1 测试资产 | M1-1 |
| `game/Assets/Editor/GrayboxBuilder.cs` | 一键构建灰盒关卡（房间/机关位/玩家/光照/层与标签） | M2-1 |
| `game/Assets/Scripts/ThirdPersonController.cs` | 第三人称移动/跳跃/重力 | M2-2 |
| `game/Assets/Scripts/CameraFollow.cs` | 环绕第三人称相机 | M2-2 |
| `game/Assets/Scripts/ClimbSystem.cs` | 攀爬状态机 | M2-3 |
| `game/Assets/Scripts/PushBlock.cs` | 可推石块（轴约束物理） | M2-4 |
| `game/Assets/Scripts/PressurePlate.cs` | 压力板（重量触发） | M2-4 |
| `game/Assets/Scripts/StoneDoor.cs` | 石门升降 | M2-4 |
| `game/Assets/Scripts/GoalTrigger.cs` | 终点触发 | M2-5 |
| `game/Assets/Scripts/SimpleUI.cs` | 目标提示 + 完成面板（中文字体动态加载） | M2-5 |
| `game/Assets/Scripts/FireFlicker.cs` | 火光闪烁 | M5-3 |
| `game/Assets/Editor/AnimatorSetup.cs` | 生成 Animator Controller 并挂到玩家 | M4-5 |
| `game/Assets/Editor/M1PlaceTest.cs`（可选过渡） | 把 M1 石柱摆入测试场景 | M1-3 |
| `game/Assets/Editor/KitPlacer.cs` | 按坐标表用正式资产替换灰盒 | M3-3 |
| `blender_assets/scripts/temple_kit.py` | 古墓环境套件生成 + 材质 + 导出 | M3-1 |
| `blender_assets/scripts/build_hero.py` | 主角低模 + 骨架 + 权重 | M4-1/M4-2 |
| `blender_assets/scripts/hero_anims.py` | 五个动画 Action + NLA + 导出 | M4-3/M4-4 |
| `tools/audio_gen.py` | 音效合成（stdlib-only） | M5-1 |
| `tools/audio_check.py` | 音效自检（时长/峰值/RMS） | M5-1 |
| `game/Assets/Scenes/Demo.unity` | 主关卡场景 | M2-1 起持续使用 |

---

## 里程碑 M0：环境部署与连通

> 目标：Qoder 能同时调用 Blender MCP 与 Unity MCP 工具（读场景 + 截图）。
> 产出：`mcp.json`（双 server）、Blender 插件已装、Unity 工程已建、`M0-tool-notes.md`。
> 🚦 门禁：开工需用户指令；第 3 任务为用户操作，完成后必须等待用户回报；本里程碑结束停下汇报。

### Task M0-1: 写入 Qoder MCP 双 server 配置

**Files:**
- Modify: `C:\Users\windows\.qoder\mcp.json`（当前为 `{"mcpServers": {}}`）

**Interfaces:**
- Produces: 两个 MCP server 条目 `blender`（stdio，uvx 全路径 + 固定 Python 3.11）与 `unityMCP`（stdio，`mcpforunityserver` 包）；重启 Qoder 后生效。

- [ ] **Step 1: 备份并写入配置**

将 `mcp.json` 内容替换为（注意 JSON 中反斜杠需双写 `\\`）：

```json
{
  "mcpServers": {
    "blender": {
      "command": "C:\\Users\\windows\\AppData\\Local\\Microsoft\\WinGet\\Packages\\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\\uvx.exe",
      "args": ["--python", "3.11", "mcp-for-blender"],
      "env": { "UV_PYTHON_PREFERENCE": "only-managed" }
    },
    "unityMCP": {
      "command": "C:\\Users\\windows\\AppData\\Local\\Microsoft\\WinGet\\Packages\\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\\uvx.exe",
      "args": ["--from", "mcpforunityserver", "mcp-for-unity", "--transport", "stdio"]
    }
  }
}
```

- [ ] **Step 2: 校验 JSON 格式**

Run: `Get-Content "$env:USERPROFILE\.qoder\mcp.json" -Raw | ConvertFrom-Json; Write-Host OK`
Expected: 输出 `OK`，无解析错误。

- [ ] **Step 3: （不 commit——该文件在仓库外）在 M0 报告中记录配置摘要**

### Task M0-2: 安装 Blender MCP 插件（install-addon）

**Files:**
- None（写 Blender 用户配置目录）

**Interfaces:**
- Produces: Blender addons 目录下的 `blender_mcp.py`；命令输出中的 addons 路径要记录到 M0 报告。

- [ ] **Step 1: 运行安装命令**

Run:
```powershell
& "C:\Users\windows\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uvx.exe" --python 3.11 mcp-for-blender install-addon
```
Expected: 打印 "wrote to ..." 一类的 addons 目录路径（预期形如 `C:\Users\windows\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py`）。

- [ ] **Step 2: 若安装失败（未检测到 Blender，Steam 版常见）**

按以下顺序尝试，并在报告中记录用了哪种方式：
1. Run: `uvx mcp-for-blender addon-paths` 查看检测到的目录 → 若为空，手动确认 Blender 用户脚本目录 `C:\Users\windows\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\` 是否存在。
2. 下载插件的 `addon.py`（仓库：`https://github.com/ahujasid/blender-mcp`）放入上述 addons 目录并改名为 `blender_mcp.py`；或设 `BLENDERMCP_ADDONS_DIR` 环境变量后重跑 Step 1。
3. 兜底：让用户在 Blender 中 `Edit → Preferences → Add-ons → Install…` 选择下载的 addon.py。

- [ ] **Step 3: 验证文件存在**

Run: `Test-Path "C:\Users\windows\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py"`
Expected: `True`

### Task M0-3: 【用户操作】重启 Qoder、启动 Blender/Unity 服务、创建 Unity 工程

**Files:**
- Create: `e:\pro\blender_mcp\game\`（用户经 Unity Hub 创建）

**Interfaces:**
- Produces: 运行中的 Blender（MCP server 已启动，端口 9876）、运行中的 Unity（unity-mcp 桥接已连接）。

- [ ] **Step 1: 输出用户操作清单（逐条给出，等用户回报"已就绪"）**

1. **重启 Qoder**：从系统托盘完全退出后重新打开（MCP 工具在重启后才会加载；会话历史会保留）。
2. **Blender**：打开后 `Edit → Preferences → Add-ons` → 搜索并启用 **Interface: MCP for Blender** → 3D 视图按 `N` → 打开 **MCP for Blender** 面板 → 点击 **Start MCP Server**（状态显示 Running/Connected，默认端口 9876）。
3. **Unity 工程**：Unity Hub → New project → 编辑器选 **6000.3.21f1** → 模板选 **Universal 3D** → 位置 `e:\pro\blender_mcp`、名称 `game` → 创建并打开。
4. **安装 unity-mcp 包**：Unity 内 `Window → Package Manager` → `+` → Add package from git URL → 粘贴：
   `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main`
5. **连接**：等待 MCP for Unity 设置向导出现（确认 Python/uv 状态为绿色 → Done；Qoder 不在自动配置列表里，跳过 Configure Selected）→ `Window → MCP for Unity` 确认状态面板为 Connected/Running。
6. 回到 Qoder 告诉我："已就绪"。

- [ ] **Step 2: 等待用户回报**（收到"已就绪"前，不得执行后续任务；若用户遇到问题，按 Troubleshooting 排查：Unity Bridge 未连接 → 重启 Unity；Python/uv 报错 → 确认 `uv --version` 正常）

### Task M0-4: 双端连通验证 + 工具名登记

**Files:**
- Create: `docs/milestones/M0-tool-notes.md`

**Interfaces:**
- Produces: `M0-tool-notes.md`——记录 blender 与 unityMCP 两侧**实际可用的工具名清单**及关键 schema 要点（后续任务按此引用）。

- [ ] **Step 1: 确认 MCP 已加载**

Run: `Get-ChildItem "C:\Users\windows\AppData\Roaming\Qoder\SharedClientCache\projects\e--pro-blender_mcp\mcps" | Select-Object Name`
Expected: 出现 `blender`、`unityMCP` 两个目录（各含 `tools/*.json`）。若缺失 → 重启 Qoder 或检查 mcp.json；仍失败 → 读 Qoder MCP 日志排查 uvx 启动错误。

- [ ] **Step 2: 读取 blender 侧工具 schema 并逐个验证**

1. Read `mcps/blender/tools/*.json`（重点：`get_addon_status`、`get_scene_info`、`look`、`execute_blender_code`）。
2. CallMcpTool `get_addon_status` → 期望返回 Blender 版本 5.2 + 插件版本（**这一步验证 5.2 兼容性**；若报错/版本拒绝 → 记录问题，暂停并汇报用户，评估切换 Blender 4.5 LTS 方案）。
3. CallMcpTool `get_scene_info` → 期望返回默认场景对象列表。
4. CallMcpTool `look`（默认视角截图）→ 期望返回图像（能"看到"Blender 默认场景，含立方体）。

- [ ] **Step 3: 读取 unityMCP 侧工具 schema 并逐个验证**

1. Read `mcps/unityMCP/tools/*.json`，把所有工具名记入 notes（预期包含：场景/对象管理、脚本读写、Console 读取、Game 视图截图一类工具）。
2. CallMcpTool 读取当前场景信息 → 期望返回 `Demo` 场景（新工程默认 SampleScene 亦可）。
3. CallMcpTool 读取 Console 日志 → 期望无 Error。
4. CallMcpTool Game 视图截图 → 期望返回图像（新工程默认可视内容）。
5. 若 stdio 连接失败：改试 HTTP 方式——在 `mcp.json` 将 unityMCP 改为 `{"url": "http://localhost:8080/mcp"}`（若 Qoder 不支持 url 型条目则记录并汇报），同时 Unity 侧 `Window → MCP for Unity` 切换 transport 到 HTTP。

- [ ] **Step 4: 写 `docs/milestones/M0-tool-notes.md`**

内容：两边可用工具名全表 + 关键参数要点 + 验证结果（截图/返回摘要）+ 遗留问题。之后 commit。

- [ ] **Step 5: Commit**

```bash
git add docs/milestones/M0-tool-notes.md
git commit -m "docs(M0): MCP 双端连通验证完成，登记工具清单"
```

### Task M0-5: M0 里程碑汇报（停下等确认）

- [ ] **Step 1: 向用户汇报**：双端连通状态、截图证据、（如有）兼容性告警与处置、M0 待办是否全部完成。
- [ ] **Step 2: 等待用户确认后再进入 M1。**（用户未确认前不得开始 M1 任何任务）

---

## 里程碑 M1：最小链路验证（石柱）

> 目标：Blender 生成一根破损石柱 → MCP 截图 → 导出 FBX → Unity 导入摆放 → 双端截图验收。
> 产出：`m1_test_pillar.py`、`SM_Pillar_Broken.fbx`、`docs/milestones/M1/` 截图。
> 🚦 门禁：开工需用户指令；结束停下汇报。

### Task M1-1: 石柱生成脚本 + headless 自测 + FBX 导出

**Files:**
- Create: `blender_assets/scripts/m1_test_pillar.py`
- Create（运行产物）: `blender_assets/export/SM_Pillar_Broken.fbx`、`blender_assets/scenes/M1_pillar.blend`

**Interfaces:**
- Produces: `SM_Pillar_Broken`（8 边圆柱、半径 0.4m、高 ~2.5-3.0m、顶部随机破损、平直着色、材质 `M_Stone`）；供 M1-3 导入 Unity；其"顶部破损顶点随机下沉+径向抖动"手法在 M3 石柱资产中复用。

- [ ] **Step 1: 写脚本（完整内容如下）**

```python
"""M1: 生成破损石柱 SM_Pillar_Broken 并导出 FBX。
headless 用法: blender.exe --background --factory-startup --python m1_test_pillar.py"""
import bpy, bmesh, random, os

random.seed(42)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # blender_assets/
OUT_FBX = os.path.join(ROOT, "export", "SM_Pillar_Broken.fbx")
OUT_BLEND = os.path.join(ROOT, "scenes", "M1_pillar.blend")

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

def main():
    obj = build_pillar()
    add_stone_material(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    assert 40 <= tris <= 500, f"面数异常: {tris}"
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

main()
```

- [ ] **Step 2: headless 自测（跑两次，验证结果确定性）**

Run:
```powershell
& "E:\SteamLibrary\steamapps\common\Blender\blender.exe" --background --factory-startup --python "e:\pro\blender_mcp\blender_assets\scripts\m1_test_pillar.py"
```
Expected: 输出 `OK verts=... tris=... fbx=...B`，且 `Test-Path "e:\pro\blender_mcp\blender_assets\export\SM_Pillar_Broken.fbx"` 为 True。
（若 Blender 5.2 报 `export_scene.fbx` 参数/算子不存在：按等价语义调整导出调用并在报告中记录；断言逻辑不变。）

- [ ] **Step 3: 生成验收截图素材（headless 渲染一张）**

Run: 在脚本末尾追加渲染段或用 `--python-expr` 执行：设置相机看向石柱、`bpy.context.scene.render.engine='BLENDER_EEVEE_NEXT'`（若 5.2 名称不同取等效）、输出 `docs/milestones/M1/pillar_blender.png`（800x600）。
Expected: PNG 文件存在且 >20KB（内容由 M1-2 的 MCP 截图交叉验证）。

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/m1_test_pillar.py
git commit -m "feat(M1): 破损石柱生成脚本与 headless 自测"
```
（`blender_assets/export/`、`blender_assets/scenes/` 的运行产物在 M1-4 一并提交）

### Task M1-2: 通过 Blender MCP 在实时会话执行 + 截图

**Files:**
- 运行产物: `docs/milestones/M1/pillar_blender.png`（MCP 截图版本，可与 Step 3 渲染图并存）

**Interfaces:**
- Consumes: M0-4 登记的工具名；`m1_test_pillar.py` 的建模函数。
- Produces: 用户可见的 Blender 侧成果截图；验证"脚本在实时 Blender（5.2）中同样可执行"。

- [ ] **Step 1: 在 Blender 新建空场景后执行模型代码**

CallMcpTool `execute_blender_code`：先 `bpy.ops.wm.read_factory_settings(use_empty=True)`（在用户许可下新建空场景，不动用户原数据），再粘贴执行 `m1_test_pillar.py` 中 `build_pillar()` + `add_stone_material()` 两函数及其调用（不含导出段落）。
Expected: 返回成功；再 `get_scene_info` 能看到 `SM_Pillar_Broken`。

- [ ] **Step 2: 多角度截图自查**

CallMcpTool `look`（auto-framed 视图）→ 检查：形状是断裂石柱、比例合理、无明显破面。
Expected: 图像正确；如有问题修改脚本参数后重复。
将返回图像存为 `docs/milestones/M1/pillar_blender.png`（若 `look` 支持保存路径参数则直接指定；否则将返回的 base64/临时文件转存归档）。

- [ ] **Step 3: 导出 FBX（实时会话内）**

CallMcpTool `execute_blender_code`：执行与脚本一致的导出段（`bpy.ops.export_scene.fbx(...)` 到 `blender_assets/export/SM_Pillar_Broken.fbx`）。
Expected: MCP 返回成功；PowerShell 验证文件存在且大小 >5KB。

### Task M1-3: Unity 导入与摆放 + 截图

**Files:**
- 复制: `blender_assets/export/SM_Pillar_Broken.fbx` → `game/Assets/Art/Static/SM_Pillar_Broken.fbx`
- Create（如需要）: `game/Assets/Editor/M1PlaceTest.cs`

**Interfaces:**
- Consumes: FBX 文件；unityMCP 工具（名称以 `M0-tool-notes.md` 为准）。
- Produces: Unity 场景中一个比例正确的石柱实例（供用户确认"链路通"）；导入参数经验（缩放/朝向）记录进报告，供 M3 复用。

- [ ] **Step 1: 复制资产并让 Unity 导入**

Run: `Copy-Item "e:\pro\blender_mcp\blender_assets\export\SM_Pillar_Broken.fbx" "e:\pro\blender_mcp\game\Assets\Art\Static\SM_Pillar_Broken.fbx" -Force`（目录不存在先建）
（也可靠 MCP 的资产导入工具完成；两者取其一，记录所用方式。）
Expected: Unity 自动导入；用 unityMCP 读取 Console 无 Error。

- [ ] **Step 2: 在场景中摆放**

优先：CallMcpTool（unityMCP 对象创建/实例化工具）在当前场景 (0, 0, 0) 实例化该模型。
兜底：写 `M1PlaceTest.cs`（`[MenuItem("Demo/M1 放置石柱")]`：`PrefabUtility.InstantiatePrefab` 或 `Object.Instantiate` 加载 `Assets/Art/Static/SM_Pillar_Broken.fbx`），再通过 MCP 触发菜单/或让用户点菜单。
Expected: Hierarchy 出现 `SM_Pillar_Broken`，位置 (0,0,0)。

- [ ] **Step 3: 截图验证比例与朝向**

CallMcpTool（unityMCP Game 视图截图；先把相机对准石柱，可用工具调整 Scene/Game 相机或临时创建相机）。
Expected: 石柱出现在画面中、高约 2.5-3 个"米"比例正常（对照默认 Cube 1m）。存图 `docs/milestones/M1/pillar_unity.png`。
若缩放/轴向异常（如压扁、倒置）：调整 FBX 导入参数（Scale Factor/Use File Scale）并重验，记录结论。

- [ ] **Step 4: 清理测试摆放**（删除测试实例或保留于临时测试对象下，不污染后续 Demo 场景；在报告中说明）。**注意：M2 将另用 `Demo.unity` 场景，本步骤的测试摆放不影响它。**

### Task M1-4: M1 汇报与提交

- [ ] **Step 1: 写 `docs/milestones/M1/report.md`**：双端截图路径、FBX 大小/面数、导入参数结论、遗留问题。
- [ ] **Step 2: Commit**

```bash
git add blender_assets/export blender_assets/scenes docs/milestones/M1
git commit -m "feat(M1): 石柱链路验证通过（Blender 生成→FBX→Unity 导入）"
```

- [ ] **Step 3: 汇报用户并停下**：给用户看双端截图（路径 + 图片），等确认后才进入 M2。

---

## 里程碑 M2：灰盒玩法（2 房间 + 控制器 + 攀爬 + 机关 + 终点）

> 目标：在 Unity 用 primitives 搭建完整可玩灰盒，验证全部玩法逻辑（不依赖 Blender 资产）。
> 产出：`Demo.unity` 灰盒场景、8 个 C# 脚本、`docs/milestones/M2/` 截图与试玩清单。
> 🚦 门禁：开工需用户指令；M2-6 须用户实机试玩验收；结束停下汇报。

**关卡坐标表（LevelSpec 常量，单位米，+X 东 / +Z 北 / Y 上）——后续所有任务共享此表：**

| 元素 | 坐标 / 尺寸 |
|---|---|
| Room A 主厅 | 地板 x∈[-10,10], z∈[-8,8]；墙高 6 |
| Room B 出口厅 | 地板 x∈[-8,8], z∈[8,22]；墙高 6 |
| 共用墙（门洞） | z=8；门洞宽 3（x∈[-1.5,1.5]）、高 4 |
| 石门 StoneDoor | (0, 2, 8)，尺寸 3×4×0.4，关闭态封门洞，升起 4.3m |
| 玩家出生点 | (0, 0.2, -6)，朝 +Z |
| 压力板 PressurePlate | (4, 0.05, -2)，1.2×0.1×1.2 |
| 推石块 PushBlock | (-2, 0.5, -2)，1×1×1（推向 +X 压板，距离 6m） |
| 攀爬石台 ClimbableLedge | 中心 (0, 1.5, 18)，6×3×4（顶面 y=3，南面为可攀面，Layer=Climbable） |
| 祭坛 Altar | (0, 0.5, 21)，2×1×1 |
| 宝物 Treasure | (0, 1.4, 21)，0.4³ + SphereCollider(trigger, r=1.5) |

**依赖关系（机关联动）：** PushBlock 被推上 PressurePlate → StoneDoor.Open()；离开则 Close()。触碰 Treasure → SimpleUI.ShowComplete()。

### Task M2-1: 关卡常量 + 灰盒构建器 + 场景生成

**Files:**
- Create: `game/Assets/Scripts/Level/LevelSpec.cs`
- Create: `game/Assets/Editor/GrayboxBuilder.cs`

**Interfaces:**
- Produces: `LevelSpec` 静态常量（上表全部坐标，`public static readonly Vector3/float`）；`GrayboxBuilder.Build()` 静态方法 + 菜单 `Demo/构建灰盒关卡`；生成场景 `Assets/Scenes/Demo.unity`（含 Layers `Climbable`、Tags `Pushable`）；后续 M3 KitPlacer 复用 LevelSpec 与菜单模式。

- [ ] **Step 1: 写 `LevelSpec.cs`（完整内容）**

```csharp
using UnityEngine;

public static class LevelSpec
{
    public const float WallH = 6f, WallT = 0.5f, DoorWidth = 3f, DoorHeight = 4f;
    public static readonly Vector3 PlayerSpawn = new Vector3(0, 0.2f, -6);
    public static readonly Vector3 DoorPos = new Vector3(0, DoorHeight / 2f, 8);
    public static readonly Vector3 PlatePos = new Vector3(4, 0.05f, -2);
    public static readonly Vector3 BlockPos = new Vector3(-2, 0.5f, -2);
    public static readonly Vector3 LedgeCenter = new Vector3(0, 1.5f, 18);
    public static readonly Vector3 LedgeSize = new Vector3(6, 3, 4);
    public static readonly Vector3 AltarPos = new Vector3(0, 0.5f, 21);
    public static readonly Vector3 TreasurePos = new Vector3(0, 1.4f, 21);
    public const string LayerClimbable = "Climbable";
    public const string TagPushable = "Pushable";
}
```

- [ ] **Step 2: 写 `GrayboxBuilder.cs`（完整逻辑如下，含层/标签幂等创建）**

```csharp
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class GrayboxBuilder
{
    [MenuItem("Demo/构建灰盒关卡")]
    public static void Build()
    {
        EnsureLayer(LevelSpec.LayerClimbable);
        EnsureTag(LevelSpec.TagPushable);
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // 地板
        Box("FloorA", new Vector3(0, -0.25f, 0), new Vector3(20, 0.5f, 16));
        Box("FloorB", new Vector3(0, -0.25f, 15), new Vector3(16, 0.5f, 14));
        // Room A 外墙
        Box("WallA_S", new Vector3(0, WallH2(), -8), new Vector3(20, L2(), 0.5f));
        Box("WallA_E", new Vector3(10, L2(), 0), new Vector3(0.5f, L2(), 16));
        Box("WallA_W", new Vector3(-10, L2(), 0), new Vector3(0.5f, L2(), 16));
        // 共用墙 + 门洞（左右两段 + 门楣）
        Box("WallAB_L", new Vector3(-5.75f, L2(), 8), new Vector3(8.5f, L2(), 0.5f));
        Box("WallAB_R", new Vector3(5.75f, L2(), 8), new Vector3(8.5f, L2(), 0.5f));
        Box("WallAB_Top", new Vector3(0, 5f, 8), new Vector3(3f, 2f, 0.5f));
        // Room B 外墙
        Box("WallB_E", new Vector3(8, L2(), 15), new Vector3(0.5f, L2(), 14));
        Box("WallB_W", new Vector3(-8, L2(), 15), new Vector3(0.5f, L2(), 14));
        Box("WallB_N", new Vector3(0, L2(), 22), new Vector3(16, L2(), 0.5f));

        // 石门
        var door = Box("StoneDoor", LevelSpec.DoorPos, new Vector3(3f, 4f, 0.4f));
        door.AddComponent<StoneDoor>();

        // 攀爬石台
        var ledge = Box("ClimbableLedge", LevelSpec.LedgeCenter, LevelSpec.LedgeSize);
        ledge.layer = LayerMask.NameToLayer(LevelSpec.LayerClimbable);

        // 压力板 + 推石块
        var plate = Box("PressurePlate", LevelSpec.PlatePos, new Vector3(1.2f, 0.1f, 1.2f));
        var plateComp = plate.AddComponent<PressurePlate>();
        plateComp.door = door.GetComponent<StoneDoor>();

        var block = Box("PushBlock", LevelSpec.BlockPos, Vector3.one);
        block.tag = LevelSpec.TagPushable;
        var rb = block.AddComponent<Rigidbody>();
        rb.mass = 50f;
        rb.constraints = RigidbodyConstraints.FreezeRotation | RigidbodyConstraints.FreezePositionY;
        block.AddComponent<PushBlock>();

        // 祭坛 + 宝物 + 终点触发
        Box("Altar", LevelSpec.AltarPos, new Vector3(2, 1, 1));
        var treasure = Box("Treasure", LevelSpec.TreasurePos, Vector3.one * 0.4f);
        var sc = treasure.AddComponent<SphereCollider>(); sc.isTrigger = true; sc.radius = 3.75f; // 世界半径≈1.5（父缩放 0.4）
        treasure.AddComponent<GoalTrigger>();

        // 玩家（胶囊视觉 + CharacterController + 控制器/攀爬/推挤 + 相机）
        var player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "Player"; player.tag = "Player";
        player.transform.position = LevelSpec.PlayerSpawn;
        Object.DestroyImmediate(player.GetComponent<CapsuleCollider>());
        var cc = player.AddComponent<CharacterController>();
        cc.height = 1.8f; cc.radius = 0.3f; cc.center = new Vector3(0, 0.9f, 0);
        player.AddComponent<ThirdPersonController>();
        var climb = player.AddComponent<ClimbSystem>();
        climb.climbableMask = 1 << LayerMask.NameToLayer(LevelSpec.LayerClimbable);

        var camGo = new GameObject("MainCamera");
        var cam = camGo.AddComponent<Camera>(); camGo.tag = "MainCamera";
        var follow = camGo.AddComponent<CameraFollow>();
        follow.target = player.transform;
        player.GetComponent<ThirdPersonController>().cameraPivot = camGo.transform;

        new GameObject("UI").AddComponent<SimpleUI>();

        // 光照占位（暗环境 + 暖色点光）
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.08f, 0.08f, 0.12f);
        var sun = new GameObject("Sun").AddComponent<Light>();
        sun.type = LightType.Directional; sun.intensity = 0.3f; sun.transform.rotation = Quaternion.Euler(60, -30, 0);
        MakePointLight("TorchA_L", new Vector3(-3, 2.5f, -6), new Color(1f, 0.6f, 0.3f), 6f);
        MakePointLight("TorchA_R", new Vector3(3, 2.5f, -6), new Color(1f, 0.6f, 0.3f), 6f);

        System.IO.Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene, "Assets/Scenes/Demo.unity");
        Debug.Log("[GrayboxBuilder] Demo.unity 构建完成");
    }

    static float WallH2() => LevelSpec.WallH / 2f;
    static float L2() => LevelSpec.WallH;

    static GameObject Box(string name, Vector3 center, Vector3 size)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name; go.transform.position = center; go.transform.localScale = size;
        return go;
    }

    static void MakePointLight(string name, Vector3 pos, Color c, float range)
    {
        var go = new GameObject(name);
        var lt = go.AddComponent<Light>();
        lt.type = LightType.Point; lt.color = c; lt.range = range; lt.intensity = 1.5f;
        go.transform.position = pos;
    }

    static void EnsureLayer(string name)
    {
        if (LayerMask.NameToLayer(name) != -1) return;
        var so = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        var layers = so.FindProperty("layers");
        for (int i = 8; i < layers.arraySize; i++)
            if (string.IsNullOrEmpty(layers.GetArrayElementAtIndex(i).stringValue))
            { layers.GetArrayElementAtIndex(i).stringValue = name; so.ApplyModifiedProperties(); return; }
    }

    static void EnsureTag(string name)
    {
        var so = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        var tags = so.FindProperty("tags");
        for (int i = 0; i < tags.arraySize; i++) if (tags.GetArrayElementAtIndex(i).stringValue == name) return;
        tags.InsertArrayElementAtIndex(tags.arraySize);
        tags.GetArrayElementAtIndex(tags.arraySize - 1).stringValue = name;
        so.ApplyModifiedProperties();
    }
}
```

- [ ] **Step 3: 检查输入系统配置（决定 M2-2 代码路径）**

Run: `Select-String -Path "e:\pro\blender_mcp\game\ProjectSettings\ProjectSettings.asset" -Pattern "activeInputHandler"`
- 值 `0`（旧）或 `2`（Both）→ 无需处理，后续脚本用经典 `Input.GetAxis` API。
- 值 `1`（仅新系统）→ 用编辑器脚本把 `activeInputHandler` 改为 `2`（同 `EnsureLayer` 的 SerializedObject 手法操作 `ProjectSettings/ProjectSettings.asset`），然后提示用户重启 Unity 生效。把结论记入 M2 报告。

- [ ] **Step 4: 触发构建并验证**

先写全部 M2 脚本（M2-2～M2-5）让工程编译通过，再触发 `Build()`：
- 优先：用 unityMCP 工具触发菜单项 `Demo/构建灰盒关卡`（工具名以 M0-tool-notes 为准；若有"执行菜单/执行编辑器操作"类工具）。
- 兜底 1：让用户在 Unity 顶部菜单点击 `Demo → 构建灰盒关卡`。
- 兜底 2：关闭 Unity 后用 CLI：`& "D:\Unity\Hub\Editor\6000.3.21f1\Editor\Unity.exe" -batchmode -projectPath "e:\pro\blender_mcp\game" -executeMethod GrayboxBuilder.Build -quit -logFile -`（注意：编辑器打开时不可用此方式）。

Expected: Console 打印 `[GrayboxBuilder] Demo.unity 构建完成`，无编译错误；Hierarchy 含全部清单对象。
CallMcpTool（unityMCP 截图）→ 存 `docs/milestones/M2/graybox_roomA.png`。

- [ ] **Step 5: Commit**

```bash
git add game/Assets/Scripts/Level/LevelSpec.cs game/Assets/Editor/GrayboxBuilder.cs
git commit -m "feat(M2): 灰盒关卡构建器与关卡常量表"
```

### Task M2-2: 第三人称控制器 + 相机

**Files:**
- Create: `game/Assets/Scripts/ThirdPersonController.cs`
- Create: `game/Assets/Scripts/CameraFollow.cs`

**Interfaces:**
- Consumes: `ClimbSystem.IsClimbing`（M2-3 提供，本任务先按接口引用，M2-3 落地；若编译顺序问题，先加最小 stub 并在 M2-3 替换为完整实现）。
- Produces: `ThirdPersonController.cameraPivot`（public，CameraFollow 的相机 transform）；`OnControllerColliderHit` → 调用 `PushBlock.Push(Vector3)`（M2-4 接口）。

- [ ] **Step 1: 写 `ThirdPersonController.cs`（完整内容）**

```csharp
using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class ThirdPersonController : MonoBehaviour
{
    public float moveSpeed = 4f, runSpeed = 6f, turnLerp = 12f, gravity = -20f, jumpHeight = 1.2f;
    public Transform cameraPivot;

    CharacterController cc;
    float velocityY;
    ClimbSystem climb;

    void Awake() { cc = GetComponent<CharacterController>(); climb = GetComponent<ClimbSystem>(); }

    void Update()
    {
        if (climb && climb.IsClimbing) { velocityY = 0f; return; }   // 攀爬期间交出控制权
        bool grounded = cc.isGrounded;
        if (grounded && velocityY < 0f) velocityY = -2f;

        float h = Input.GetAxisRaw("Horizontal"), v = Input.GetAxisRaw("Vertical");
        float yaw = cameraPivot ? cameraPivot.eulerAngles.y : 0f;
        Vector3 dir = Quaternion.Euler(0, yaw, 0) * new Vector3(h, 0, v);
        if (dir.sqrMagnitude > 1f) dir.Normalize();

        if (dir.sqrMagnitude > 0.01f)
        {
            var look = Quaternion.LookRotation(dir);
            transform.rotation = Quaternion.Slerp(transform.rotation, look, turnLerp * Time.deltaTime);
        }
        if (grounded && Input.GetButtonDown("Jump")) velocityY = Mathf.Sqrt(jumpHeight * -2f * gravity);
        velocityY += gravity * Time.deltaTime;

        float speed = Input.GetKey(KeyCode.LeftShift) ? runSpeed : moveSpeed;
        Vector3 move = dir * speed; move.y = velocityY;
        cc.Move(move * Time.deltaTime);
    }

    void OnControllerColliderHit(ControllerColliderHit hit)
    {
        if (!hit.rigidbody) return;
        var pb = hit.rigidbody.GetComponent<PushBlock>();
        if (pb) pb.Push(hit.moveDirection);
    }
}
```

- [ ] **Step 2: 写 `CameraFollow.cs`（完整内容）**

```csharp
using UnityEngine;

public class CameraFollow : MonoBehaviour
{
    public Transform target;
    public float distance = 5f, height = 1.6f, mouseSens = 3f, minPitch = -20f, maxPitch = 60f;
    public float posLerp = 10f, collisionRadius = 0.25f;

    float yaw, pitch = 15f;

    void Start()
    {
        if (target) yaw = target.eulerAngles.y;
        Cursor.lockState = CursorLockMode.Locked;   // 编辑器内点击画面进入锁定，Esc 解锁
    }

    void LateUpdate()
    {
        if (!target) return;
        yaw += Input.GetAxis("Mouse X") * mouseSens;
        pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * mouseSens, minPitch, maxPitch);

        Vector3 pivot = target.position + Vector3.up * height;
        Quaternion rot = Quaternion.Euler(pitch, yaw, 0);
        Vector3 desired = pivot - rot * Vector3.forward * distance;

        Vector3 dir = (desired - pivot).normalized;
        if (Physics.SphereCast(pivot, collisionRadius, dir, out var hit, distance, ~0, QueryTriggerInteraction.Ignore))
            desired = pivot + dir * Mathf.Max(0.3f, hit.distance - 0.1f);

        transform.position = Vector3.Lerp(transform.position, desired, posLerp * Time.deltaTime);
        transform.rotation = Quaternion.LookRotation(pivot - transform.position);
    }
}
```

- [ ] **Step 3: 编译并验证**

触发 Unity 刷新编译（保存文件即自动编译；用 unityMCP 读 Console 确认 0 errors；若有编译错则修复）。
Expected: 无编译错误；用户可选在编辑器 Play 手动移动验证（正式验收在 M2-6）。

- [ ] **Step 4: Commit**

```bash
git add game/Assets/Scripts/ThirdPersonController.cs game/Assets/Scripts/CameraFollow.cs
git commit -m "feat(M2): 第三人称控制器与环绕相机"
```

### Task M2-3: 攀爬系统

**Files:**
- Create: `game/Assets/Scripts/ClimbSystem.cs`

**Interfaces:**
- Consumes: `LevelSpec.LayerClimbable`（M2-1）；`CharacterController`。
- Produces: `ClimbSystem.IsClimbing`（public bool，M2-2 已引用）；`climbableMask` 由构建器赋值。

- [ ] **Step 1: 写 `ClimbSystem.cs`（完整内容）**

```csharp
using UnityEngine;

public class ClimbSystem : MonoBehaviour
{
    public LayerMask climbableMask;
    public float checkDist = 0.65f, climbSpeed = 1.5f, topOutDuration = 0.4f, topOutForward = 0.7f;

    public bool IsClimbing { get; private set; }

    CharacterController cc;
    bool toppingOut; float topOutT;
    Vector3 topStart, topEnd;

    void Awake() { cc = GetComponent<CharacterController>(); }

    void Update()
    {
        if (IsClimbing) { TickClimb(); return; }
        if (!cc.isGrounded) return;
        float v = Input.GetAxisRaw("Vertical"), h = Input.GetAxisRaw("Horizontal");
        if (v <= 0.1f || Mathf.Abs(h) > 0.5f) return;                    // 须朝向墙前进
        Vector3 origin = transform.position + Vector3.up * 1.1f;
        if (Physics.Raycast(origin, transform.forward, out var hit, checkDist, climbableMask))
            BeginClimb(hit.normal);
    }

    void BeginClimb(Vector3 wallNormal)
    {
        IsClimbing = true;
        transform.rotation = Quaternion.LookRotation(-wallNormal, Vector3.up);
    }

    void TickClimb()
    {
        if (toppingOut)
        {
            topOutT += Time.deltaTime / topOutDuration;
            cc.Move(Vector3.Lerp(topStart, topEnd, Mathf.Clamp01(topOutT)) - transform.position);
            if (topOutT >= 1f) { toppingOut = false; IsClimbing = false; }
            return;
        }
        float v = Input.GetAxisRaw("Vertical");
        if (v < -0.1f) { IsClimbing = false; return; }                   // 按 S 松手
        bool wallAhead = Physics.Raycast(transform.position + Vector3.up * 2.0f,
            transform.forward, out _, checkDist, climbableMask);
        if (!wallAhead)                                                   // 到顶 → 翻上去
        {
            toppingOut = true; topOutT = 0f;
            topStart = transform.position;
            topEnd = transform.position + Vector3.up * 0.9f + transform.forward * topOutForward;
            return;
        }
        cc.Move(Vector3.up * (climbSpeed * Time.deltaTime) - transform.forward * 0.5f * Time.deltaTime);
    }
}
```

- [ ] **Step 2: 编译验证 + 逻辑自检**

Console 0 errors。逻辑自检清单（对照代码确认）：①贴墙前推才触发 ②攀爬中重力由控制器跳过 ③到顶翻越后 `IsClimbing=false` ④按 S 可脱离。
Expected: 全部符合。实机验收并入 M2-6。

- [ ] **Step 3: Commit**

```bash
git add game/Assets/Scripts/ClimbSystem.cs
git commit -m "feat(M2): 攀爬状态机（贴墙检测→上爬→到顶翻越→放手脱离）"
```

### Task M2-4: 机关三件套（推石块 / 压力板 / 石门）

**Files:**
- Create: `game/Assets/Scripts/PushBlock.cs`
- Create: `game/Assets/Scripts/PressurePlate.cs`
- Create: `game/Assets/Scripts/StoneDoor.cs`

**Interfaces:**
- Produces: `PushBlock.Push(Vector3 pushDirWorld)`（被控制器调用）；`PressurePlate.door`（public，构建器已接线）；`StoneDoor.Open()/Close()`。

- [ ] **Step 1: 写三个脚本（完整内容）**

`PushBlock.cs`：
```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class PushBlock : MonoBehaviour
{
    public float maxPushSpeed = 1.2f;

    Rigidbody rb;
    void Awake() { rb = GetComponent<Rigidbody>(); }

    // 由玩家控制器 OnControllerColliderHit 调用；把推力约束到 X/Z 主导轴，避免斜推乱飘
    public void Push(Vector3 pushDirWorld)
    {
        Vector3 p = pushDirWorld; p.y = 0f;
        if (p.sqrMagnitude < 1e-4f) return;
        if (Mathf.Abs(p.x) < Mathf.Abs(p.z)) p = new Vector3(0, 0, Mathf.Sign(p.z));
        else p = new Vector3(Mathf.Sign(p.x), 0, 0);
        Vector3 v = rb.linearVelocity;                      // Unity 6 API
        rb.linearVelocity = new Vector3(p.x * maxPushSpeed, v.y, p.z * maxPushSpeed);
    }
}
```

`PressurePlate.cs`：
```csharp
using UnityEngine;

[RequireComponent(typeof(BoxCollider))]
public class PressurePlate : MonoBehaviour
{
    public StoneDoor door;
    public float pressDepth = 0.08f;

    int occupants;
    Vector3 initialPos;

    void Awake()
    {
        initialPos = transform.position;
        GetComponent<BoxCollider>().isTrigger = true;
    }

    bool IsPresser(Collider c) => c.CompareTag(LevelSpec.TagPushable) || c.CompareTag("Player");

    void OnTriggerEnter(Collider other)
    {
        if (!IsPresser(other)) return;
        occupants++;
        if (occupants == 1 && door) door.Open();
    }

    void OnTriggerExit(Collider other)
    {
        if (!IsPresser(other)) return;
        occupants = Mathf.Max(0, occupants - 1);
        if (occupants == 0 && door) door.Close();
    }

    void Update()
    {
        Vector3 target = initialPos + (occupants > 0 ? Vector3.down * pressDepth : Vector3.zero);
        transform.position = Vector3.Lerp(transform.position, target, 10f * Time.deltaTime);
    }
}
```

`StoneDoor.cs`：
```csharp
using UnityEngine;

public class StoneDoor : MonoBehaviour
{
    public float raiseHeight = 4.3f, duration = 2f;

    Vector3 closedPos; bool open; float t;

    void Awake() { closedPos = transform.position; }

    public void Open()
    {
        if (!open && SimpleUI.Instance) SimpleUI.Instance.SetObjective("石门已开——攀上高台，取得圣物！");
        open = true;
    }
    public void Close() { open = false; }

    void Update()
    {
        t = Mathf.MoveTowards(t, open ? 1f : 0f, Time.deltaTime / duration);
        transform.position = closedPos + Vector3.up * (raiseHeight * Mathf.SmoothStep(0f, 1f, t));
    }
}
```

- [ ] **Step 2: 编译验证**

Console 0 errors；检查 `rb.linearVelocity`（Unity 6 API）无弃用警告。
Expected: 通过。

- [ ] **Step 3: Commit**

```bash
git add game/Assets/Scripts/PushBlock.cs game/Assets/Scripts/PressurePlate.cs game/Assets/Scripts/StoneDoor.cs
git commit -m "feat(M2): 推石块/压力板/石门机关三件套"
```

### Task M2-5: 终点触发 + 简易 UI（中文字体）

**Files:**
- Create: `game/Assets/Scripts/GoalTrigger.cs`
- Create: `game/Assets/Scripts/SimpleUI.cs`

**Interfaces:**
- Consumes: `LevelSpec.TreasurePos`（构建器摆位）。
- Produces: `SimpleUI.Instance`、`SetObjective(string)`、`ShowComplete()`（StoneDoor 已调用 SetObjective）。

- [ ] **Step 1: 写 `GoalTrigger.cs`（完整内容）**

```csharp
using UnityEngine;

public class GoalTrigger : MonoBehaviour
{
    bool done;

    void OnTriggerEnter(Collider other)
    {
        if (done || !other.CompareTag("Player")) return;
        done = true;
        if (SimpleUI.Instance) SimpleUI.Instance.ShowComplete();
    }
}
```

- [ ] **Step 2: 写 `SimpleUI.cs`（完整内容，动态加载系统中文字体避免 TMP 字体图集流程）**

```csharp
using UnityEngine;
using UnityEngine.UI;

public class SimpleUI : MonoBehaviour
{
    public static SimpleUI Instance;

    Text objective, complete;
    Font font;

    void Awake()
    {
        Instance = this;
        font = Font.CreateDynamicFontFromOSFont("Microsoft YaHei", 24);
        if (!font) font = Font.CreateDynamicFontFromOSFont(new[] { "SimHei", "Arial" }, 24);

        var canvasGo = new GameObject("HUD", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        var canvas = canvasGo.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;

        objective = MakeText(canvasGo.transform, new Vector2(24, -24), TextAnchor.UpperLeft, "找到并开启石门", 24);
        complete = MakeText(canvasGo.transform, Vector2.zero, TextAnchor.MiddleCenter, "探索完成！\n你取得了圣物", 48);
        var rt = complete.rectTransform;
        rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
        rt.pivot = new Vector2(0.5f, 0.5f);
        rt.anchoredPosition = Vector2.zero;
        rt.sizeDelta = new Vector2(900, 300);
        complete.gameObject.SetActive(false);
    }

    Text MakeText(Transform parent, Vector2 anchoredPos, TextAnchor anchor, string text, int size)
    {
        var go = new GameObject("Text", typeof(Text));
        go.transform.SetParent(parent, false);
        var t = go.GetComponent<Text>();
        t.font = font; t.fontSize = size; t.text = text; t.alignment = anchor; t.color = Color.white;
        var rt = t.rectTransform;
        rt.anchorMin = rt.anchorMax = new Vector2(0, 1); rt.pivot = new Vector2(0, 1);
        rt.anchoredPosition = anchoredPos; rt.sizeDelta = new Vector2(900, 300);
        return t;
    }

    public void SetObjective(string s) { if (objective) objective.text = s; }
    public void ShowComplete() { if (complete) complete.gameObject.SetActive(true); SetObjective(""); }
}
```

- [ ] **Step 3: 编译验证**

Console 0 errors；确认 uGUI（`com.unity.ugui`）已在该工程中（Unity 6 默认内置）。
Expected: 通过。

- [ ] **Step 4: Commit**

```bash
git add game/Assets/Scripts/GoalTrigger.cs game/Assets/Scripts/SimpleUI.cs
git commit -m "feat(M2): 终点触发与中文 HUD（系统字体动态加载）"
```

### Task M2-6: 集成试玩验收（用户实测）

> 🚦 本任务必须用户参与；验收通过前不得进入 M3。

- [ ] **Step 1: 我先自查**：统一截图 `docs/milestones/M2/`（主厅全景、门洞、机关、石台）；Console 无错误无警告；确认场景已保存。
- [ ] **Step 2: 给用户实机试玩清单**（用户在 Unity 打开 `Demo.unity` 点 Play，逐条验证并回报）：
  1. WASD 移动 + 鼠标环绕相机（视角不穿墙）
  2. 空格跳跃；按住 Shift 加速
  3. 走近推石块（-2,-2 位置），可把它一路推到 (4,-2) 的压力板上（推动受轴约束、速度稳定）
  4. 石块压上压力板 → 压力板下沉 + 石门升起；把石块推离 → 石门落下
  5. 石门开启时穿过门洞进入 Room B
  6. 走到石台南面（z≈16 一侧）贴墙向前推 → 自动攀爬 → 到顶翻上石台
  7. 攀爬中按 S 可中途松手落地
  8. 走上石台触碰宝物 → 屏幕出现「探索完成！」
- [ ] **Step 3: 收集问题并修复**（按用户反馈逐条改；每次修改后重新自查截图，再请用户复验直至通过）
- [ ] **Step 4: 写 `docs/milestones/M2/report.md`**（截图、验收记录、修复项、遗留问题）。
- [ ] **Step 5: Commit + 汇报**

```bash
git add docs/milestones/M2
git commit -m "docs(M2): 灰盒玩法集成验收通过"
```
停下汇报，等用户确认后进入 M3。

---

## 里程碑 M3：场景资产替换（Blender 生产古墓套件）

> 目标：Blender 生成正式环境资产并替换灰盒，视觉呈「古墓」风；关卡保持可玩。
> 产出：`temple_kit.py`、`blender_assets/export/temple/*.fbx`、`KitPlacer.cs`、替换后的 `Demo.unity`。
> 🚦 门禁：开工需用户指令；结束停下汇报（含对比截图）。

### Task M3-1: 古墓套件生成脚本（含材质）+ headless 自测 + 批量导出

**Files:**
- Create: `blender_assets/scripts/temple_kit.py`
- Create（产物）: `blender_assets/export/temple/SM_*.fbx`、`blender_assets/scenes/M3_kit.blend`

**Interfaces:**
- Consumes: M1 的"破损顶点处理"手法；命名规范 `SM_/M_`。
- Produces: 每资产独立 FBX（供 M3-3 摆放），具体清单与尺寸：

| 资产 | 尺寸（米） | 面数预算 | 说明 |
|---|---|---|---|
| SM_FloorTile_A / B | 2×0.3×2 | 50-300 | 石砖，B 有破损缺口，A/B 交替铺 |
| SM_Wall_A / B | 4×3×0.5 | 100-400 | 墙段，B 带裂纹凹槽 |
| SM_Pillar_Whole | 3×0.5 径 | 200-800 | 10 边形 + 上下柱头 |
| SM_Pillar_Broken | 3×0.5 径 | 200-800 | M1 风格升级版（断口更自然） |
| SM_Arch | 4×4×0.6 | 300-1000 | 门洞拱（两柱+顶部梯形段，布尔挖洞） |
| SM_Stairs | 3 宽×1.5 深×1.5 高 | 100-400 | 5 级台阶 |
| SM_DoorFrame | 3.4×4.2×0.6 | 200-600 | 石门框 |
| SM_Brazier | 高 1.0 | 200-600 | 火盆（柱座+碗），火面用 M_Fire |
| SM_PressurePlate | 1.2×0.12×1.2 | 50-200 | 与 LevelSpec.PlatePos 对位 |
| SM_PushBlock | 1×1×1 | 100-400 | 崩边石块 |
| SM_StoneDoor | 3×4×0.4 | 200-800 | 浮雕槽石门 |
| SM_Altar | 2×1×1 | 200-600 | 双层台 |
| SM_Treasure | 0.4³×1.2 高 | 100-400 | 发光宝物（M_Treasure_Glow） |
| SM_Debris_A / B | 0.5-1.0 | 50-200 | 碎石 |

- [ ] **Step 1: 写脚本骨架（模式与 M1 一致，完整函数结构见下）**

```python
"""M3: 生成古墓环境套件并批量导出 FBX。
headless: blender.exe --background --factory-startup --python temple_kit.py"""
import bpy, bmesh, random, os

random.seed(7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(ROOT, "export", "temple")

# 通用工具（复用 M1 模式）
def new_mesh_obj(name):            # 清空默认物体并新建空网格对象
def box(name, size, bevel=0.02):   # 倒角方盒
def jitter_verts(obj, amp, zmin=0.0):   # 顶点随机抖动（破损感）
def cut_notch(obj, ...):           # 布尔切缺口（用 bmesh.ops.bisect_plane 或布尔立方体）
def cylinder(name, verts, r, depth):
def assign_material(obj, mat_name, color, rough, metal=0.0, emission=None)

MATERIALS = {
    "M_Stone":       dict(color=(0.42, 0.40, 0.37, 1), rough=0.9),
    "M_Stone_Dark":  dict(color=(0.30, 0.29, 0.27, 1), rough=0.92),
    "M_Metal_Dark":  dict(color=(0.25, 0.24, 0.22, 1), rough=0.55, metal=0.8),
    "M_Fire":        dict(color=(1.0, 0.5, 0.1, 1), rough=1.0, emission=(1.0, 0.4, 0.05)),
    "M_Treasure_Glow": dict(color=(1.0, 0.85, 0.4, 1), rough=0.3, emission=(1.0, 0.8, 0.3)),
}

def build_all():
    """按上表逐个构建；每个资产构建后: 命名/材质/平直着色/断言面数预算。"""
    # 例: floor tile
    t = box("SM_FloorTile_A", (2, 2, 0.3)); jitter_verts(t, 0.015)
    assign_material(t, "M_Stone"); yield t
    # ...（其余资产按上表逐一实现；破损类复用 jitter/cut_notch）
    # 提示实现顺序: 砖/墙 → 柱 → 拱/台阶/门框 → 机关三件套 → 祭坛/宝物/火盆/碎石

def export_obj(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    path = os.path.join(EXPORT_DIR, f"{obj.name}.fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True,
        apply_scale_options='FBX_SCALE_ALL', apply_unit_scale=True,
        axis_forward='-Z', axis_up='Y', object_types={'MESH'})

def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    objs = list(build_all())
    assert len(objs) == 16, f"资产数量不符: {len(objs)}"       # 表中 16 个（A/B 各计一个）
    for o in objs:
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        assert tris <= 1000, f"{o.name} 面数超预算: {tris}"
        export_obj(o)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "scenes", "M3_kit.blend"))
    print(f"OK assets={len(objs)}")

main()
```

（实现要求：每个资产在 `build_all()` 中按上表尺寸/面数预算逐一实现，禁止留空；布尔缺口用 `bmesh.ops` 实现，避免依赖 Blender 6.x 才有的新算子。）

- [ ] **Step 2: headless 自测**

Run: `& "E:\SteamLibrary\steamapps\common\Blender\blender.exe" --background --factory-startup --python "e:\pro\blender_mcp\blender_assets\scripts\temple_kit.py"`
Expected: 输出 `OK assets=16`；`blender_assets/export/temple/` 下 16 个 FBX 均 >5KB。

- [ ] **Step 3: 渲染套件总览图（自查 + 给用户看）**

在脚本加 `--render` 分支：所有资产排成陈列墙 + 相机 + EEVEE 渲染 → `docs/milestones/M3/kit_overview.png`。
Expected: 图片能看清各资产形态与破损效果；不满意则调整参数重渲。

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/temple_kit.py blender_assets/export/temple docs/milestones/M3 blender_assets/scenes
git commit -m "feat(M3): 古墓环境套件（16 资产）生成与导出"
```

### Task M3-2: （并入 M3-1 执行，无需独立任务——材质在脚本内完成）

### Task M3-3: Unity 按坐标表用正式资产替换灰盒

**Files:**
- Create: `game/Assets/Editor/KitPlacer.cs`
- 复制: `blender_assets/export/temple/*.fbx` → `game/Assets/Art/Static/temple/*.fbx`

**Interfaces:**
- Consumes: `LevelSpec`（M2-1）；FBX 资产（M3-1）；灰盒对象名（GrayboxBuilder 生成的名字）。
- Produces: `KitPlacer.Replace()` + 菜单 `Demo/用正式资产替换灰盒`；替换后的场景（机关/碰撞/脚本引用全部保留）。

- [ ] **Step 1: 复制资产**

Run: `Copy-Item "e:\pro\blender_mcp\blender_assets\export\temple\*.fbx" "e:\pro\blender_mcp\game\Assets\Art\Static\temple\" -Force`
Expected: Unity 自动导入；Console 无 Error。

- [ ] **Step 2: 写 `KitPlacer.cs`（核心模式如下，完整实现覆盖全部灰盒对象名）**

```csharp
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class KitPlacer
{
    [MenuItem("Demo/用正式资产替换灰盒")]
    public static void Replace()
    {
        var scene = EditorSceneManager.OpenScene("Assets/Scenes/Demo.unity", OpenSceneMode.Single);

        // 1) 地面: 删除 FloorA/FloorB 大板，按 2m 网格用 SM_FloorTile_A/B 交错铺设（保持原 Y=-0.25 面）
        ReplaceTiled("FloorA", new Rect(-10, -8, 20, 16));
        ReplaceTiled("FloorB", new Rect(-8, 8, 16, 14));

        // 2) 墙: 按对象名找到每面墙 → 用 4m 墙段沿墙面排列替换（保留碰撞: 逐段 BoxCollider）
        ReplaceWalls();

        // 3) 机关/道具: 一一对应替换（位置取原灰盒对象 transform，销毁灰盒后实例化正式模型，保留既有脚本组件——用 GameObject 包装承载）
        Swap("StoneDoor",    "SM_StoneDoor");
        Swap("ClimbableLedge","SM_Stairs");      // 石台本体保留灰盒+贴面（碰撞简单），靠墙外观用拱/柱装饰
        Swap("PressurePlate","SM_PressurePlate");
        Swap("PushBlock",    "SM_PushBlock");    // 注意: 必须保留 Rigidbody/PushBlock/tag 于新的视觉体上
        Swap("Altar",        "SM_Altar");
        Swap("Treasure",     "SM_Treasure");     // 保留 SphereCollider(isTrigger)/GoalTrigger
        // 4) 装饰: 石柱×4(±7,±5)、破柱×2、火盆×2(±3,-6 与门前)、拱门(门洞两侧)、碎石若干
        Decorate();

        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
        Debug.Log("[KitPlacer] 灰盒替换完成");
    }
    // Swap 要点: 在原对象位置实例化 FBX 模型 → 把原对象的关键组件（脚本/Rigidbody/Collider/tag/layer）
    // 迁移到新对象或其父包装体上 → 删除原灰盒视觉体。机关脚本引用（plate.door）重新接线。
}
```

实现要求：`Swap` 迁移组件时必须保留 —— Player/PushBlock 的 tag、StoneDoor/PressurePlate 的脚本引用、ClimbableLedge 的 Layer 与 BoxCollider；替换后 Play 测试关卡逻辑不回退。

- [ ] **Step 3: 触发替换并验证**

触发方式同 M2-1 Step 4（MCP 菜单触发 / 用户点菜单 / CLI）。
Expected: Console 打印替换完成；截图对比灰盒（替换前）与替换后 → `docs/milestones/M3/after_replace_*.png`；Play 检查：机关链路仍可玩、攀爬面仍是可攀 Layer。

- [ ] **Step 4: Commit**

```bash
git add game/Assets/Editor/KitPlacer.cs game/Assets/Art/Static/temple
git commit -m "feat(M3): 正式资产替换灰盒（保持玩法链路）"
```

### Task M3-4: 光照氛围初调

**Files:**
- 修改: 场景光照（通过编辑器脚本 `LightingSetup.cs` 或直接改 RenderSettings；推荐脚本化以便复现）

**Interfaces:**
- Produces: 雾（RenderSettings.fog=true, exponential, density≈0.012, 深蓝灰色）、暗环境、火盆位置点光（暖橙）就位；M5 在此基础上加 Flicker/Bloom。

- [ ] **Step 1: 写 `game/Assets/Editor/LightingSetup.cs`**（`[MenuItem("Demo/应用基础光照")]`）：设置 fog/ambient/sun（同 M2 占位参数但微调）；确保 4 个火盆处有暖色点光（位置对齐装饰表）。
- [ ] **Step 2: 应用 + 截图**：`docs/milestones/M3/lighting_*.png`（主厅/出口厅两个视角）。
- [ ] **Step 3: Commit**

```bash
git add game/Assets/Editor/LightingSetup.cs docs/milestones/M3
git commit -m "feat(M3): 古墓基础光照与雾氛围"
```

### Task M3-5: 用户验收 + 汇报

- [ ] **Step 1: 邀请用户实机走一遍**（关注：观感是否"古墓"、有无穿插/悬空/比例问题、帧率是否流畅）。
- [ ] **Step 2: 修复反馈项 → 复验 → 写 `docs/milestones/M3/report.md` → Commit。**
- [ ] **Step 3: 停下汇报，等用户确认后进入 M4。**

---

## 里程碑 M4：主角资产（建模 + 绑骨 + 动画）——全计划最高风险段

> 目标：Blender 生成风格化低模探险者（含骨架、权重、5 段动画），导入 Unity 接入 Animator 替换胶囊。
> 产出：`build_hero.py`、`hero_anims.py`、`SK_Explorer.fbx`、`ExplorerAnimator.controller`、`docs/milestones/M4/` 证据。
> 🚦 门禁：开工需用户指令；每个 Task 的模型/绑定/动画中间产物先给用户看截图；M4-5 用户实机验收；结束停下汇报。
> ⚠️ 质量预期（写入 M4 报告）：风格化方块感角色 + 简洁程序化动画；不追求写实。若动画观感不达标，降级顺序：①减小摆幅/降速匹配 ②动作数精简为 Idle/Walk/Climb ③接受更抽象表现。

### Task M4-1: 低模人形网格（部件表构建）

**Files:**
- Create: `blender_assets/scripts/build_hero.py`（第一部分：网格）
- Create（产物）: `blender_assets/scenes/M4_hero.blend`、`docs/milestones/M4/hero_model.png`

**Interfaces:**
- Produces: 网格对象 `SK_Explorer`（高 ≈1.75m，面向 +Z，站姿 T-pose 手臂自然下垂 15°，3-6k tris）；材质槽顺序 `M_Skin/M_Shirt/M_Pants/M_Boots`；供 M4-2 绑定。

- [ ] **Step 1: 按部件表写构建代码（全部坐标/尺寸/材质在此固定，勿改）**

| 部件 | 图元 | 中心 (x, y, z) | 尺寸/参数 | 材质 |
|---|---|---|---|---|
| 头 | box | (0, 1.62, 0) | 0.22×0.24×0.24，倒角 0.03 | M_Skin |
| 躯干 | box | (0, 1.24, 0) | 0.42×0.55×0.24，倒角 0.04，上宽下窄（顶面 x×1.08） | M_Shirt |
| 左/右上臂 | cyl | (±0.27, 1.27, 0) | r=0.06, len=0.32，垂放 15° 外摆 | M_Shirt |
| 左/右前臂 | cyl | (±0.30, 0.97, 0.02) | r=0.055, len=0.28 | M_Skin |
| 左/右大腿 | cyl | (±0.11, 0.72, 0) | r=0.09, len=0.45 | M_Pants |
| 左/右小腿 | cyl | (±0.11, 0.29, 0) | r=0.075, len=0.42 | M_Pants |
| 左/右脚 | box | (±0.11, 0.05, 0.04) | 0.16×0.10×0.26 | M_Boots |

实现模式：与 temple_kit.py 相同（box/cylinder 工具函数 + bevel + join + 平直着色 + `merge by distance` 0.001 焊接邻近部件接缝，便于后续自动权重）。

```python
# build_hero.py 关键函数签名
def hero_materials():                      # 创建 4 个材质并返回 dict
def add_part(name, kind, center, size, mat, bevel=0.02, rot=None):   # 单部件
def build_body():                          # 按上表逐部件创建 → join → SK_Explorer → merge_by_distance(0.001)
def render_variants(path):                 # 4 视角渲染（前/侧/背/斜）拼图输出
def main():
    build_body()
    o = bpy.data.objects["SK_Explorer"]
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    assert 1000 <= tris <= 6000, tris
    assert 1.6 <= o.dimensions.z <= 1.9, o.dimensions.z
    render_variants(os.path.join(ROOT, "..", "docs", "milestones", "M4", "hero_model.png"))
    bpy.ops.wm.save_as_mainfile(filepath=M4_BLEND)
    print(f"OK hero tris={tris} h={o.dimensions.z:.2f}")
main()
```

- [ ] **Step 2: headless 自测**

Run: `& "E:\SteamLibrary\steamapps\common\Blender\blender.exe" --background --factory-startup --python "e:\pro\blender_mcp\blender_assets\scripts\build_hero.py"`
Expected: `OK hero tris=... h=1.7x`；渲染图存在。
**用户检查点 ①**：把 `hero_model.png` 给用户看，形态认可后才继续（不认可则调部件表重渲，最多 2 轮）。

- [ ] **Step 3: Commit**

```bash
git add blender_assets/scripts/build_hero.py docs/milestones/M4
git commit -m "feat(M4): 主角低模网格（部件表构建）"
```

### Task M4-2: 骨架 + 蒙皮权重

**Files:**
- Modify: `blender_assets/scripts/build_hero.py`（追加骨架与权重段）
- Create（产物）: `docs/milestones/M4/hero_rig_test.png`

**Interfaces:**
- Produces: 骨架对象 `Armature_Hero`，骨骼命名（Unity 友好）：`Hips, Spine, Chest, Neck, Head, Shoulder.L/R, UpperArm.L/R, LowerArm.L/R, Hand.L/R, UpperLeg.L/R, LowerLeg.L/R, Foot.L/R`（共 17 根变形骨）；网格已挂 Armature 修改器且各骨骼顶点组非空。

- [ ] **Step 1: 骨架坐标表（head→tail，单位米）**

| 骨骼 | head | tail | 父级 |
|---|---|---|---|
| Hips | (0, 0.95, 0) | (0, 1.10, 0) | - |
| Spine | (0, 1.10, 0) | (0, 1.35, 0) | Hips |
| Chest | (0, 1.35, 0) | (0, 1.50, 0) | Spine |
| Neck | (0, 1.50, 0) | (0, 1.56, 0) | Chest |
| Head | (0, 1.56, 0) | (0, 1.74, 0) | Neck |
| Shoulder.L/R | (±0.08, 1.44, 0) | (±0.26, 1.43, 0) | Chest |
| UpperArm.L/R | (±0.26, 1.43, 0) | (±0.29, 1.11, 0) | Shoulder |
| LowerArm.L/R | (±0.29, 1.11, 0) | (±0.31, 0.84, 0) | UpperArm |
| Hand.L/R | (±0.31, 0.84, 0.02) | (±0.31, 0.74, 0.03) | LowerArm |
| UpperLeg.L/R | (±0.11, 0.95, 0) | (±0.11, 0.50, 0) | Hips |
| LowerLeg.L/R | (±0.11, 0.50, 0) | (±0.11, 0.10, 0) | UpperLeg |
| Foot.L/R | (±0.11, 0.10, 0) | (±0.11, 0.02, 0.14) | LowerLeg |

- [ ] **Step 2: 绑定流程（按此顺序，含失败兜底）**

1. 建骨架（edit mode 按上表建骨，`use_connect` 按父子链）。
2. 网格 + 骨架选中 → `bpy.ops.object.parent_set(type='ARMATURE_AUTO')`（自动权重）。
3. 断言：遍历 `Armature_Hero` 的变形骨，每根在网格上存在同名顶点组且顶点数 > 0；失败项打印。
4. 姿态测试：设 `UpperLeg.L` 旋转 45° → 渲染 `hero_rig_test.png`。
5. **兜底（自动权重异常时）**：按"部件→骨骼"硬绑定——头部顶点全给 `Head`、躯干给 `Chest/Spine` 分段、每段肢体给对应骨、脚给 `Foot`（用顶点 y 坐标范围筛选赋权重 1.0）。方块风格角色该方式观感可接受且绝对稳定；报告记录所用方式。

- [ ] **Step 3: headless 自测 + 用户检查点 ②**

Run: 同 M4-1 方式执行 `build_hero.py`。
Expected: 输出各骨骼顶点组统计无 FAIL；`hero_rig_test.png` 中大腿抬起无严重拉丝/破面。
**用户检查点 ②**：给用户看绑定测试图，认可后继续。

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/build_hero.py docs/milestones/M4
git commit -m "feat(M4): 主角骨架与蒙皮（自动权重+硬绑定兜底）"
```

### Task M4-3: 五段动画 Action（正弦程序化 + 关键姿态）

**Files:**
- Create: `blender_assets/scripts/hero_anims.py`
- Create（产物）: `docs/milestones/M4/anim_sheet_*.png`（每动作 4 帧条）

**Interfaces:**
- Consumes: `Armature_Hero`（M4-2）；`scene.render.fps = 30`。
- Produces: 5 个 Action：`A_Idle(60f) / A_Walk(27f) / A_Run(20f) / A_Jump(27f) / A_Climb(36f)`，全部 push 到独立 NLA track（供 FBX 全量导出）。

- [ ] **Step 1: 动画参数表（动作、周期、幅度——实现时按此，不得另设）**

| 动作 | 帧数@30fps | 类型 | 关键参数 |
|---|---|---|---|
| A_Idle | 60 | 正弦循环 | Chest ±1.5°；Hips 上下 ±0.012m（双频）；手臂 ±2° |
| A_Walk | 27 | 正弦循环 | 大腿 ±28°（左右反相）；小腿 0~-35°（相位滞后 0.6rad）；手臂 ∓20°；Hips 上下 ±0.03m（双频） |
| A_Run | 20 | 正弦循环 | 大腿 ±40°；手臂 ∓35°；躯干前倾 8°（Spine 固定偏移）；Hips 上下 ±0.05m |
| A_Jump | 27 | 关键姿态 | f0 站立 → f5 下蹲（大腿屈 30°、Hips 降 0.15）→ f10 伸展起跳（手臂上摆 40°）→ f16 空中收腿（大腿屈 25°）→ f27 落地缓冲回站立 |
| A_Climb | 36 | 正弦循环 | 手臂交替上举 ±60°（左右反相）；大腿交替屈 20°（与手臂同相错 0.5π）；Hips 左右轻摆 ±0.03m |

- [ ] **Step 2: 写脚本（核心函数实例如下，其余动作复用同一模式）**

```python
import bpy, math

def set_rot(arm, bone, x=0.0, y=0.0, z=0.0):
    pb = arm.pose.bones[bone]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (x, y, z)

def set_loc(arm, bone, dx=0.0, dy=0.0, dz=0.0):
    arm.pose.bones[bone].location = (dx, dy, dz)   # 注意: 骨骼局部坐标

def key_all(arm, frame):
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_euler", frame=frame)
        pb.keyframe_insert("location", frame=frame)

def make_walk(arm, period=0.9, fps=30, amp_leg=28, amp_arm=20):
    act = bpy.data.actions.new("A_Walk")
    arm.animation_data_create(); arm.animation_data.action = act
    n = int(period * fps)
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        set_rot(arm, "UpperLeg.L", x=math.radians(amp_leg) * math.sin(ph))
        set_rot(arm, "UpperLeg.R", x=math.radians(amp_leg) * math.sin(ph + math.pi))
        set_rot(arm, "LowerLeg.L", x=math.radians(-35) * max(0, math.sin(ph + 0.6)))
        set_rot(arm, "LowerLeg.R", x=math.radians(-35) * max(0, math.sin(ph + math.pi + 0.6)))
        set_rot(arm, "UpperArm.L", x=math.radians(-amp_arm) * math.sin(ph + math.pi))
        set_rot(arm, "UpperArm.R", x=math.radians(-amp_arm) * math.sin(ph))
        set_loc(arm, "Hips", dz=0.03 * math.sin(2 * ph))
        key_all(arm, f)
    return act

def push_to_nla(arm, act):
    tr = arm.animation_data.nla_tracks.new()
    tr.name = act.name
    tr.strips.new(act.name, 0, act)
    arm.animation_data.action = None

def main():
    # 依次 make_idle/make_walk/make_run/make_jump/make_climb → push_to_nla
    # 每动作: 渲染 4 帧条 → docs/milestones/M4/anim_sheet_<name>.png
    # 断言: 每 action fcurve 数 > 0 且帧范围符合参数表
    print("OK anims=5")
main()
```

- [ ] **Step 3: headless 自测 + 用户检查点 ③**

Run: 同上方式执行。
Expected: 5 张动画条图；每图姿态符合参数表描述（走路腿交替、攀爬手交替上举等）。
**用户检查点 ③**：给用户看动画条图；认可后继续（最多迭代 2 轮，超限触发降级预案并汇报）。

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/hero_anims.py docs/milestones/M4
git commit -m "feat(M4): 主角五段程序化动画（idle/walk/run/jump/climb）"
```

### Task M4-4: FBX 导出（含动画）+ Unity 导入检查

**Files:**
- Create（产物）: `blender_assets/export/characters/SK_Explorer.fbx`
- Create: `game/Assets/Editor/HeroImporter.cs`
- 复制: FBX → `game/Assets/Art/Characters/`

**Interfaces:**
- Produces: Unity 内 `SK_Explorer` 模型的 5 个 AnimationClip（**准确 clip 名登记到 `docs/milestones/M4/report.md`**，M4-5 的控制器按此名加载）；Humanoid Rig 生效。

- [ ] **Step 1: 导出（hero_anims.py 追加导出段）**

```python
def export_hero(arm, mesh):
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True); mesh.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=OUT_FBX, use_selection=True,
        apply_scale_options='FBX_SCALE_ALL', apply_unit_scale=True,
        axis_forward='-Z', axis_up='Y',
        object_types={'ARMATURE', 'MESH'},
        bake_anim=True, bake_anim_use_nla_strips=True, bake_anim_use_all_actions=False,
        add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X')
```
（若 5.2 参数名与上不一致按等价语义调整并记录。）导出后断言文件 >50KB。

- [ ] **Step 2: 复制 + 写 `HeroImporter.cs`（检查与配置）**

```csharp
using UnityEngine;
using UnityEditor;

public class HeroImporter : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        if (!assetPath.Contains("SK_Explorer")) return;
        var imp = (ModelImporter)assetImporter;
        imp.animationType = ModelImporterAnimationType.Humanoid;
        imp.materialImportMode = ModelImporterMaterialImportMode.None;   // 用 Blender 材质色即可
    }
}
```
另提供 `[MenuItem("Demo/打印主角动画片段")]`：读取 `AssetDatabase.LoadAllAssetsAtPath("Assets/Art/Characters/SK_Explorer.fbx")` 中所有 AnimationClip 并 `Debug.Log` 名称与长度。

- [ ] **Step 3: 导入并验证**

Run: `Copy-Item ...\SK_Explorer.fbx ...\game\Assets\Art\Characters\ -Force` → 触发菜单打印。
Expected: 打印 5 个 clip；Rig 为 Humanoid 无映射错误（若有红叉 → 检查骨骼命名/层级，按 Unity 提示调整骨骼映射或修正 Blender 骨架）。结果登记报告。

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/hero_anims.py game/Assets/Editor/HeroImporter.cs game/Assets/Art/Characters docs/milestones/M4
git commit -m "feat(M4): 主角带动画 FBX 导出与 Unity Humanoid 导入"
```

### Task M4-5: Animator 控制器 + 接入控制器替换胶囊 + 用户实机验收

**Files:**
- Create: `game/Assets/Editor/AnimatorSetup.cs`
- Modify: `game/Assets/Scripts/ThirdPersonController.cs`（动画同步段）

**Interfaces:**
- Consumes: clip 名（M4-4 报告）；`ClimbSystem.IsClimbing`。
- Produces: `Assets/Animations/ExplorerAnimator.controller`；Animator 参数 `speed(float)/grounded(bool)/climbing(bool)/jump(trigger)`。

- [ ] **Step 1: 写 `AnimatorSetup.cs`（结构如下，clips 按 M4-4 实际名加载）**

```csharp
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

public static class AnimatorSetup
{
    [MenuItem("Demo/生成玩家 Animator")]
    public static void Setup()
    {
        var ctrl = AnimatorController.CreateAnimatorControllerAtPath("Assets/Animations/ExplorerAnimator.controller");
        ctrl.AddParameter("speed", AnimatorControllerParameterType.Float);
        ctrl.AddParameter("grounded", AnimatorControllerParameterType.Bool);
        ctrl.AddParameter("climbing", AnimatorControllerParameterType.Bool);
        ctrl.AddParameter("jump", AnimatorControllerParameterType.Trigger);

        var sm = ctrl.layers[0].stateMachine;
        var clips = LoadClips();                       // 见 Step 2
        var idle = sm.AddState("Idle"); idle.motion = clips["A_Idle"];
        var walk = sm.AddState("Walk"); walk.motion = clips["A_Walk"];
        var run = sm.AddState("Run"); run.motion = clips["A_Run"];
        var jump = sm.AddState("Jump"); jump.motion = clips["A_Jump"];
        var climb = sm.AddState("Climb"); climb.motion = clips["A_Climb"];
        sm.defaultState = idle;

        T(idle, walk, "speed", AnimatorConditionMode.Greater, 0.1f);
        T(walk, idle, "speed", AnimatorConditionMode.Less, 0.1f);
        T(walk, run, "speed", AnimatorConditionMode.Greater, 4.5f);
        T(run, walk, "speed", AnimatorConditionMode.Less, 4.5f);
        T(idle, jump, "jump", AnimatorConditionMode.If, 0f);
        T(walk, jump, "jump", AnimatorConditionMode.If, 0f);
        T(climb, idle, "climbing", AnimatorConditionMode.IfNot, 0f);
        T(idle, climb, "climbing", AnimatorConditionMode.If, 0f);
        T(walk, climb, "climbing", AnimatorConditionMode.If, 0f);
        var back = jump.AddTransition(idle);          // 跳跃播完自动回
        back.hasExitTime = true; back.exitTime = 0.85f; back.duration = 0.1f;
        AssetDatabase.SaveAssets();
        Debug.Log("[AnimatorSetup] ExplorerAnimator.controller 生成完成");
    }

    static void T(AnimatorState a, AnimatorState b, string p, AnimatorConditionMode m, float v)
    {
        var t = a.AddTransition(b); t.hasExitTime = false; t.duration = 0.1f;
        t.AddCondition(m, v, p);
    }

    static Dictionary<string, AnimationClip> LoadClips()
    {   // 从 Assets/Art/Characters/SK_Explorer.fbx 按 M4-4 登记的 clip 名加载
        var map = new Dictionary<string, AnimationClip>();
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath("Assets/Art/Characters/SK_Explorer.fbx"))
            if (o is AnimationClip c && !c.name.StartsWith("__preview")) map[c.name] = c;
        return map;
    }
}
```

- [ ] **Step 2: 玩家接线（editor 脚本或 MCP 操作，二选一记录）**

1. 实例化 `SK_Explorer` 为 `Player` 子对象（位置对齐胶囊中心，朝向 +Z）；隐藏胶囊的 MeshRenderer（保留 CharacterController 碰撞）。
2. 在 `Player`（或模型子对象）加 `Animator`：Controller=ExplorerAnimator，Avatar=从 fbx 生成的 Avatar。
3. `ThirdPersonController` 追加同步段：

```csharp
// 字段: Animator anim;   Start(): anim = GetComponentInChildren<Animator>();
// Update() 跳跃分支内追加: if (anim) anim.SetTrigger("jump");
// Update() 末尾追加:
void SyncAnimator()
{
    if (!anim) return;
    Vector3 hv = new Vector3(cc.velocity.x, 0f, cc.velocity.z);
    anim.SetFloat("speed", hv.magnitude);
    anim.SetBool("grounded", cc.isGrounded);
    anim.SetBool("climbing", climb && climb.IsClimbing);
}
```

- [ ] **Step 3: 用户实机验收**（Play Mode 清单）：
  1. 站立时呼吸待机动画 2. 走路/跑步动画随速度切换 3. 跳跃播放跳跃动作 4. 贴墙攀爬播放攀爬动画、登顶恢复正常 5. 整体无明显滑步/穿插（可接受简化，记录）
- [ ] **Step 4: 修复反馈 → 复验 → `docs/milestones/M4/report.md` → Commit**

```bash
git add game/Assets/Editor/AnimatorSetup.cs game/Assets/Scripts/ThirdPersonController.cs game/Assets/Animations docs/milestones/M4
git commit -m "feat(M4): Animator 控制器与主角动画接入"
```
停下汇报，等用户确认后进入 M5。

---

## 里程碑 M5：打磨与交付

> 目标：音效、氛围、UI、性能收尾；可选打包 exe；完整验收。
> 产出：`tools/audio_gen.py` 等、`game/Assets/Audio/`、终验报告。
> 🚦 门禁：开工需用户指令；含两次用户试听/试玩；结束完成整体验收后由用户决定是否推送/打包。

### Task M5-1: 音效合成脚本 + 波形自检

**Files:**
- Create: `tools/audio_gen.py`、`tools/audio_check.py`
- Create（产物）: `game/Assets/Audio/*.wav`

**Interfaces:**
- Produces: 10 个音效 WAV（44.1kHz/16bit/mono）；文件名固定（M5-2 按名接线）：
  `ambient_temple.wav / fire_crackle.wav / footstep_stone_1..4.wav / jump.wav / land.wav / block_grind.wav / plate_click.wav / door_rumble.wav / goal_chime.wav`

- [ ] **Step 1: 参数表（合成目标）**

| 文件 | 时长 | 合成配方 |
|---|---|---|
| ambient_temple | 30s loop | 棕噪声低速滤波 + 0.05Hz 幅度起伏 + 每 4-9s 随机水滴（1.2kHz 正弦指数衰减 80ms） |
| fire_crackle | 10s loop | 低幅棕噪声底 + 每秒 3-8 个随机噼啪（高通短脉冲 30-80ms） |
| footstep_stone_1..4 | 0.25s | 带通噪声 burst（中心 400/500/650/800Hz 各一版）+ 快衰减（20ms attack, 180ms decay） |
| jump | 0.35s | 低频 thud（120Hz 正弦 + 噪声，80ms 起音）+ 上滑音 |
| land | 0.30s | 低频 thud（90Hz）+ 噪声，更重尾音 |
| block_grind | 2s loop | 带通噪声（200-800Hz 扫频）+ 周期性幅度调制（8Hz） |
| plate_click | 0.25s | 高频双脉冲（2.5kHz）+ 快速衰减（clack 感） |
| door_rumble | 3s | 低频噪声（60-150Hz）渐强 2s + 1s 衰减尾 |
| goal_chime | 2.5s | C5-E5-G5 正弦叠加，各自错开 150ms 起音、指数衰减 + 轻微 detune |

- [ ] **Step 2: 写 `audio_gen.py`（纯标准库；核心工具函数 + 一个完整示例）**

```python
import wave, struct, math, random, os

SR, OUT = 44100, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game", "Assets", "Audio")

def write_wav(name, samples):                       # samples: -1..1 float 列表
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))

def lowpass(sig, alpha):                            # 一阶低通
    out, prev = [], 0.0
    for s in sig: prev += alpha * (s - prev); out.append(prev)
    return out

def brown_noise(n, step=0.02):                      # 随机游走噪声（归一化）
    v, out = 0.0, []
    for _ in range(n):
        v = max(-1, min(1, v + random.uniform(-step, step))); out.append(v)
    return out

def env(n, attack, decay):                          # 简单 AD 包络
    return [min(1.0, i / attack) * math.exp(-max(0, i - attack) / decay) for i in range(n)]

def gen_footstep(center_hz, dur=0.25, seed=1):
    random.seed(seed)
    n = int(dur * SR)
    noise = [random.uniform(-1, 1) for _ in range(n)]
    # 简易带通 = 低通(高频) - 低通(低频)
    lo = lowpass(noise, 0.35); band = [a - b for a, b in zip(lowpass(noise, 0.08), lo)]
    e = env(n, int(0.02 * SR), int(0.06 * SR))
    return [band[i] * e[i] * 0.8 for i in range(n)]

def main():
    random.seed(42)
    write_wav("footstep_stone_1.wav", gen_footstep(400, seed=1))
    write_wav("footstep_stone_2.wav", gen_footstep(500, seed=2))
    write_wav("footstep_stone_3.wav", gen_footstep(650, seed=3))
    write_wav("footstep_stone_4.wav", gen_footstep(800, seed=4))
    # ... 其余按参数表逐一实现（ambient/fire/jump/land/grind/click/rumble/chime 各一个函数）
    print("OK audio generated")

main()
```
（实现要求：按参数表补全其余 8 个生成函数，禁止空实现。）

- [ ] **Step 3: 写 `tools/audio_check.py` 并运行自检**

自检项：文件存在；时长与目标偏差 ≤10%；峰值 ≤0.99（不削波）；RMS ∈ [-30, -12] dB；无全零段（前 1 秒 RMS > -60dB）。全部通过打印表格并退出码 0。
Run: `python "e:\pro\blender_mcp\tools\audio_check.py"`
Expected: 表格全绿，退出码 0。（若削波 → 降增益重生成；若过静 → 提升；迭代至通过。）

- [ ] **Step 4: 用户试听检查点**

把 10 个 wav 路径给用户试听，收集"怪"的反馈并按参数表微调（最多 2 轮）。记录结论。

- [ ] **Step 5: Commit**

```bash
git add tools/audio_gen.py tools/audio_check.py game/Assets/Audio
git commit -m "feat(M5): 程序化音效合成（10 音效）与波形自检"
```

### Task M5-2: Unity 音频集成

**Files:**
- Create: `game/Assets/Scripts/AudioManager.cs`
- Create: `game/Assets/Editor/AudioWiring.cs`（将 wav 赋到 AudioManager 字段 + 场景摆放）
- Modify: 各事件脚本（每处 1-3 行）

**Interfaces:**
- Produces: `AudioManager.Instance.Footstep()/Jump()/Land()/PlateClick()/Door()/Goal()/Grind(bool)`。

- [ ] **Step 1: 写 `AudioManager.cs`（完整内容）**

```csharp
using UnityEngine;

public class AudioManager : MonoBehaviour
{
    public static AudioManager Instance;
    public AudioClip[] footsteps;
    public AudioClip jump, land, plateClick, doorRumble, goalChime, blockGrind, ambient, fireCrackle;

    AudioSource oneShot, grind;

    void Awake()
    {
        Instance = this;
        oneShot = gameObject.AddComponent<AudioSource>(); oneShot.playOnAwake = false;
        grind = gameObject.AddComponent<AudioSource>();
        grind.loop = true; grind.volume = 0.5f; grind.clip = blockGrind;
        PlayLoop(ambient, 0.45f); PlayLoop(fireCrackle, 0.3f);
    }

    void PlayLoop(AudioClip c, float v)
    { if (!c) return; var s = gameObject.AddComponent<AudioSource>(); s.clip = c; s.loop = true; s.volume = v; s.Play(); }

    public void OneShot(AudioClip c, float v = 1f) { if (c) oneShot.PlayOneShot(c, v); }
    public void Footstep() { if (footsteps != null && footsteps.Length > 0) oneShot.PlayOneShot(footsteps[Random.Range(0, footsteps.Length)], 0.7f); }
    public void Jump() => OneShot(jump, 0.8f);
    public void Land() => OneShot(land, 0.9f);
    public void PlateClick() => OneShot(plateClick);
    public void Door() => OneShot(doorRumble);
    public void Goal() => OneShot(goalChime);
    public void Grind(bool on)
    {
        if (!grind.clip) return;
        if (on && !grind.isPlaying) grind.Play();
        else if (!on && grind.isPlaying) grind.Stop();
    }
}
```

- [ ] **Step 2: 事件接线补丁（逐处修改）**

| 脚本 | 修改点 |
|---|---|
| ThirdPersonController | 累计水平位移 ≥2.2m 且 grounded 时 `AudioManager.Instance?.Footstep()` 并清零；跳跃分支 `?.Jump()`；`!wasGrounded && grounded && velocityY < -3f` → `?.Land()` |
| StoneDoor | Open()/Close() 首帧调用 `AudioManager.Instance?.Door()` |
| PressurePlate | 首次 occupants 0→1 时 `?.PlateClick()` |
| PushBlock | 在 Push() 或 Update 中按 `rb.linearVelocity` 水平速度 >0.05 持续时 `?.Grind(true)`，否则 `?.Grind(false)` |
| GoalTrigger | 触发成功时 `?.Goal()` |

- [ ] **Step 3: 写 `AudioWiring.cs`**：`[MenuItem("Demo/接线音效")]`——场景创建/查找 `AudioManager` 对象；按文件名 `Assets/Audio/xxx.wav` 载入并赋到对应字段；保存场景。
- [ ] **Step 4: 执行接线 → Play 试听 → 用户验收（音量平衡、机关音效同步性）→ 调参复验。**
- [ ] **Step 5: Commit**

```bash
git add game/Assets/Scripts/AudioManager.cs game/Assets/Editor/AudioWiring.cs game/Assets/Scripts docs/milestones/M5
git commit -m "feat(M5): 音效接入（环境/脚步/机关/完成）"
```

### Task M5-3: 氛围打磨（火光闪烁 + 泛光）

**Files:**
- Create: `game/Assets/Scripts/FireFlicker.cs`
- Create: `game/Assets/Editor/PostFxSetup.cs`（可选：加 Global Volume + Bloom）

**Interfaces:**
- Produces: 火盆点光闪烁；宝藏/火光受 Bloom 增强。

- [ ] **Step 1: `FireFlicker.cs`（完整内容）**

```csharp
using UnityEngine;

[RequireComponent(typeof(Light))]
public class FireFlicker : MonoBehaviour
{
    public float baseIntensity = 1.6f, amp = 0.5f, speed = 8f;
    Light lt; float seed;

    void Awake() { lt = GetComponent<Light>(); seed = Random.value * 100f; }

    void Update()
    {
        lt.intensity = baseIntensity + (Mathf.PerlinNoise(seed, Time.time * speed) - 0.5f) * 2f * amp;
    }
}
```

- [ ] **Step 2:** 给全部火盆点光挂 `FireFlicker`（editor 脚本批量挂载）；`PostFxSetup.cs`：创建 Global Volume + Bloom（intensity 0.8、threshold 1.0）并保存；不支持的 URP 配置则跳过并记录。
- [ ] **Step 3:** 截图对比 `docs/milestones/M5/atmosphere_*.png`。
- [ ] **Step 4: Commit** `feat(M5): 火光闪烁与泛光氛围`

### Task M5-4: UI 完善（目标流转 + 操作说明 + 完成面板）

**Files:**
- Modify: `game/Assets/Scripts/SimpleUI.cs`

- [ ] **Step 1: 扩展 `SimpleUI`**：
  - 开局显示操作说明：`"WASD 移动 · 鼠标 视角 · 空格 跳跃 · 面向高台前推 攀爬"`，8 秒后淡出（协程，alpha 渐变）。
  - 标题行 `"古墓探索"` 顶部居中。完成面板：半透明黑底 `Image`（alpha 0.6，全屏）+ 大字 `"探索完成！\n你取得了圣物"` + 小字 `"感谢游玩 · 按 Esc 退出"`。
  - 目标流转保持：出生→"找到并开启石门"；（StoneDoor.Open 已改文案）→"石门已开——攀上高台，取得圣物！"；完成清空目标。
- [ ] **Step 2: Play 验证三段文案出现时机正确；截图归档。**
- [ ] **Step 3: Commit** `feat(M5): 中文 UI 完善（说明/目标流转/完成面板）`

### Task M5-5: 性能与 Console 清零

- [ ] **Step 1:** Play 下用 unityMCP 读 Console：清零所有 Error/Warning（含弃用 API 提示）。
- [ ] **Step 2:** 性能抽查：编辑器 Play 记录 帧率（应稳定 60+）、`Profiler` 简查（渲染线程、GC 无明显尖峰）；静态物体标记 Static 提升批处理。
- [ ] **Step 3:** 将结果写入 `docs/milestones/M5/report.md`。
- [ ] **Step 4: Commit** `chore(M5): 性能抽查与 Console 清零`

### Task M5-6:（可选，用户决定）打包 Windows exe

**Files:**
- Create: `game/Assets/Editor/BuildScript.cs`

- [ ] **Step 1: 写 `BuildScript.cs`**

```csharp
using UnityEditor;
using UnityEngine;

public static class BuildScript
{
    [MenuItem("Demo/打包 Windows")]
    public static void BuildWindows()
    {
        var opts = new BuildPlayerOptions
        {
            scenes = new[] { "Assets/Scenes/Demo.unity" },
            locationPathName = "Builds/TempleDemo/TempleDemo.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None
        };
        var report = BuildPipeline.BuildPlayer(opts);
        Debug.Log($"[BuildScript] 结果: {report.summary.result} 大小: {report.summary.totalSize / 1048576}MB");
    }
}
```
- [ ] **Step 2:** 触发打包（MCP 菜单 / 用户点菜单 / CLI）；运行 exe 截图；记录大小与结果。
- [ ] **Step 3: Commit** `build(M5): Windows 打包脚本与产物说明`（不使用 git 管理 Builds/，说明写入报告）。

### Task M5-7: 终验与收尾

- [ ] **Step 1: 用户完整验收**（3-5 分钟全流程）：出生→探索→推石压板→开门→穿门→攀爬→登顶取宝→完成画面；全程音效/氛围/UI 正常；无卡死穿模。
- [ ] **Step 2: 写项目根 `README.md`**（中文，简短）：项目一句话简介、目录结构、如何打开 Unity 工程运行、如何再次生成资产（脚本入口命令）、里程碑状态表。
- [ ] **Step 3: 写 `docs/milestones/M5/report.md`**：终验清单结果、性能数据、已知不足与后续建议（对接"AI游戏开发工作站"下一步的启示）。
- [ ] **Step 4: 最终 Commit + 汇报用户**：整体完成情况、证据索引；是否需要推送远程仓库由用户指示（默认不推送）。

---

## 自审记录（写完计划后的核查）

### 1. Spec 覆盖核对

| Spec 章节 | 覆盖任务 |
|---|---|
| §3 环境基线 / §4 架构（双 MCP、uvx 全路径） | M0-1～M0-4 |
| §5 目录结构与 git 策略 | 全局约束 + M0-4；`.gitignore` 已有 |
| §6 里程碑 M0～M5 全表 | 本文档 M0～M5 各节 |
| §7.1/7.2 关卡与玩法闭环 | M2-1 坐标表 + M2-2～M2-6 |
| §7.3 Unity 系统模块（全部脚本） | M2-2～M2-5 一一对应 |
| §8.1 环境/机关/道具/主角/动画清单 | M3-1 资产表、M4-1～M4-5 |
| §8.2 技术规范（比例/命名/FBX 参数/面数） | 全局约束 + 各导出段参数 |
| §8.3 音效清单与实现路径 | M5-1、M5-2 |
| §9 验证方式表 | 各里程碑验收步骤（含用户试玩清单） |
| §10 风险对策（Blender 5.2 兼容/PATH/FBX 轴向/动画降级） | M0-4 Step2、M0-1、M1-3 Step3、M4 头注降级预案 |
| §11 范围外 | 未安排对应任务（正确） |

### 2. 占位符扫描结论

- 全文无 TBD/TODO；M3-1 的资产实现以"清单表+参数+模式示例+面数断言"约束（16 个资产均为 5 类程序化模式的参数化变体），M5-1 同（10 音效为 8 个合成函数的参数化变体），实现信息完备。
- 所有引用外部产物（clip 名、MCP 工具名）均指向前置任务明确产出的登记文件（`M0-tool-notes.md`、`M4/report.md`），非凭空引用。

### 3. 类型/命名一致性核对

- `ClimbSystem.IsClimbing`（M2-3 定义）↔ M2-2 引用 ↔ M4-5 同步段引用：一致。
- `PushBlock.Push(Vector3)`（M2-4 定义）↔ M2-2 OnControllerColliderHit 调用：一致。
- `PressurePlate.door`（public StoneDoor）↔ GrayboxBuilder 接线：一致。
- `SimpleUI.Instance/SetObjective/ShowComplete`（M2-5 定义）↔ StoneDoor/GoalTrigger 调用：一致。
- `LevelSpec` 常量名（M2-1 定义）↔ M3-3 KitPlacer 消费：一致。
- `GrayboxBuilder.Build()` / `KitPlacer.Replace()` / `AnimatorSetup.Setup()` / `AudioWiring` 菜单触发模式统一。

### 4. 已知执行期需按实际情况微调的点（不属于计划缺陷，属环境不确定性）

- Blender 5.2 的 FBX 导出参数名、EEVEE 引擎名等以实际 API 为准（已在全局约束中约定处理方式）。
- unityMCP 工具名以 M0-4 登记为准（已约定）。
- 输入系统 activeInputHandler 的值以实测为准（M2-1 Step3 已给分流处理）。
