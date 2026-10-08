# AI 驱动 3D 游戏 Demo 设计文档（Blender MCP + Unity MCP）

> 日期：2026-10-08 · 状态：待用户评审 · 设计者：Qoder × 用户
> 关联文档：`3D游戏开发流程指南_Blender加大模型_古墓丽影风格.md`（导师提供，仅存本地不入库）

## 1. 背景与目标

导师提供《3D游戏开发流程指南_Blender加大模型_古墓丽影风格.md》，要求：使用 Qoder 通过 MCP 操控 Blender 直接建模，并结合 Unity 完成一个「古墓丽影风格」游戏 Demo，验证「AI 全链路」开发模式的可行性。

核心目标：

1. 我（Qoder）作为 MCP 客户端，同时连接 **Blender MCP** 与 **Unity MCP**，全程用工具调用完成开发
2. 全部建模美术资源（含主角模型、骨骼绑定、动画）由我通过 Blender 生成，不使用 Mixamo / 资源商店
3. 交付一个 Unity 编辑器可玩的垂直切片（3-5 分钟体验）；打包 exe 为可选加分项

## 2. 关键决策记录

| # | 决策点 | 结论 |
|---|--------|------|
| 1 | Demo 定位 | 垂直切片：1-2 个房间 + 第三人称移动/攀爬 + 1 个机关谜题 + 终点目标 |
| 2 | Blender 版本 | 先用 Steam 版 5.2；若 MCP 不兼容则加装官方 4.5 LTS（共存） |
| 3 | 美术来源 | 全部由 Qoder 通过 Blender MCP 生成 |
| 4 | 开发路径 | 方案 A「灰盒优先」：先灰盒跑通玩法，再由 Blender 资产逐个替换 |
| 5 | Blender MCP 选型 | 社区版 `mcp-for-blender`（ahujasid；支持 Blender 3.0+，带多角度截图便于自查） |
| 6 | Unity MCP 选型 | 社区版 `CoplayDev/unity-mcp`（支持 Unity 2021.3 LTS → 6.x） |
| 7 | 工程组织 | `blender_assets/` 与 `game/` 两个独立文件夹；Unity 工程由用户在 Unity Hub 创建后交付路径 |
| 8 | 交付验收 | Unity 编辑器可玩；exe 可选 |
| 9 | 协作节奏 | 里程碑制：每阶段完成 → 停下汇报 → 用户确认后才进入下一阶段（不自动连推） |
| 10 | git 策略 | 工作区本地仓库；导师指南等参考材料不入库；推送前需用户确认 |
| 11 | 后续方向 | 若 Demo 链路好用 → 下一项目「AI游戏开发工作站」（另行立项，本次不涉及） |

## 3. 环境基线（2026-10-08 实测）

| 组件 | 现状 |
|---|---|
| uv / uvx | 0.12.19（WinGet 安装，未在 ~/.local/bin）；uvx 全路径：`C:\Users\windows\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uvx.exe` |
| Blender | Steam 版 **5.2**（`E:\SteamLibrary\steamapps\common\Blender\blender.exe`） |
| Unity | **6.3**（6000.3.21f1）位于 `D:\Unity\Hub\Editor\6000.3.21f1` |
| Unity Hub | `E:\Unity Hub\Unity Hub.exe` |
| 硬件 | RTX 4060 Laptop（8GB 显存）+ 32GB 内存（满足指南推荐基线） |
| Qoder MCP 配置 | `C:\Users\windows\.qoder\mcp.json`（当前为空 `{"mcpServers": {}}`，待写入两个 server） |
| git | 2.47.1（user: chenzhou0071） |

## 4. 总体架构

```
┌───────────────────────────  Qoder（MCP 客户端）  ───────────────────────────┐
│                                                                             │
│   ┌─ Blender MCP server ──(uvx mcp-for-blender)──socket(9876)──▶ Blender 5.2 │
│   │    能力：对象/材质操作、执行 bpy、多角度截图、渲染、FBX/GLB 导出            │
│   │                                                                          │
│   └─ Unity MCP server ──(uvx mcp-for-unity)──────────────▶ Unity 6.3 编辑器  │
│        能力：场景搭建、组件操作、C# 脚本、资产导入、Game 窗口截图、Console 日志 │
└─────────────────────────────────────────────────────────────────────────────┘
                      资产流转：blender_assets/export/*.fbx
                                ──(Unity 导入)──▶ game/Assets/Art/
```

