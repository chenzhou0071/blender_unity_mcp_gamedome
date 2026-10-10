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

### M4-8 反馈修复迭代（用户验收反馈 6 项，第 4 项暂缓）

| # | 问题 | 根因 | 修法 |
|---|---|---|---|
| 1 | 左肩左突、骨架弯曲靠左 | Tripo 网格左臂天生比右臂胖/高（骨头 ±0.115/0.306 对称、权重近对称，高亮渲染定位到左臂皮肤鼓包 + 背带被顶起）；旋转补偿不可修（delt/cap 恒残留 +5.5~7.1mm） | 镜像对称化手术：左臂 9577 顶点（臂链权重 w>0.03）向镜像右臂表面 4-近邻反距离加权对齐（alpha=0.9·smoothstep）；垂臂切片 dy +6.5~11.8mm→+0.3~1.8mm，右臂逐位未动，镜像残差中位 1.4mm；备份 `hero_rigged_pre_armsym.blend` |
| 2 | 走/跑"太快" | 播放率配小步幅（walk 28°/1.79、run 48°/1.29） | 步幅加大 walk 28°→33°、run 48°→58°；播放率 walk 1.79→1.5、run 1.29→1.35（5m/s 零滑步 1.41，容忍 ~5% 微滑步换低频观感）；runSpeed 4→5、Walk↔Run 阈值 3.25→3.75（2.5/5 中点） |
| 3 | 爬顶不"翻上"、还是爬 | 无翻越动画，到顶后爬升动画硬切 | 新增 A_Mantle（26f/0.867s 一次性：悬挂→拉引→撑压→跨腿→站直）；ClimbSystem topOutDuration 0.45→0.85、暴露 IsToppingOut；Animator 加 toppingOut 参数 + Climb→Mantle→Idle；HeroImporter loop 排除 Mantle |
| 3b | 撑压手"竖着撑"怪（复审） | 旧版大臂前外平伸+前臂垂直下折 = 肘顶在体前的 L 形怪姿 | 翻越 K 表重做手臂段：f9 翻腕平伸（手掌翻压台沿、手臂水平前伸）→ f10 手臂伸向前下压撑（手在体前下 0.29/0.36m）→ f14 身体越沿转体侧下撑；侧/正视逐帧验证（`mantle_arc_check.png`/`mantle_arc_check_front.png`），翻转路径无绕路 |
| 4 | 推石抽搐 | 顶推交互 | 暂缓（后期改"抱石头"承接，M5） |
| 5 | 跳跃手从后往前"绕"摆 | f4→f9 大角度旋转欧拉插值抄近路绕体侧 | jump K 表加 2 中间帧（f7 双臂经正下方、f12 前上回落）锁矢状面钟摆弧线；侧/正视逐帧渲染验证（`jump_arc_check.png`/`jump_arc_check_front.png`），无横向外展 |
| 6 | 石门旁门框柱无碰撞 | 门框/拱门用 Spawn（纯视觉） | 改 SpawnSolid（按 MeshFilter 挂 MeshCollider），重跑 `Demo/用正式资产替换灰盒` 应用 |

本轮附加：AnimatorSetup.cs 补齐 `walk.speed/run.speed` 显式赋值（此前为手改 controller 值，重跑菜单会回退）；Walk↔Run 阈值写入生成器同步 3.75。

### M4-9 反馈修复迭代（第二轮实机反馈 4 项 + 速度分层方案）

| # | 问题 | 根因 | 修法 |
|---|---|---|---|
| 1 | 跳跃挥臂太快 | 蓄力/挥臂段各仅 5f（0.167s），且物理"按下即离地"与动画蓄力段错位 | K 表重排 0,7,10,14,17,21,27（蓄力/挥臂各 0.233s，慢 40%）；ThirdPersonController 加 0.26s 起跳前摇（蹲→蹬→离地时序对齐，蓄力中走落则放弃起跳）；侧/正视验证无绕路，Unity 曲线极值 0.467s=f14 ✓ |
| 2 | 跑步动画快 | **场景 Player 实例 runSpeed 序列化值=4**（M4-8 只改脚本默认 5，未同步场景实例），而播放率按 5m/s 调优 → 速度/播放双重错配 | 用户拍板速度分层：走路 2.5→**1.5m/s**（散步）配播放率 **0.9**（动画原速以下悠闲步伐）；跑步 5→**3.5m/s** 配播放率 **1.0**（零滑步原速点——动画设计节奏直出，不再被加速放大）；场景实例同步（1.5/3.5）、阈值 3.75→2.5；run 动画 Hips 起伏 0.05→0.08 强化弹跳浮空感 |
| 3 | 翻越动作太晚（人都上去了才翻） | 到顶检测须等头部越过台顶（距台面 1.7m）才触发 | 贴墙爬升中每帧主动探测台面（起点脚+3.0、向下 3.5m），距台面 <2.2m（=手举起恰好触及台沿，与 A_Mantle f0 抓沿姿态物理对齐）即触发翻越；原"头顶墙消失"路径保留为保底（防探测被场景几何干扰时卡死） |
| 4 | 高台视觉又变矮 | M4-5 手动加高未写进生成器，M4-8 重跑菜单 CleanupOld 覆盖回 3m | KitPlacer 石台段等高重写：`LedgeTop=4.5` 常量派生（墙段纵向缩放 1.4925/地砖 y=4.2/祭坛 4.5/宝物 5.5）；LevelSpec 灰盒同步 4.5（LedgeCenter.y=2.25、AltarPos=5.0、TreasurePos=5.9）；场景对象同步并保存 |

