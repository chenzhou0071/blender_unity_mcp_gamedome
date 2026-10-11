# 古墓探索 · 3D Demo（Blender MCP × Unity 管线）

一个以"AI 全流程驱动"方式制作的 3D 游戏 demo：**程序化建模/绑定/动画（Blender）→ 灰盒玩法 → 正式资产替换 → 氛围与音效打磨（Unity）**——全程通过 Blender MCP + Unity MCP 以代码完成，可复现、可重跑。

## 玩法（约 3~5 分钟）

出生 → 探索遗迹 → 推石压机关 → 石门开启 → 攀爬高台 → 取得圣物。

| 操作 | 键位 |
|---|---|
| 移动 | WASD |
| 视角 | 鼠标 |
| 跑步 | Shift（按住） |
| 跳跃 | 空格 |
| 攀爬 | 面向可攀墙体前推（自动触发） |
| 退出 | Esc |

## 目录结构

| 路径 | 内容 |
|---|---|
| `blender_assets/scripts/` | Blender 端程序化资产脚本（场景 Kit、主角绑定/动画） |
| `game/3D-Demo/` | Unity 工程（Unity 6 + URP），主场景 `Assets/Scenes/Demo.unity` |
| `tools/` | 辅助工具（音效生成/校准等脚本） |
| `docs/superpowers/` | 设计文档与实施计划（specs / plans） |
| `docs/milestones/` | M0~M5 里程碑报告与验收截图（M5 为最终交付报告） |

## 如何运行

1. 用 **Unity 6（6000.3.21f1）** 打开 `game/3D-Demo` 工程；
2. 打开场景 `Assets/Scenes/Demo.unity`，点击 **Play**；
3. 打包：`File → Build Profiles`（Windows x64）自行构建；本地产物不入库。

## 如何重新生成资产

| 端 | 入口 | 说明 |
|---|---|---|
| Blender | `blender_assets/scripts/temple_kit.py` | 场景 Kit：程序化建模 → FBX 导出 |
| Blender | `blender_assets/scripts/hero_rig_v4.py` → `hero_anims.py` | 主角：绑定 → 走/跑/跳/攀爬动画 → 导出 |
| Unity 菜单 | `Demo/构建灰盒关卡` | 从零重建灰盒关卡（含机关/触发/UI） |
| Unity 菜单 | `Demo/用正式资产替换灰盒` | 灰盒 → 正式资产替换（KitPlacer） |
| Unity 菜单 | `Demo/生成玩家 Animator` / `Demo/接线主角到玩家` | 主角动画状态机生成与落地 |
| Unity 菜单 | `Demo/接线音效` | 音效资产接线到场景 |
| Unity 菜单 | `Tools/M5/Setup Atmosphere` | 火光闪烁 + Bloom 氛围配置 |

> Blender 脚本通过 Blender MCP 执行，亦可 `blender --background --python <脚本>` 复现。

## 里程碑状态

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 环境部署与连通（Blender + Unity 双 MCP） | ✅ |
| M1 | 最小链路验证（Blender → FBX → Unity） | ✅ |
| M2 | 灰盒玩法闭环（移动/攀爬/机关/UI） | ✅ |
| M3 | 场景资产替换（程序化 Kit） | ✅ |
| M4 | 主角资产与动画（绑定/动画状态机） | ✅ |
| M5 | 打磨与交付（音效/氛围/性能/终验） | ✅ |

> M5 中「UI 扩展（操作说明/完成面板）」为可选任务未做；打包方式为手动构建（未提供打包脚本）。

## 文档索引

- 设计文档：`docs/superpowers/specs/2026-10-08-3d-game-demo-design.md`
- 实施计划：`docs/superpowers/plans/2026-10-08-3d-game-demo-milestones.md`
- M5 交付报告：`docs/milestones/M5/report.md`