- MCP 配置写入 `C:\Users\windows\.qoder\mcp.json`；`command` 使用 **uvx 全路径**（规避 GUI 进程 PATH 缺失问题）；配置后需重启 / reload Qoder 生效
- Blender 插件安装：`uvx mcp-for-blender install-addon` 自动安装；启动 Blender 后在 N 面板确认/启动 server
- Unity 侧：Unity 内 Package Manager 安装 `com.coplaydev.unity-mcp`，按向导完成 MCP 连接
- 具体安装命令与参数在实施计划中固化，以各项目当前官方文档为准

## 5. 目录结构与 git 策略

```
e:\pro\blender_mcp\                    ← git 仓库根
├─ .gitignore                          （忽略清单见 5.1）
├─ 3D游戏开发流程指南_....md            （导师文档：仅本地，不入库）
├─ docs\
│   ├─ superpowers\specs\              （设计文档）
│   └─ milestones\                     （每阶段成果截图与记录）
├─ blender_assets\                     ← 文件夹一：Blender 资源
│   ├─ scripts\                        （bpy 生成脚本）
│   ├─ scenes\                         （*.blend 源文件）
│   └─ export\                         （*.fbx，交给 Unity）
└─ game\                               ← 文件夹二：Unity 工程（用户创建）
    └─ Assets\Art\                     （导入的 Blender 资产）
```

### 5.1 .gitignore 忽略清单（已创建）

- 导师参考资料：`3D游戏开发流程指南_*.md`
- Unity 生成物：`game/Library/`、`Temp/`、`Obj/`、`Logs/`、`UserSettings/`、`Build*/`、`*.csproj`、`*.sln` 等
- Blender 自动备份：`*.blend1/2/3`
- 里程碑录屏视频（截图保留）：`docs/milestones/**/*.mp4|mov`
- 系统杂项：`Thumbs.db`、`desktop.ini`、`.DS_Store`

### 5.2 git 使用规则

- 每里程碑完成进行**本地** commit（无远程仓库，不涉及 push）
- 需要新建远程仓库 / 推送时，由用户明确指示后执行

## 6. 里程碑计划

| 阶段 | 目标 | 用户参与 | 验收标准 |
|---|---|---|---|
| **M0 环境部署与连通** | 配置 2 个 MCP server；装 Blender 插件；创建 Unity 工程并装 unity-mcp 包 | ①重启 Qoder ②开 Blender ③Unity Hub 创建工程（建议 `e:\pro\blender_mcp\game`，模板 Universal 3D / 6000.3.21f1）④装 unity-mcp 包 | 我能同时读取 Blender 场景对象、Unity 场景对象，并各截一张图 |
| **M1 最小链路验证** | Blender 生成测试石柱 → 截图 → 导出 FBX → Unity 导入并摆放 | 查看双端截图 | 石柱出现在 Unity 场景中且比例正确 |
| **M2 灰盒玩法** | Unity primitives 灰盒（2 房间）；第三人称控制器/相机/跳跃/攀爬/推石块/压力板/石门/终点 | **实机试玩** | 能完整玩通：走/跳/爬/推石压板/开门/登顶触碰宝物出现完成提示 |
| **M3 场景资产替换** | Blender 生产古墓环境套件 + 材质，替换灰盒；初步光照氛围 | 查看效果 | 同关卡可玩，视觉呈「古墓」风 |
| **M4 主角资产** | Blender 低模主角 + 绑骨 + 程序化动画（idle/walk/run/jump/climb）→ Unity Animator 接入 | **实机试玩** | 角色带动画表现：移动播走路、攀爬播攀爬、空中播跳跃 |
| **M5 打磨与交付** | 氛围（雾/火光/色调）、UI、音效占位、性能检查、（可选）打包 exe | 最终体验 | 3-5 分钟完整可玩；Console 无报错 |

时间预估：总计约 1.5-2 周（视踩坑情况），每阶段汇报实际进展与问题。

### 里程碑纪律

- 每个里程碑开始前：用户已明确下达开工指令
- 每个里程碑结束：停下汇报（成果 + 截图），等待用户确认后再进入下一阶段，**不自动连推**

## 7. 玩法与关卡设计

### 7.1 关卡布局（垂直切片）

```
┌──────────── Room A · 主厅（神庙入口） ────────────┐
│  出生点（UI 提示：找到开启石门的方法）             │
│  破损石柱×N、火盆×2、（可选陶罐）                  │
│  [石块] ──推动──▶ [压力板] ──触发──▶ [石门升起]   │
└──────────────────────── 石门 ──────────────────────┘
                             ▼
┌──────────── Room B · 出口厅 ──────────────────────┐
│  [攀爬石台 高≈3m] ──登顶──▶ [祭坛 + 发光宝物]     │
│                             触碰 → 「探索完成」    │
└────────────────────────────────────────────────────┘
```

### 7.2 玩法闭环与操作