验证数据：`colTop=4.500（碰撞顶=墙段顶=地砖顶）  PLAYER move=1.5/run=3.5  Walk.speed=0.9/Run.speed=1.0  宝物视觉件 worldY=5.5/祭坛 4.5`；A_Jump 左臂曲线极值 0.467s（旧版 0.300s）确认新节奏已导入 ✓

流程教训：① 场景实例的序列化字段不会跟随脚本默认值更新（runSpeed 4→5 失效案例），改默认值后必须手动同步场景实例并保存；② 生成器菜单与灰盒的先后依赖——"替换资产"须在灰盒位置就位后运行（挂载型视觉件按当时相对位置定位，如宝物挂 Treasure 下）；③ 生成器菜单在 Play Mode 下场景操作无效（退出播放后重跑）。

备注：台高 4.5m 后站台上（人 1.7+4.5=6.2m）高于 B 厅北墙（5.88m），台上视野可能越过墙顶看到场景边界；若实机穿帮，下一轮把 B 厅墙加第三层。

### M4-10 反馈修复迭代（第三轮实机反馈 2 项）

| # | 问题 | 根因 | 修法 |
|---|---|---|---|
| 1 | 跳跃挥臂太快、改了"没变化" | 上轮 K 表 f7→f14 中真正的核心挥臂段（正下→前上）只跨 f10→f14=0.133s，肉眼不可感；clip 引用无问题（Unity 曲线极值 0.467s=f14 已证新版在播） | K 表重排 0,6,9,18,21,24,27：挥臂 f9（正下）→f18（前上峰值）=**0.3s**（对旧核心段 2 倍多），f12/f15 两个中间帧显式定义推进节奏；侧/正视 12 帧验证三帧递进、贴合矢状面 |
| 2 | 翻越"像跳"，应为"弯腰→撑地→膝盖上来→站立" | 双根因：①**场景实例 topOutDuration=0.45**（M4-8 只改代码默认 0.85 未同步场景实例，又踩序列化值坑）——物理 0.45s 内弹上 2.2m（峰值 ~9m/s）=瞬弹感；②旧动画姿态近直立引体式，无弯腰俯身读感 | 物理：代码默认 1.0 + 场景实例同步 **1.0**（BEFORE 0.45→AFTER 1.00 实证）、上升比例 0.55→0.62（对齐动画撑台段节奏）；动画：**A_Mantle 完全重做 30f/1.0s**（悬挂→引体→翻肘→弯腰俯身 42°→提膝跪台→蹬起→站直，单膝上法），时长与物理对齐；侧/正视 12 帧验证弯腰弧线与提膝路径 |

验证数据：`A_Mantle dur=1.000s（旧 0.867s）  controller.Mantle=1.000s  A_Jump/A_Mantle loop=False  topOutDuration 场景实例 1.00`；`mantle_arc_check.png`（侧视：f10-f16 背拱 42° 弯腰、f16-f18 提膝上台）+ `mantle_arc_check_front.png`（正视：手臂贴身前正中面）；`jump_arc_check.png`（侧视：f12 半举→f15 前上→f18 峰值）+ `jump_arc_check_front.png`（正视：无横向外展）✓

环境事故：EEVEE 在本机 NV 驱动下 headless 渲染必崩（最小复现：空场景 64px 渲染即崩 `nvoglv64 EXCEPTION_STACK_OVERFLOW`），三个渲染脚本（主脚本 + 两个轨迹检查）统一切 **CYCLES CPU**（32 采样；560-640px 约 3s/帧），渲染链路恢复。

流程教训升级：场景实例序列化值坑**第二次踩**（M4-9 runSpeed=4、本轮 topOutDuration=0.45）——改任何 MonoBehaviour public 默认值后，必须用 execute_code 同步场景实例并 SaveScene（已固化为发布前检查项）。

### M4-11 反馈迭代（跑跳专门动作 + 空中锁速）

