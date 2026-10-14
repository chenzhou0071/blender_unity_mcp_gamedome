# 古墓探索 · 3D Demo（Blender MCP × Unity 管线）

一个以"AI 全流程驱动"方式制作的 3D 游戏 demo：**程序化建模/绑定/动画（Blender）→ 灰盒玩法 → 正式资产替换 → 氛围与音效打磨 → 户外探险扩展（Unity）**——全程通过 Blender MCP + Unity MCP 以代码完成，可复现、可重跑。

## 玩法（约 8~10 分钟）

神庙内出生 → 探索遗迹 → 推石压机关 → 石门开启 → 攀爬高台 → 取得圣物 → **走出神庙，潜入峡谷**：草原穿行 → 蹲行钻过岩缝 / 挥刀斩断挡路的藤帘 → 游过河谷 → 在断崖南岸抓住斜绳横越深渊 → 登上崖顶遗迹 → 抵达终点「序章完成 · 你走出了峡谷」。

| 操作 | 键位 |
|---|---|
| 移动 | WASD |
| 视角 | 鼠标 |
| 跑步 | Shift（按住） |
| 跳跃 / 爬绳中松手 | 空格 |
| 攀爬 / 爬绳 | 面向可攀墙体或绳索前推（自动触发） |
| 蹲行 | C（岩缝段需蹲行通过，站姿会被挡） |
| 挥刀 | 鼠标左键（斩断藤帘） |
| 游泳 | 走进深水自动切换 |
| 退出 | Esc |

## 目录结构

| 路径 | 内容 |
|---|---|
| `blender_assets/scripts/` | Blender 端程序化资产脚本（场景 Kit、峡谷地形、户外道具、主角绑定/动画） |
| `game/3D-Demo/` | Unity 工程（Unity 6 + URP），主场景 `Assets/Scenes/Demo.unity` |
| `tools/` | 辅助工具（音效生成/校准等脚本） |
| `docs/superpowers/` | 设计文档与实施计划（specs / plans） |
| `docs/milestones/` | M0~M6 里程碑报告与验收截图（M6 为户外扩展一期） |

## 如何运行

1. 用 **Unity 6（6000.3.21f1）** 打开 `game/3D-Demo` 工程；
2. 打开场景 `Assets/Scenes/Demo.unity`，点击 **Play**；
3. 打包：`File → Build Profiles`（Windows x64）自行构建；本地产物不入库。

## 如何重新生成资产

| 端 | 入口 | 说明 |
|---|---|---|
| Blender | `blender_assets/scripts/temple_kit.py` | 神庙场景 Kit：程序化建模 → FBX 导出 |
| Blender | `blender_assets/scripts/temple_rebuild.py` | 神庙重做（金字塔外壳 + 房间内装 + 火把） |
| Blender | `blender_assets/scripts/canyon_terrain.py` | 峡谷地形（草原/岩缝/河谷/深渊/崖顶） |
| Blender | `blender_assets/scripts/outdoor_props.py` | 户外道具（岩缝巨石/藤帘/水面/斜绳/锚桩） |
| Blender | `blender_assets/scripts/hero_rig_v4.py` → `hero_anims.py` | 主角：绑定 → 移动/攀爬/游泳/挥砍动画 → 导出 |
| Blender | `blender_assets/scripts/hero_props.py` | 主角佩刀等道具资产 |
| Unity 菜单 | `Demo/重建神庙` | 从零重建神庙（M6 重做版）+ 出口衔接 |
| Unity 菜单 | `Demo/构建户外场景` | 峡谷全境重建（地形/岩缝/藤帘/水面/绳索/雾层/崖顶遗迹/终点） |
| Unity 菜单 | `Demo/散布植被` | 草原植被散布 |
| Unity 菜单 | `Demo/户外氛围` | 天空/太阳/雾/后处理 + 室内外光照过渡 |
| Unity 菜单 | `Demo/构建灰盒关卡` | （M2 存档）从零重建灰盒关卡（含机关/触发/UI） |
| Unity 菜单 | `Demo/用正式资产替换灰盒` | （M3 存档）灰盒 → 正式资产替换（KitPlacer） |
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
| M6 | 户外探险扩展一期（峡谷地形/蹲行岩缝/砍藤/游泳/爬绳/崖顶遗迹+终点） | ✅ |

> M6 为一期收尾范围：计划中的火盆检查点（Task 18）、血条/摔伤/死亡重生、ESC 菜单与打磨项（M6-7/M6-8）未做，留待后续期。M5 中「UI 扩展（操作说明/完成面板）」为可选任务未做；打包方式为手动构建（未提供打包脚本）。

## 文档索引

- 设计文档（基础版）：`docs/superpowers/specs/2026-10-08-3d-game-demo-design.md`
- 设计文档（户外扩展）：`docs/superpowers/specs/2026-10-11-adventure-expansion-design.md`
- 实施计划（基础版）：`docs/superpowers/plans/2026-10-08-3d-game-demo-milestones.md`
- 实施计划（户外扩展）：`docs/superpowers/plans/2026-10-11-adventure-expansion-m6.md`
- 里程碑报告：`docs/milestones/M1 ~ M5/report.md`（M5 为交付报告）
- 验收截图：`docs/milestones/M6/`（峡谷/神庙/岩缝/藤帘/水面/斜绳+雾/爬绳/遗迹/终点）
