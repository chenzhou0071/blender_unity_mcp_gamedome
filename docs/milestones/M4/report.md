# M4 报告：主角资产替换（Tripo 高模 + 绑骨 + 程序化动画 + Unity 导入）

## 阶段状态

| 任务 | 状态 | 说明 |
|---|---|---|
| M4-1 程序化骨架 + 权重 | 已被取代 | 被 Tripo 高模重建方案取代（历史记录见 c20e097） |
| M4-2 Tripo 高模重拓扑 + 绑骨 | 完成 | 含肩关节解剖修正（24c7f6d） |
| M4-3 五段程序化动画 | 完成 | idle/walk/run/jump/climb（59bee1f） |
| M4-4 FBX 导出 + Unity Humanoid 导入 | 完成 | 本文档 |
| M4-5 Animator 接线与实机验证 | 完成（自检 ✓ + 实机反馈修复迭代 ✓，待复验） | 本文档 |

## M4-4 产物

- Blender 导出：`blender_assets/export/characters/SK_Explorer.fbx`（12.16MB，4K 贴图内嵌）
- Unity 资产：`game/3D-Demo/Assets/Art/Characters/SK_Explorer.fbx`
- 导入配置：`game/3D-Demo/Assets/Editor/HeroImporter.cs`（AssetPostprocessor，自动 Human rig）
- 菜单工具：`Demo/打印主角动画片段`（HeroClipPrinter，打印 clip 名/时长）

## 验证结果

- Rig：Humanoid（Unity 6.3 枚举成员名为 `ModelImporterAnimationType.Human`，旧版为 Humanoid）
- Avatar：`SK_ExplorerAvatar` isHuman=true isValid=true
- AnimationClips（M4-5 按此名加载）：

| clip 名 | 长度 | 帧率 | 对应 Blender Action |
|---|---|---|---|
| A_Idle | 2.000s | 30 | A_Idle（60f） |
| A_Walk | 0.900s | 30 | A_Walk（27f） |
| A_Run | 0.667s | 30 | A_Run（20f） |
| A_Jump | 0.900s | 30 | A_Jump（27f） |
| A_Climb | 1.200s | 30 | A_Climb（36f） |

- 菜单打印输出：`[HeroClip] total 5 clips; loaded objects=66` ✓

## M4-5 产物与验证

### 产物
- `game/3D-Demo/Assets/Editor/AnimatorSetup.cs`：菜单 `Demo/生成玩家 Animator`（生成控制器）+ `Demo/接线主角到玩家`（场景接线，幂等可重跑）
- `game/3D-Demo/Assets/Animations/ExplorerAnimator.controller`：参数 speed/grounded/climbing/jump；状态 Idle/Walk/Run/Jump/Climb
- `game/3D-Demo/Assets/Scripts/ThirdPersonController.cs`：追加 SyncAnimator 同步段 + 跳跃 trigger
- 场景 Demo.unity：Player 下新增 `Hero` 子对象（FBX 实例：scale 1.7、脚底校准 localY=0.81、朝向 0°=导入即面朝 +Z）；灰盒 `Visual` 隐藏

### 状态机接线

| 转换 | 条件 |
|---|---|
| Idle↔Walk | speed >0.1 / <0.1 |
| Walk↔Run | speed >3.25 / <3.25 |
| Idle/Walk/Run→Jump | jump trigger |
| Jump→Idle | 播完（exitTime 0.85） |
| Idle/Walk/Run↔Climb | climbing bool |

（相比计划补充了 Run→Jump、Run→Climb 两条转换）

### 技术自检（手动推进 Animator 逐态验证）
```
推进0.3s: Hips.dy=0.00051  Arm.rotDelta=0.874度   ← 动画驱动骨骼
speed=5  Run?True    speed=2  Walk?True    speed=0  Idle?True
climb=true  Climb?True    climb=false  Idle?True    jump  Jump?True
```
全部通过 ✓；动画循环设置（Idle/Walk/Run/Climb=Loop，Jump=单次）已验证 ✓