| # | 需求 | 方案 | 实现 |
|---|---|---|---|
| 1 | 跑步跳跃要有专门"跑跳"动作 | 走跳保留 A_Jump（反馈"走路跳还行"）；跑步起跳切 A_JumpRun | 新增 **A_JumpRun 28f/0.933s** 单脚蹬地跨步式：蹬地→蹬伸离地→左腿前跨高抬(-72°)→落地缓冲→恢复跑姿；躯干前倾 16-22°、摆臂异侧平衡；Animator 加 JumpRun state：Run→JumpRun（jump trigger）、JumpRun→Run（exitTime 0.85≈物理落地 0.793s） |
| 2 | 跑跳要更远 | 无需改物理——距离=速度×滞空：走跳 1.5×0.693≈1.0m vs 跑跳 3.5×0.693≈2.4m 物理已自动更远 | 仅确认，未改跳跃参数 |
| 3 | 跑跳前摇 0.1s（拍板） | 走路/立定跳保持 0.26s；跑跳 0.1s 对齐 A_JumpRun f3 蹬伸（跑步中不打断节奏） | ThirdPersonController：`const runJumpDelay=0.1f` + `jumpIsRun` 档位判定（有输入且 speed>2.5） |
| 4 | 跑跳离地后锁定水平速度（拍板） | 空中惯性：按下瞬间记录起跳冲量，离地启用；松键不空中急停、不空中转向 | 按下瞬间 `airVel=dir*speed`+`jumpIsRun`；离地 `airLocked=true`；空中 move.x/z=airVel 覆盖 + 跳过转向 Slerp；解除条件 `grounded && velocityY<=0`（避开离地帧 grounded 缓存 true+vy>0 误清）；攀爬接管清锁 |

验证数据：`A_JumpRun range=(0.0,28.0) fcurves=132`（重建日志）；FBX 8947900B 导入后 7 段 clips 全齐（**A_JumpRun 0.933s loop=False**，HeroImporter "Jump" 排除规则自动覆盖）；controller：`JumpRun state=A_JumpRun、Run→JumpRun [jump:If]、JumpRun→Run exit=0.85 dur=0.10、Walk 0.9/Run 1.0 保持`；`jumprun_arc_check.png`（侧视 12 帧：f0 蹬地→f3 蹬伸→f8-f12 左腿前跨腾空→f20-f25 触地缓冲→f28 恢复跑姿）+ `jumprun_arc_check_front.png`（正视：跨步开合、摆臂异侧上扬）✓

本轮事件与修正：
1. 主脚本首跑崩于循环闭合断言：一次性动作 A_JumpRun 被误报 loop gap 0.26（首尾不闭合是设计——落地接 Run 融合）→ 豁免名单 `("A_Mantle","A_JumpRun")`。
2. **场景 Hero 的 controller 引用断裂**：AnimatorSetup.Setup 用 DeleteAsset+CreateAtPath 重建 controller 后 GUID 变更，场景引用变 NULL → 跑"接线主角到玩家"（幂等）修复，Hero ctrl/avatar/rootMotion 全量复验 ✓。新检查项：自此每次重跑"生成玩家 Animator"后必须验证场景 Hero 的 ctrlRef 非空。
3. 相机朝向历史误标修正：world_to_camera_view 实证侧视相机 (0,2.3,0.85) 下 **+X→screen_x=-0.411（画面左）**，此前脚本注释"角色面朝图右"应为"图左"（3 个 check 脚本注释已改）；历史验证结论不受影响（对称动作判读与朝向无关）。
4. 场景序列化值坑**零新增**（M4-11 新参数全部 const/private：runJumpDelay 为 const、airLocked/airVel/jumpIsRun 为 private 非序列化）——无场景同步项，从源头规避第三次踩坑。

## 备注

- 实际 Unity 工程路径为 `game/3D-Demo/Assets/...`（计划文档写 `game/Assets/...`，少一层目录）
- 模型尺寸约 1.06m 高（垂臂姿势渲染 bounds），M4-5 接入场景时核查缩放适配
- FBX 导入带 animation import warnings 提示（详情未暴露于 Unity API）；鉴于 Avatar 有效、clips 时长全部正确，判定为无害提示，以 M4-5 实机播放为最终复核
- 关键导出参数：`bake_anim_use_nla_strips=True`（NLA 逐轨导出为 clip）、`path_mode='COPY' + embed_textures=False`（贴图外置引用；packed 贴图需先在 Blender 落盘为 PNG——`embed_textures=True` 内嵌贴图 Unity 无法提取，会导致材质丢贴图）
- 编辑器失焦冻结为 Unity 编辑器交互模式（Interaction Mode=Focused，默认）行为：窗口失焦时游戏循环不推进，影响自动截图；已改用"手动推进 Animator"完成状态机/骨骼驱动验证。用户实机 Play 时窗口聚焦，不受影响
- 脚底校准必须用"动画站姿实测"（BakeMesh 逐顶点）而非导入 bind 包络：本例 bind 最低点与 Idle 站姿脚底差 15.3cm，按 bind 校准会悬浮
- 模型导入朝向以实测为准（左右肩轴/脚趾方向 + 渲染对照），FBX 轴转换的纸面推导不可靠