出生 → 探索主厅 → 发现压力板与石块 → 推石块压实压力板 → 石门升起 → 进入出口厅 → 攀爬石台 → 触碰宝物 → 完成画面

- 移动：WASD（相机相对）、空格跳跃、鼠标环绕第三人称相机
- 攀爬：靠近可攀边缘并向前推 → 自动进入攀爬 → 到达顶点自动登顶
- 交互：推动石块（刚体推挤）、压力板（重量触发）、石门（升降 + 碰撞）

### 7.3 Unity 系统模块（全部由 Qoder 用 C# 编写并经 Unity MCP 创建）

| 模块 | 脚本 | 职责 |
|---|---|---|
| 角色控制 | ThirdPersonController | 移动/转向/跳跃/重力（CharacterController） |
| 相机 | CameraFollow | 环绕跟随 + 简单遮挡处理 |
| 攀爬 | ClimbSystem | 射线检测可攀面 → 攀爬状态机 → 登顶 |
| 机关 | PushBlock / PressurePlate / StoneDoor | 推石块、压力板重量检测、门升降与碰撞 |
| 目标与 UI | GoalTrigger / SimpleUI | 完成触发、目标提示、完成面板 |

## 8. 资产清单与规范（Blender 侧）

### 8.1 资产清单

| 类别 | 资产 | 备注 |
|---|---|---|
| 环境套件 | 地面砖块（带破损）、墙体、石柱（完好/破损）、拱门、台阶、门框、火盆 | 模块化复用 |
| 机关 | 压力板、可推石块、石门 | 与灰盒尺寸一致 |
| 道具 | 祭坛、发光宝物；可选：陶罐、藤蔓 | 宝物可发光材质 |
| 主角 | 风格化低模探险者（3-6k 三角面） | 简易人形骨架 + 自动权重 |
| 动画 | idle / walk / run / jump / climb | 程序化关键帧，简洁风格 |

### 8.2 技术规范

- 比例：1 单位 = 1 m；导入导出前应用缩放
- 导出：FBX（Y-up），带动画角色含 Armature；静态资产可 GLB
- 命名：`SM_`（静态网格）/ `SK_`（骨骼网格）/ `M_`（材质）/ `A_`（动画）
- 面数：静态资产几百~几千面；主角 3-6k
- 材质：程序化 PBR 参数为主（基色/粗糙度/金属度），控制贴图复杂度
- 碰撞：Unity 侧用简单 Collider 近似（Box/Capsule），复杂网格不做精确碰撞

## 9. 验证方式

| 阶段 | 验证手段 |
|---|---|
| M0 | 双端「列出场景对象」+ 双端截图 |
| M1 | 双端截图 + Unity 中资产比例正确 |
| M2/M3/M4 | 用户实机试玩（操作清单逐项打勾） |
| M5 | 完整游玩 3-5 分钟；Console 无报错；（可选）exe 可运行 |
| 全程 | `docs/milestones/` 留证据截图；每阶段本地 git commit |

## 10. 风险与对策

| 风险 | 概率 | 对策 |
|---|---|---|
| Blender 5.2 与 MCP/插件不兼容 | 中 | 加装官方 4.5 LTS 共存切换 |
| Unity MCP 对 6.3 适配问题 | 低 | 换 IvanMurzak/Unity-MCP；最后手段：直接写 C# 文件 + Unity CLI 批处理执行 |
| FBX 轴向/缩放错乱 | 中 | 固定导出预设（apply scale、Y-up）+ 导入后截图验证 |
| 主角绑骨/动画质量不达预期 | 高 | 预期管理：风格化简洁动画；降级方案：简化姿态动画，优先玩法完整 |
| MCP 断连 / 端口冲突（9876） | 中 | 单实例运行；断线重启对应端并重连；小步脚本执行 |
| GUI 进程 PATH 缺失导致 uvx 找不到 | 中 | mcp.json 中 uvx 使用全路径 |
| Unity 工程体积/构建失败 | 低 | 标准 .gitignore；构建问题单独排查 |

## 11. 范围外（Out of Scope）

- 「AI游戏开发工作站」（GameDevMCP-Studio，桌面 docx 项目）— 下一方向，另行立项
- 写实画质、多关卡、战斗系统、存档系统 — 垂直切片验证后再评估
- 云端文生 3D（Hyper3D/Tripo 等）— 默认不使用，保持全本地免费链路
- 音效正式制作 — 仅占位

## 12. 后续步骤

1. 用户评审本文档（本步骤）
2. 调用 writing-plans 技能，将 M0-M5 拆解为可执行实施计划
3. 用户下达 M0 开工指令后，开始实施