### 待用户实机验收（Play Mode 清单）
1. 站立：呼吸待机动画
2. 走/跑：动画随速度切换
3. 跳跃：播放跳跃动作
4. 贴墙攀爬：播放攀爬动画、登顶恢复正常
5. 整体无明显滑步/穿插（可接受简化，记录）

### 实机反馈修复迭代（用户验收反馈 4 项）

| # | 问题 | 根因 | 修法 |
|---|---|---|---|
| 1 | 按 W 移动时角色面朝不对 | 模型导入朝向实测为 +Z，初版 -90° 旋转把脸转到了侧向 | localRot 改为 identity（实测肩轴前向 fwdAngY=0.0） |
| 2 | 人物无颜色（灰白） | `embed_textures=True` 内嵌贴图 Unity 无法提取（材质 mainTex=NULL） | 改 `embed_textures=False` + 贴图落盘 PNG 外置引用；Refresh+重导后自动绑定（2048²） |
| 3 | 站立时悬浮空中 | bind 包络最低点 ≠ Idle 站姿真实脚底（差 15.3cm） | BakeMesh 逐顶点实测 Idle 脚底，localY 0.963→0.81（worldMinY 0.163→0.0102） |
| 4 | 攀爬高台太矮 | 设计高度 3m | ClimbableLedge 加高到 3.75m（LedgeCenter.y=1.875、LedgeSize.y=3.75；Altar→4.25、Treasure→5.15 联动），场景对象与 LevelSpec 常量已同步 |
| 5 | 站上高台仍悬空约 0.75m | 行 4 加高只改了碰撞/逻辑，台面视觉件（7 石墙+6 地砖）仍是旧 3m 设计 | 石墙沿 localScale.z 拉伸、地砖上移，顶面补齐至 3.75m=碰撞面；实机站台 player.y=3.795（=碰撞顶+0.045）✓ |
| 6 | 跑步动画不触发 | Walk↔Run 双阈值 4.5 高于跑速上限 4，Run 永远不可达 | 双阈值改为 3.25（走 2.5/跑 4 之间）；文件/资产导入/实机（speed=4 成功切入 Run）三层验证 ✓ |

验证数据：`fwdAngY=0.0（面朝 +Z）  worldMinY=0.0102（贴地）`
实拍证据：`m45_fix_gameview.png`（游戏视角：背影朝场景深处、脚踩地有影）、`m45_fix_front.png`（正面：色彩/贴地/站姿）

## 备注

- 实际 Unity 工程路径为 `game/3D-Demo/Assets/...`（计划文档写 `game/Assets/...`，少一层目录）
- 模型尺寸约 1.06m 高（垂臂姿势渲染 bounds），M4-5 接入场景时核查缩放适配
- FBX 导入带 animation import warnings 提示（详情未暴露于 Unity API）；鉴于 Avatar 有效、clips 时长全部正确，判定为无害提示，以 M4-5 实机播放为最终复核
- 关键导出参数：`bake_anim_use_nla_strips=True`（NLA 逐轨导出为 clip）、`path_mode='COPY' + embed_textures=False`（贴图外置引用；packed 贴图需先在 Blender 落盘为 PNG——`embed_textures=True` 内嵌贴图 Unity 无法提取，会导致材质丢贴图）
- 编辑器失焦冻结为 Unity 编辑器交互模式（Interaction Mode=Focused，默认）行为：窗口失焦时游戏循环不推进，影响自动截图；已改用"手动推进 Animator"完成状态机/骨骼驱动验证。用户实机 Play 时窗口聚焦，不受影响
- 脚底校准必须用"动画站姿实测"（BakeMesh 逐顶点）而非导入 bind 包络：本例 bind 最低点与 Idle 站姿脚底差 15.3cm，按 bind 校准会悬浮
- 模型导入朝向以实测为准（左右肩轴/脚趾方向 + 渲染对照），FBX 轴转换的纸面推导不可靠
