# 古墓丽影风格 3D Demo 一期（M6-1 ~ M6-8）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **执行规则（用户约定，优先于流程默认）**：里程碑制——**每个里程碑的全部任务完成后停下汇报，等用户确认后再继续下一个里程碑**；用户未下达"开工"指令前不启动任何任务。

**Goal:** 在现有神庙 demo 基础上扩展出一期"最小完整循环"：神庙石门→下行台阶→草原→蹲行岩缝→挥刀砍藤→游泳过河→爬绳上崖→崖顶遗迹终点（含血条/摔伤/检查点重生/ESC 菜单）。

**Architecture:** 户外场景采用"地形高度场 + Kit 复用 + 植被散布"三段式：Blender 程序化生成峡谷地形 FBX（含七段剖面），Unity 侧 `OutdoorBuilder.cs` 作为户外场景唯一构建器（仿 `KitPlacer` 的幂等摆放模式）增量扩展 Demo.unity；移动四能力（蹲/泳/绳/刀）以"独立组件 + ThirdPersonController 状态扩展 + Animator 参数接线"模式实现，复用 ClimbSystem 的接管/吸附写法。

**Tech Stack:** Blender 4.x headless（bpy/bmesh/mathutils——程序化资产生成）、Unity 6000.3.21f1 URP（旧 Input Manager、CharacterController、Animator StateMachine API）、blender MCP + unityMCP（验证/截图/断言）、Git。

## Global Constraints

- **Unity 版本**：6000.3.21f1（URP）；**不得**引入新输入系统包（Input System）——全部沿用旧 `Input.GetAxisRaw / GetKey / GetKeyDown / GetMouseButtonDown`
- **输入键位**（spec 定稿）：WASD 移动 / 鼠标视角 / LeftShift 跑 / 空格跳 / C 蹲（切换式）/ 鼠标左键挥刀 / ESC 暂停菜单 / 攀爬与抓绳=朝向前进键自动触发
- **Player 基线**（不可破坏）：CharacterController `height=1.8, radius=0.3, center=(0,0.9,0)`；Hero 模型挂 `Player/Hero`（localScale 1.7，localPos y=0.81，脚底对齐原点）；动画只加不减——现有 7 段 clip（A_Idle/Walk/Run/Jump/JumpRun/Climb/Mantle）全部保留
- **资产管线**：全部程序化——Blender headless 脚本生成 → 导出 FBX 到 `blender_assets/export/<组>/` → 拷贝到 `game/3D-Demo/Assets/Art/Static/<组>/` → Unity 重新导入；**不下载任何第三方模型/贴图**
- **命名规范**：网格 `SM_` / 材质 `M_` / 视觉实例 `VIZ_` / 户外场景对象 `OUT_`；材质数值沿用 `temple_kit.py` 的 MATERIALS 字典风格（color/rough/emission）
- **静态批处理规则（M5 教训，必须遵守）**：标记 `BatchingStatic` 前**沿父链检查**，`StoneDoor/PushBlock/PressurePlate/Treasure` 及一切运行时位移/缩放对象（藤蔓、火盆火焰、绳、终点饰件）**及其子对象一律不标**；新户外静态件（地形/巨石/遗迹件）可以标
- **场景修改纪律**：**不再重跑**「Demo/构建灰盒关卡」（会清空场景）；所有 M6 场景修改走新增的 `Demo/构建户外场景` 菜单（幂等：先清 `OUT_` 前缀对象再重建）；`KitPlacer`（用正式资产替换灰盒）仅在需要重铺室内 VIZ 时运行
- **代码注释**：中文；新特性标记 `M6-x:` 前缀（沿用现有 `M4-x/M5-x` 风格）；公共字段带单位/取值说明
- **验证模式**：无 Unity 单测框架——每个任务用「Blender assert + 渲染截图」或「unityMCP `execute_code` 断言 + Play 截图」验证；断言先写期望值、先跑失败、实现后再跑通过
- **提交粒度**：每个 Task 末尾一次 commit，消息格式 `feat(M6-x): 描述`（中文）
- **性能目标**：打包后户外 ≥60fps（M5-5 采样法：Δ`Time.frameCount`/Δ`Time.realtimeSinceStartup`）；植被用 GPU Instancing（材质开 `enableInstancing`），树/石实体标 BatchingStatic（按父链规则）

---

## 文件结构总览

**新增（Blender 侧）**
| 文件 | 职责 |
|---|---|
| `blender_assets/scripts/canyon_terrain.py` | 峡谷地形高度场生成 + SM_Step 台阶构件；导出 FBX + 渲染顶视/透视验证图 |
| `blender_assets/scripts/outdoor_props.py` | 户外构件：SM_GorgeRock_A/B（岩缝巨石）、SM_Vine_Curtain（藤帘）、SM_Rope + SM_Stake（绳与锚桩） |
| `blender_assets/scripts/hero_props.py` | SM_Knife（主角佩刀） |
| （改）`blender_assets/scripts/hero_anims.py` | 追加 A_CrouchIdle/A_CrouchWalk/A_Slash/A_Swim 四段动画 + EXPECT/断言扩展 |

**新增（Unity 侧）**
| 文件 | 职责 |
|---|---|
| `Assets/Editor/OutdoorBuilder.cs` | 户外场景唯一构建器：地形放置/出口工程/岩缝/藤帘/绳/崖顶遗迹/火盆；菜单 `Demo/构建户外场景`（幂等，先清 `OUT_`） |
| `Assets/Editor/VegetationScatter.cs` | 植被散布器：地形坡度/高程采样 + 抖动格点摆放（草 instancing / 树实体）；菜单 `Demo/散布植被` |
| `Assets/Editor/OutdoorFxSetup.cs` | 户外氛围：天空/太阳/雾/后处理扩展 + 光照过渡 Zone；菜单 `Demo/户外氛围` |
| `Assets/Scripts/Attack.cs` | 左键挥刀：动画触发 + 判定窗扇形检测 + 手骨挂刀 |
| `Assets/Scripts/CuttableVine.cs` | 藤帘：实现斩断（塌落/隐藏 + 音效 + 碰撞移除） |
| `Assets/Scripts/WaterVolume.cs` | 水体积：记录水位供游泳状态读取（Box Trigger） |
| `Assets/Scripts/RopeSystem.cs` | 爬绳：吸附/上下爬/顶翻越/松手（仿 ClimbSystem 结构） |
| `Assets/Scripts/PlayerHealth.cs` | 血量/摔落伤害/死亡重生（接检查点） |
| `Assets/Scripts/CheckpointSystem.cs` | 火盆检查点：走近记录复活点 + 提示 |
| `Assets/Scripts/PauseMenu.cs` | ESC 菜单：暂停/继续/退出（保存与回档灰置） |
| `Assets/Scripts/LightZone.cs` | 室内外光照/雾过渡触发器 |

**修改（Unity 侧）**
| 文件 | 改动 |
|---|---|
| `Scripts/ThirdPersonController.cs` | +蹲行状态机、+游泳状态、+绳态接管分支、+crouch/swim 动画参数 |
| `Scripts/SimpleUI.cs` | +血条、+Flash 提示、+死亡黑幕、+ESC 菜单面板构建 |
| `Scripts/CameraFollow.cs` | +`if (Time.timeScale == 0f) return;`（暂停时冻结视角） |
| `Scripts/AudioManager.cs` | +`Chop() / Splash() / Checkpoint() / Damage()` 音效接口 |
| `Editor/AnimatorSetup.cs` | +参数 crouch/swimming/slash + 状态 CrouchIdle/CrouchWalk/Swim/Slash + 转换 |
| `Editor/AudioWiring.cs` | +新音效 clip 生成/接线（程序合成，沿用 M5-2 模式） |

---

## Milestone M6-1：地形骨架与第一眼

> 里程碑目标：从神庙出门→下行台阶→草原可自由行走；天空/太阳/雾/后处理就位；基础植被铺开。**完成后停下汇报等待确认。**

### Task 1: 峡谷地形生成脚本（Blender）

**Files:**
- Create: `blender_assets/scripts/canyon_terrain.py`
- 产出: `blender_assets/export/outdoor/SM_CanyonTerrain.fbx` + `SM_Step.fbx` + `docs/milestones/M6/terrain_top.png` + `terrain_persp1.png` + `terrain_persp2.png`

**Interfaces:**
- Produces: `SM_CanyonTerrain`——世界坐标已烘焙的地形网格（z 24→254，x ±40，顶点 1.25m 间距）；`SM_Step`——单级台阶（宽 4m×高 0.2m×深 0.6m，原点在底面中心）；材质 `M_Terrain`（岩土棕）、`M_Step_Stone`（石板灰）
- 坐标系约定（后续任务依赖）：神庙 B 房北墙 z=22；户外地形起点 z=24；路径中心线 x=0

- [ ] **Step 1: 写地形脚本（含验证断言）**

```python
"""M6-1: 峡谷地形生成——七段剖面高度场 + 噪声 + FBX 导出。
headless 用法: blender.exe --background --factory-startup --python canyon_terrain.py [-- --render]
段落（沿 +Z 轴，世界坐标已烘焙，Unity 里放置在原点）:
  z  24- 34  出口平台 y=0（接神庙地台）
  z  34- 46  下行坡道 y=0 → -1.5（视觉铺 SM_Step 台阶）
  z  46- 96  草原缓起伏 y≈-1.5±0.6
  z  96-126  岩缝段 y=-1.5 平底（|x|>1.4 升壁 3m，缝顶另摆横石）
  z 126-176  河谷下切（河床 y=-3.5，水面 y=-2.6，宽 18m）
  z 176-194  南岸高台 y=-1.5（深渊边缘可走行；爬绳段起点）
  z 194-208  深渊带（底 y=-32 全黑不可达，坠入即死；斜绳横越其上）
  z 208-216  对岸崖壁（35m 升至崖顶 y=3）
  z 216-254  崖顶平台 y=3（30×30 平坦，smoothstep 收边）
两侧崖壁：|x|>20 渐升 +15~+35（各段参数略不同）；噪声三频叠加（路径带 |x|<3 减半保可走性）。
"""
import bpy, bmesh, random, os, sys, math
from mathutils import Vector, noise

random.seed(11)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(ROOT, "export", "outdoor")
RENDER_DIR = os.path.join(ROOT, "..", "docs", "milestones", "M6")
DO_RENDER = "--render" in sys.argv

X_MIN, X_MAX, Z_MIN, Z_MAX = -40.0, 40.0, 24.0, 254.0
GRID = 1.25                       # 顶点间距（米）

def path_height(z):
    """路径中心线高度（分段线性 + smoothstep 过渡）。"""
    def sstep(a, b, t):
        t = max(0.0, min(1.0, (t - a) / (b - a)))
        return t * t * (3 - 2 * t)
    if z < 34:   return 0.0
    if z < 46:   return -1.5 * sstep(34, 46, z)                  # 出口坡道
    if z < 96:   return -1.5                                      # 草原
    if z < 126:  return -1.5                                      # 岩缝平底
    if z < 176:                                                  # 河谷下切
        k = sstep(126, 140, z) * (1 - sstep(164, 176, z))
        return -1.5 - 2.0 * k                                     # 河床 -3.5 → 回 -1.5
    if z < 194:  return -1.5                                      # 南岸高台（深渊边缘）
    if z < 208:  return -1.5 - 30.5 * sstep(194, 206, z)          # 断崖直落：深渊底 -32（全黑不可达）
    return -32.0 + 35.0 * sstep(208, 216, z)                      # 对岸崖壁 35m 升至崖顶 +3

def wall_height(x, z):
    """两侧崖壁抬升（|x|>20 渐升）。"""
    ax = abs(x)
    if ax < 20: return 0.0
    base = min(35.0, (ax - 20) * 1.4)
    wob = noise.noise(Vector((x * 0.05, z * 0.05, 7.3))) * 6.0    # 崖壁起伏
    return base + wob

def height(x, z):
    h = path_height(z) + wall_height(x, z)
    ax = abs(x)
    mask = 0.35 if ax < 3.0 else (1.0 if ax > 6.0 else 0.65)      # 路径带噪声减半
    h += noise.noise(Vector((x * 0.02, z * 0.02, 1.1))) * 3.0 * mask
    h += noise.noise(Vector((x * 0.08, z * 0.08, 2.2))) * 0.8 * mask
    h += noise.noise(Vector((x * 0.30, z * 0.30, 3.3))) * 0.15 * mask
    return h

def build_terrain():
    nx = int((X_MAX - X_MIN) / GRID) + 1
    nz = int((Z_MAX - Z_MIN) / GRID) + 1
    me = bpy.data.meshes.new("SM_CanyonTerrain")
    verts, faces = [], []
    for j in range(nz):
        z = Z_MIN + j * GRID
        for i in range(nx):
            x = X_MIN + i * GRID
            verts.append((x, height(x, z), z))       # 注意: Unity 为 Y-up，导出时交换见下
    for j in range(nz - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = False
    obj = bpy.data.objects.new("SM_CanyonTerrain", me)
    bpy.context.scene.collection.objects.link(obj)
    return obj
```

- [ ] **Step 2: 补导出/渲染/断言段并 headless 跑**

（脚本后续段：SM_Step 构建 → 材质 → triangulate → 导出（`axis_forward='-Z', axis_up='Y'`，与 temple_kit 相同）→ assert（顶点数 ≈185×65、FBX >20KB、tris ≤ 30k）→ `--render` 时顶视+两个透视渲染到 `docs/milestones/M6/`）

Run: `blender.exe --background --factory-startup --python blender_assets/scripts/canyon_terrain.py -- --render`
Expected: 输出 `OK terrain verts=... tris=... fbx=...B`，三张渲染图生成且 >20KB

- [ ] **Step 3: 人工检查渲染图**

看 `terrain_top.png`（顶视：七段可辨）与透视两张（峡谷两侧壁、河谷下切、对岸崖顶）。**不看图不提交**。

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/canyon_terrain.py docs/milestones/M6/
git commit -m "feat(M6-1): 峡谷地形生成脚本（七段剖面+噪声，FBX导出+渲染验证）"
```

### Task 2: 地形导入 Unity + 碰撞 + 走出神庙验证

**Files:**
- Create: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`
- Copy: `blender_assets/export/outdoor/*.fbx` → `game/3D-Demo/Assets/Art/Static/outdoor/`

**Interfaces:**
- Produces: `OutdoorBuilder`（静态类，菜单 `Demo/构建户外场景`）——后续 Task 3/9/12/15/17 全部在此文件追加段落函数；约定：所有生成对象名以 `OUT_` 开头，重跑时先 `CleanupOUT()`
- Consumes: Task 1 的 FBX（`Assets/Art/Static/outdoor/SM_CanyonTerrain.fbx`）

- [ ] **Step 1: 拷贝 FBX 并确认 Unity 导入**

```bash
mkdir -p game/3D-Demo/Assets/Art/Static/outdoor
cp blender_assets/export/outdoor/SM_CanyonTerrain.fbx game/3D-Demo/Assets/Art/Static/outdoor/
cp blender_assets/export/outdoor/SM_Step.fbx game/3D-Demo/Assets/Art/Static/outdoor/
```

- [ ] **Step 2: 写 OutdoorBuilder 骨架 + 地形放置**

```csharp
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

// M6: 户外场景唯一构建器（幂等：重跑先清 OUT_ 前缀对象）。
// 原则沿用 KitPlacer——地形/FBX 直接实体 + MeshCollider；会动的对象不加静态标记。
public static class OutdoorBuilder
{
    const string FbxDir = "Assets/Art/Static/outdoor";
    const string Scene = "Assets/Scenes/Demo.unity";

    [MenuItem("Demo/构建户外场景")]
    public static void Build()
    {
        EditorSceneManager.OpenScene(Scene, OpenSceneMode.Single);
        CleanupOUT();
        PlaceTerrain();
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[OutdoorBuilder] 户外场景构建完成");
    }

    static void CleanupOUT()
    {
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
            if (go.name.StartsWith("OUT_")) Object.DestroyImmediate(go);
    }

    static GameObject InstantiateFbx(string name, Vector3 pos, Quaternion rot)
    {
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>($"{FbxDir}/{name}.fbx");
        var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        go.name = "OUT_" + name; go.transform.SetPositionAndRotation(pos, rot);
        go.AddComponent<MeshCollider>();               // 静态地形：convex=false 默认
        UnityEditor.GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        return go;
    }

    static void PlaceTerrain() { InstantiateFbx("SM_CanyonTerrain", Vector3.zero, Quaternion.identity); }
}
```

- [ ] **Step 3: 跑菜单 + Play 断言（TDD：先验证失败基线）**

先执行菜单 `Demo/构建户外场景`，然后 unityMCP 进 Play，`execute_code` 采样 3 点：

```csharp
// 期望: 三点射线命中高度 ≈ { z=30:y≈0±1, z=70:y≈-1.5±1, z=140:y≈-3.2±1 }
foreach (float z in new float[]{30f, 70f, 140f}) {
    Physics.Raycast(new Vector3(0, 30f, z), Vector3.down, out var hit, 100f);
    Debug.Log($"[M6-1] z={z} groundY={hit.point.y:F2}");
}
```

Expected: 三点高度与剖面设计吻合（误差 ±1 内）；**不吻合则回到 Task 1 修高度函数**

- [ ] **Step 4: 走到出口验证衔接**

Play 中用 MCP 传送玩家到 `(0, 0.2, 20)`（B 房北墙内侧），向北走应被墙挡住；传送到 `(0, 0.2, 26)`（墙外）应站上出口平台。截图两张存 `docs/milestones/M6/`。

- [ ] **Step 5: Commit**

```bash
git add game/3D-Demo/Assets/Editor/OutdoorBuilder.cs game/3D-Demo/Assets/Art/Static/outdoor/
git commit -m "feat(M6-1): OutdoorBuilder 骨架 + 峡谷地形导入（MeshCollider 静态）"
```

### Task 3: 出口工程（北墙门洞 + 下行台阶 + 门厅石块）

**Files:**
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（追加 `BuildExitHall()`）

**Interfaces:**
- Consumes: 关卡坐标（墙 `WallB_N` 位于 z=22、x ±8；`SM_Step`、`SM_Arch/SM_DoorFrame/SM_Wall_*` FBX）；`LevelSpec.DoorPos` 模式
- Produces: 出口门洞对象组 `OUT_ExitHall_*`——墙洞宽 4m（x ±2）、高 4.5m；台阶 8 级（z 34→46 坡道上，每级下落 0.19m）；`OUT_Exit_Stairs` 组

- [ ] **Step 1: 实现 BuildExitHall**

```csharp
// —— 出口工程 ——
// 1) 北墙中央开门洞: 隐藏 WallB_N 灰盒渲染并拆洞——直接在墙北侧新建门洞组件（灰盒碰撞保持完整，
//    用新增两段墙代替中部阻挡，玩家出口走 z=22 洞口）。
//    实现：销毁 WallB_N 中央 4m 的 VIZ_ 子对象（KitPlacer 铺的墙段），
//    新建 OUT_ExitHall_L/R（SM_Wall_A 各一段 2m，位置 x=±3, z=22）
//    与 OUT_ExitHall_Top（SM_Wall_A 横放封门楣 y=4.2~6）——均带 BoxCollider。
// 2) 台阶：for i in 0..7，Instantiate SM_Step 于 (0, -0.19*i, 34 + 1.5*i)，含 BoxCollider。
// 3) 洞口两侧石壁：SM_Wall_C/D 各一竖直贴内墙。
static void BuildExitHall()
{
    // （完整实现按注释顺序：清 WallB_N 中部 VIZ → 摆 8 级台阶 → 两段门洞墙 + 门楣）
}
```

（完整实现按上述注释顺序编写；墙段位置与 `SM_Wall_A` 尺寸（4m 宽）对齐：`OUT_ExitHall_L` 中心 `(-4, 3, 22)`、`R` 在 `(+4, 3, 22)`。）

- [ ] **Step 2: 跑菜单 + Play 走通**

Play 传送到 `(0, 0.2, 20)`，按 W 向北：应穿过门洞、沿台阶下到 `y≈-1.5` 的草原起点（z≈46）。MCP 断言：`GameObject.Find("Player").transform.position.z > 46` 且 `y <= -1.4`。

- [ ] **Step 3: 截图（门洞内外两张）存 `docs/milestones/M6/exit_*.png`，Commit**

```bash
git add game/3D-Demo/Assets/Editor/OutdoorBuilder.cs docs/milestones/M6/
git commit -m "feat(M6-1): 出口工程（北墙门洞+八级下行台阶+门厅墙件）"
```

### Task 4: 户外氛围（天空/太阳/雾/后处理 + 室内外光照过渡）

**Files:**
- Create: `game/3D-Demo/Assets/Editor/OutdoorFxSetup.cs`
- Create: `game/3D-Demo/Assets/Scripts/LightZone.cs`

**Interfaces:**
- Consumes: 现有 `Sun`（Directional Light，室内强度 0.3）、`Global Volume`（M5 的 Bloom+ACES profile，路径 `Assets/Settings/M5_Atmosphere_Volume.asset`）
- Produces: 户外光照参数——太阳强度 1.5 / 色温 5400K / 角度 (42°, -35°)；雾 线性 start 60 end 240 色 (0.62,0.70,0.78)；Volume 追加 `ColorAdjustments`（饱和度 +8）；`LightZone` 触发器组（`OUT_Zone_Indoor` z 12-24 / `OUT_Zone_Outdoor` z 26-40）过渡时长 1.5s

- [ ] **Step 1: 写 LightZone.cs**

```csharp
using UnityEngine;

// M6-1: 室内外光照过渡——玩家进入 Zone 后把太阳/雾/环境光混到目标值（Lerp 过渡）。
public class LightZone : MonoBehaviour
{
    public Light sun; public float sunIntensity = 1.5f; public Color sunColor = new Color(1f, 0.96f, 0.88f);
    public float fogStart = 60f, fogEnd = 240f;
    public float blendSeconds = 1.5f;

    static float targetIntensity = 0.3f, targetFogStart = 0f, targetFogEnd = 60f;   // 静态: 两 Zone 共用同一目标
    static Color targetSunColor = new Color(1f, 0.85f, 0.7f);
    float t = 1f;

    // 初始抓取（室内默认值在场景里保存于 Sun/雾设置，这里只 lerp 到目标）
    void OnTriggerEnter(Collider other)
    {
        if (!other.CompareTag("Player")) return;
        targetIntensity = sunIntensity; targetSunColor = sunColor;
        targetFogStart = fogStart; targetFogEnd = fogEnd;
        t = 0f;
    }

    void Update()
    {
        if (t >= 1f || !sun) return;
        t += Time.deltaTime / blendSeconds;
        float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(t, 1f));
        sun.intensity = Mathf.Lerp(sun.intensity, targetIntensity, k);
        sun.color = Color.Lerp(sun.color, targetSunColor, k);
        RenderSettings.fogStartDistance = Mathf.Lerp(RenderSettings.fogStartDistance, targetFogStart, k);
        RenderSettings.fogEndDistance = Mathf.Lerp(RenderSettings.fogEndDistance, targetFogEnd, k);
    }
}
```

- [ ] **Step 2: 写 OutdoorFxSetup.cs（菜单 `Demo/户外氛围`）**

要点（仿 PostFxSetup 的资产化+幂等写法）：① 打开 profile 资产追加 `ColorAdjustments`（`AddObjectToAsset` 关键——M5-3 的坑）；② `RenderSettings.fog = true; mode = Linear`，初始 start 0/end 60（室内浓雾）；③ 天空：`profile.Add<PhysicallyBasedSky>(true)`（Unity 6 URP 内置；若版本无此类则用 `GradientSky`——代码用 `#if` 或 try 反射，**实现时先查 URP 版本支持**）；④ 创建 `OUT_Zone_Indoor/Outdoor` 两个 Box（isTrigger）+ `LightZone` 组件（Outdoor 的 sun 指向场景 Sun）；⑤ 曝光：`ColorAdjustments.postExposure.Override(0.2f)`。

- [ ] **Step 3: 跑菜单 + Play 过渡验证**

Play 从室内走到户外：截图三张（室内原样 / 门口过渡中 / 草原户外），存 `docs/milestones/M6/fx_*.png`。断言：出门后 `RenderSettings.fogEndDistance ≈ 240±5`。

- [ ] **Step 4: Commit**

```bash
git add game/3D-Demo/Assets/Editor/OutdoorFxSetup.cs game/3D-Demo/Assets/Scripts/LightZone.cs docs/milestones/M6/
git commit -m "feat(M6-1): 户外氛围（天空/太阳/雾/曝光）+ 室内外光照过渡 Zone"
```

### Task 5: 植被资产（草丛/灌木/树）

**Files:**
- Create: `blender_assets/scripts/outdoor_plants.py`
- 产出: `export/outdoor/SM_GrassTuft.fbx` / `SM_Bush_A.fbx` / `SM_Bush_B.fbx` / `SM_Tree_A.fbx` / `SM_Tree_B.fbx` + 渲染总览图

**Interfaces:**
- Produces: 五件植物网格（**写实丛林取向**：草簇=7-9 叶片状面片群、灌木=多层半球叶团、树=锥柱干+3 层不规则叶冠）；材质 `M_Grass`（沿用 temple 的幽暗草绿）、新增 `M_Leaf_Dark`（(0.13,0.22,0.09)）、`M_Trunk`（(0.18,0.13,0.09)）、`M_Leaf_Mid`（(0.18,0.28,0.11)）；tris 预算：草 ≤400 / 灌木 ≤1800 / 树 ≤2800

- [ ] **Step 1: 写生成脚本**

结构照抄 temple_kit.py 的 `_fin/bmesh 聚合/材质/jitter/flat/triangulate/export_obj/渲染` 模式（新文件独立，`random.seed(12)`）。草簇=3-9 根锥形曲带（bmesh 沿曲线挤出，双面镜像片 8mm 间隔——**沿用 add_flame 的双面片技巧**，Unity 单面剔除兼容）；树冠=icosphere 拉长变形 + jitter。

- [ ] **Step 2: headless 跑 + 断言 + 渲染检查**

Run: `blender.exe --background --factory-startup --python blender_assets/scripts/outdoor_plants.py -- --render`
Expected: 五件 FBX 各 >5KB、tris 在预算内；`plants_overview.png` 目视五件形态成立（**不看图不提交**）

- [ ] **Step 3: 拷贝 FBX 到 Unity 并提交**

```bash
cp blender_assets/export/outdoor/SM_{GrassTuft,Bush_A,Bush_B,Tree_A,Tree_B}.fbx game/3D-Demo/Assets/Art/Static/outdoor/
git add blender_assets/scripts/outdoor_plants.py game/3D-Demo/Assets/Art/Static/outdoor/ docs/milestones/M6/
git commit -m "feat(M6-1): 植被资产五件（草簇/灌木×2/树×2，程序化+双面片）"
```

### Task 6: 植被散布器 + M6-1 验收

**Files:**
- Create: `game/3D-Demo/Assets/Editor/VegetationScatter.cs`（菜单 `Demo/散布植被`）

**Interfaces:**
- Consumes: Task 1 地形（射线采样）、Task 5 五件 FBX
- Produces: `OUT_Veg_*` 分组对象——草：材质 `M_Grass`（**enableInstancing=true**，每簇独立实体但同材质 Instanced）；树/灌木：实体标 `BatchingStatic`（静态——**按父链检查无例外**：植物不会被砍/移动，藤帘除外）；密度常量：草 4m 抖动格、树 12m 抖动格、灌木 8m 格

- [ ] **Step 1: 写散布器**

```csharp
// 规则：射线从 (x, 40, z) 向下；要求命中 OUT_SM_CanyonTerrain；法线 y>0.85（坡度<32°）；
// 路径带 |x|<4 不撒树（草可）；高程带权重：草原段(z 46-96)最密、河谷(z126-176)只草、崖壁(|x|>20)不撒。
// 随机：格点 + 抖动 0-2m；旋转随机 yaw；缩放 0.8-1.3。
```

（含断言：撒完打印 `草/灌木/树` 数量，预期量级 500-700 / 60-100 / 60-120；不符则检查射线条件。）

- [ ] **Step 2: 跑菜单 + 帧率抽查（M5-5 采样法）**

Play 草原视点 `(0,0,80)` 朝北：`execute_code` 两次采样 `Time.frameCount/Time.realtimeSinceStartup`，帧率目标 ≥70（编辑器态）。低于则先降密度常数。

- [ ] **Step 3: 截图三视点（草原/河谷口/回望神庙）存 `docs/milestones/M6/veg_*.png`**

- [ ] **Step 4: M6-1 验收截图集 + 汇报**

出门全流程（门洞→台阶→草原）连续截图 5 张存 `docs/milestones/M6/M6_1_acceptance/`，**停下向用户汇报截图与帧率，等确认后再进 M6-2**。

- [ ] **Step 5: Commit**

```bash
git add game/3D-Demo/Assets/Editor/VegetationScatter.cs docs/milestones/M6/
git commit -m "feat(M6-1): 植被散布器（坡度/高程规则+Instancing）与 M6-1 验收"
```

---

## Milestone M6-2：蹲行 + 岩缝

> 里程碑目标：C 键蹲行（站起受头顶净空限制）；岩缝段可蹲行通过、站立被挡。**完成后停下汇报等待确认。**

### Task 7: 蹲行动画（Blender）

**Files:**
- Modify: `blender_assets/scripts/hero_anims.py`（新增 `make_crouch_idle` / `make_crouch_walk` + 注册 + 断言）
- 产出: 更新后的 `export/characters/SK_Explorer.fbx`（+2 clips）+ `docs/milestones/M4/anim_sheet_crouchidle.png`、`anim_sheet_crouchwalk.png`

**Interfaces:**
- Produces: 动画 clip `A_CrouchIdle`（40f 循环）、`A_CrouchWalk`（36f 循环）；蹲姿身高约 1.15m（Hips 下降 0.52m）
- Consumes: 现有 `hero_anims.py` 骨架（`begin/key_all/wrot/wloc/walign2/FOOT_FIX/LEG_IN_*` 等助手）

- [ ] **Step 1: 追加两段动画（照 make_idle/make_walk 结构）**

```python
def make_crouch_idle():
    """40f 循环蹲姿：Hips 降 0.52m + 躯干前倾（Spine 14°/Spine1 8°）+ 大腿前抬小腿深屈（脚保持贴地）；
    呼吸微动 ±1°。身高约 1.15m，与 CharacterController crouchHeight 对齐。"""
    act = begin("A_CrouchIdle"); n = 40
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        wloc("Hips", dz=-0.52)
        wrot("Spine", "Y", 14); wrot("Spine1", "Y", 8 + 1.0 * math.sin(ph))
        wrot2("LeftUpLeg", [("X", LEG_IN_L), ("Y", -68)])          # 大腿前抬（蹲）
        wrot2("RightUpLeg", [("X", LEG_IN_R), ("Y", -68)])
        wrot("LeftLeg", "Y", 100)                                   # 小腿后折（屈膝）
        wrot("RightLeg", "Y", 100)
        wrot2("LeftArm", [("X", ARM_DROP_L), ("Y", 6)])
        wrot2("RightArm", [("X", ARM_DROP_R), ("Y", 6)])
        wrot("LeftForeArm", "Z", -22); wrot("RightForeArm", "Z", 22)   # 肘收
        wrot("LeftFoot", "Y", FOOT_FIX); wrot("RightFoot", "Y", FOOT_FIX)
        key_all(f)
    return act

def make_crouch_walk():
    """36f 循环蹲行：蹲姿基底 + 大腿摆 ±14° / 小腿 96±10° / 臂微摆 ±8° / Hips 起伏 0.02。"""
    act = begin("A_CrouchWalk"); n = 36
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        wloc("Hips", dz=-0.52 + 0.02 * math.sin(2 * ph))
        wrot("Spine", "Y", 14); wrot("Spine1", "Y", 8)
        wrot2("LeftUpLeg", [("X", LEG_IN_L), ("Y", -68 - 14 * math.sin(ph))])
        wrot2("RightUpLeg", [("X", LEG_IN_R), ("Y", -68 - 14 * math.sin(ph + math.pi))])
        wrot("LeftLeg", "Y", 96 + 10 * max(0.0, math.sin(ph + 0.6)))
        wrot("RightLeg", "Y", 96 + 10 * max(0.0, math.sin(ph + math.pi + 0.6)))
        wrot2("LeftArm", [("X", ARM_DROP_L), ("Y", 8 * math.sin(ph))])
        wrot2("RightArm", [("X", ARM_DROP_R), ("Y", 8 * math.sin(ph + math.pi))])
        wrot("LeftForeArm", "Z", -22); wrot("RightForeArm", "Z", 22)
        wrot("LeftFoot", "Y", FOOT_FIX); wrot("RightFoot", "Y", FOOT_FIX)
        key_all(f)
    return act
```

（数值为设计初值——**以 Step 2 的侧视渲染图为准微调**：脚底应贴地、无明显穿地/悬空。）

- [ ] **Step 2: 注册 + 断言 + 跑脚本**

① `acts` 列表追加 `make_crouch_idle(), make_crouch_walk()`；② `EXPECT` 追加 `"A_CrouchIdle": 40, "A_CrouchWalk": 36`；③ `SHOTS` 追加 `"A_CrouchIdle": [0,10,20,30], "A_CrouchWalk": [0,9,18,27]`。

Run: `blender.exe --background --factory-startup --python blender_assets/scripts/hero_anims.py -- --skip-render`
Expected: 断言全过（两项新 clip 打印 `ACT A_Crouch...`）；然后全量渲染 `blender.exe ... --python blender_assets/scripts/hero_anims.py`（无 --skip-render）看侧视 sheet 图调整蹲姿。

- [ ] **Step 3: 拷贝 FBX + Unity 断言 clip 存在**

```bash
cp blender_assets/export/characters/SK_Explorer.fbx game/3D-Demo/Assets/Art/Characters/SK_Explorer.fbx
```

unityMCP 编辑器代码断言（AssetDatabase 编辑器状态下可执行）：

```csharp
var names = new System.Collections.Generic.List<string>();
foreach (var o in AssetDatabase.LoadAllAssetsAtPath("Assets/Art/Characters/SK_Explorer.fbx"))
    if (o is AnimationClip c) names.Add(c.name);
Debug.Log("CLIPS: " + string.Join(",", names));
// 期望包含 A_CrouchIdle 与 A_CrouchWalk
```

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/hero_anims.py blender_assets/export/characters/SK_Explorer.fbx game/3D-Demo/Assets/Art/Characters/SK_Explorer.fbx docs/milestones/M4/anim_sheet_crouchidle.png docs/milestones/M4/anim_sheet_crouchwalk.png
git commit -m "feat(M6-2): 蹲行动画两段（A_CrouchIdle/A_CrouchWalk，40f/36f）"
```

### Task 8: 蹲行状态机（Unity）

**Files:**
- Modify: `game/3D-Demo/Assets/Scripts/ThirdPersonController.cs`
- Modify: `game/3D-Demo/Assets/Editor/AnimatorSetup.cs`

**Interfaces:**
- Produces: `ThirdPersonController.Crouching`（public 只读属性）；`crouch` Animator bool 参数；状态 `CrouchIdle`/`CrouchWalk`
- Consumes: Task 7 的两个 clip；现有 `cc.height=1.8/center=(0,0.9,0)` 基线

- [ ] **Step 1: 改 ThirdPersonController（三处）**

```csharp
// 字段区新增：
public float crouchSpeed = 0.85f, crouchHeight = 1.15f;   // M6-2: 蹲行速度/胶囊高（站起需头顶净空）
public bool Crouching { get; private set; }

// Update 内、climb 分支之前新增蹲切换（爬墙时强制起身）：
if (climb && climb.IsClimbing && Crouching) SetCrouch(false);
if (Input.GetKeyDown(KeyCode.C))
{
    if (Crouching) { if (CanStand()) SetCrouch(false); }
    else SetCrouch(true);
}

// speed 行替换（原: Input.GetKey(LeftShift) ? runSpeed : moveSpeed）：
float speed = Crouching ? crouchSpeed : (Input.GetKey(KeyCode.LeftShift) ? runSpeed : moveSpeed);

// 跳跃条件加 !Crouching（原: if (grounded && Input.GetButtonDown("Jump") && !jumpPending)）：
if (grounded && !Crouching && Input.GetButtonDown("Jump") && !jumpPending)

// 新方法（放在 GroundSnap 后）：
void SetCrouch(bool on)
{
    Crouching = on;
    cc.height = on ? crouchHeight : 1.8f;
    cc.center = new Vector3(0, cc.height / 2f, 0);   // 底部保持 y=0：无需位置补偿
}

bool CanStand()
{
    // 头顶向上检测：crouchHeight 之上到站立高再加 2cm 余量
    Vector3 o = transform.position + Vector3.up * (crouchHeight + 0.05f);
    return !Physics.SphereCast(o, 0.25f, Vector3.up, out _, 1.8f - crouchHeight + 0.1f,
                               ~0, QueryTriggerInteraction.Ignore);
}

// SyncAnimator 内追加：
anim.SetBool("crouch", Crouching);
```

- [ ] **Step 2: 改 AnimatorSetup（Setup 内扩展）**

```csharp
ctrl.AddParameter("crouch", AnimatorControllerParameterType.Bool);
var crouchIdle = sm.AddState("CrouchIdle"); crouchIdle.motion = clips["A_CrouchIdle"];
var crouchWalk = sm.AddState("CrouchWalk"); crouchWalk.motion = clips["A_CrouchWalk"];
crouchWalk.speed = 1.2f;                    // 蹲速 0.85m/s 对齐初值（Play 中按滑步微调）
// crouch 转换先于既有 speed 转换添加（Animator 按添加顺序评估，保证优先级）：
T(idle, crouchIdle, "crouch", AnimatorConditionMode.If, 0f);
T(walk, crouchWalk, "crouch", AnimatorConditionMode.If, 0f);
T(run, crouchWalk, "crouch", AnimatorConditionMode.If, 0f);
T(crouchIdle, crouchWalk, "speed", AnimatorConditionMode.Greater, 0.1f);
T(crouchWalk, crouchIdle, "speed", AnimatorConditionMode.Less, 0.1f);
T(crouchIdle, idle, "crouch", AnimatorConditionMode.IfNot, 0f);
T(crouchWalk, walk, "crouch", AnimatorConditionMode.IfNot, 0f);
T(crouchIdle, climb, "climbing", AnimatorConditionMode.If, 0f);
T(crouchWalk, climb, "climbing", AnimatorConditionMode.If, 0f);
```

然后重跑菜单：`Demo/生成玩家 Animator` → `Demo/接线主角到玩家`（重挂 Hero 修复 controller 引用）。

- [ ] **Step 3: Play 断言（先跑基线后验证行为）**

MCP Play；初始断言 `cc.height==1.8`；按 C 后断言 `==1.15`；再按 C 断言 `==1.8`；蹲着进入桌下（无遮挡处仅数字验证）；拖动到贴墙处再按 C 站起应被拒（height 保持 1.15）。截图蹲姿（近景）+ 蹲行移动 1 张。

- [ ] **Step 4: Commit**

```bash
git add game/3D-Demo/Assets/Scripts/ThirdPersonController.cs game/3D-Demo/Assets/Editor/AnimatorSetup.cs
git commit -m "feat(M6-2): 蹲行状态机（C 切换/净空检测/Animator 两状态）"
```

### Task 9: 岩缝段（巨石阵 + 蹲行通过验证）

**Files:**
- Create: `blender_assets/scripts/outdoor_props.py`（SM_GorgeRock_A/B + 后续复用）
- Create: `game/3D-Demo/Assets/Scripts/HintZone.cs`
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（追加 `BuildGorge()`）

**Interfaces:**
- Produces: `SM_GorgeRock_A`（3.5m 不规则巨石）/ `SM_GorgeRock_B`（5m 扁石）；`HintZone`（通用——`public string text; public float radius=5f;` 玩家进入半径一次性 `SimpleUI.SetObjective(text)`，后续藤/河/绳复用）；`OUT_Gorge_*` 组（缝段内高 1.45m，净宽 1.4m）
- Consumes: Task 1 地形（缝段地面 y=-1.5）、Task 8 蹲行（crouchHeight 1.15）

- [ ] **Step 1: 写 outdoor_props.py（首出两块巨石）**

结构照抄 temple_kit 的 `build_debris` 模式：ico 球 → 非均匀缩放 → jitter 大扰动（0.15×size）→ refine 细分到 tris 预算（A ≤1600 / B ≤2200）→ `M_Cliff`（新材质 (0.35,0.30,0.24) rough 0.9）→ 导出 FBX + 渲染两件总览到 `docs/milestones/M6/gorge_rocks.png`。

- [ ] **Step 2: 写 HintZone.cs**

```csharp
using UnityEngine;
// M6: 通用提示区——玩家进入半径内一次性更新目标文案（CC 不产生 Trigger 事件，用距离检测）。
public class HintZone : MonoBehaviour {
    public string text; public float radius = 5f;
    Transform player; bool fired;
    void Update() {
        if (fired) return;
        if (!player) { var p = GameObject.FindGameObjectWithTag("Player"); if (p) player = p.transform; }
        if (player && Vector3.Distance(player.position, transform.position) < radius) {
            fired = true; SimpleUI.Instance?.SetObjective(text);
        }
    }
}
```

- [ ] **Step 3: OutdoorBuilder 追加 BuildGorge()**

```csharp
// 缝段 z 96-126：两侧石壁（x=±2.2，每 4m 一块 A/B 交替，缩放到高 2-3m）+ 顶横石
//（每 4m 一块 B 横放：底面 y=-0.05 → 内高 1.45m）+ 缝口 HintZone("岩缝太窄——按 C 蹲下通过")。
// 全部 MeshCollider + BatchingStatic（静态）；随机用固定 seed 保证幂等重跑一致。
static void BuildGorge()
{
    var rnd = new System.Random(77);
    for (float z = 98f; z <= 124f; z += 4f)
    {
        float hL = 2f + (float)rnd.NextDouble(), hR = 2f + (float)rnd.NextDouble();
        MakeRock("OUT_Gorge_L" + z, "SM_GorgeRock_A", new Vector3(-2.9f, -1.5f + hL * 0.5f, z), hL);
        MakeRock("OUT_Gorge_R" + z, "SM_GorgeRock_B", new Vector3(2.9f, -1.5f + hR * 0.5f, z), hR);
        if (z <= 118f)   // 顶横石：底面 -0.05，厚 0.9 → 中心 0.40
            MakeRock("OUT_Gorge_Top" + z, "SM_GorgeRock_B", new Vector3(0f, 0.4f, z),
                     1f, new Vector3(2.6f, 1f, 1.4f));   // 缩放参数按石件包围盒校准
    }
    var hint = new GameObject("OUT_Gorge_Hint");
    hint.transform.position = new Vector3(0, -1.5f, 92f);
    var hz = hint.AddComponent<HintZone>(); hz.text = "岩缝太窄——按 C 蹲下通过"; hz.radius = 6f;
}
```

- [ ] **Step 4: 跑菜单 + Play 验证（先败后成）**

① 跑 `Demo/构建户外场景`；② Play 传送 `(0,-1.4,100)` 朝北走：**站立被挡**（断言 z 停在缝口前 < 100）；③ 按 C 蹲行：**通过**（断言 z > 126）；④ 截图：缝口外观、蹲行穿越各 1 张。

- [ ] **Step 5: Commit**

```bash
git add blender_assets/scripts/outdoor_props.py game/3D-Demo/Assets/Scripts/HintZone.cs game/3D-Demo/Assets/Editor/OutdoorBuilder.cs game/3D-Demo/Assets/Art/Static/outdoor/ docs/milestones/M6/
git commit -m "feat(M6-2): 岩缝段（巨石阵+顶横石，蹲行通过/站立被挡）"
```

---

## Milestone M6-3：挥刀砍藤

> 里程碑目标：鼠标左键挥刀（刀挂右手）；藤蔓帘挡路，挥刀砍断后可通过。**完成后停下汇报等待确认。**

### Task 10: 佩刀资产 + 挥刀动画（Blender）

**Files:**
- Create: `blender_assets/scripts/hero_props.py`
- Modify: `blender_assets/scripts/hero_anims.py`（新增 `make_slash`）

**Interfaces:**
- Produces: `SM_Knife`（总长 0.42m：柄 0.11 + 刃 0.28，原点在柄底——便于挂手骨校准）；材质 `M_Blade`（(0.65,0.66,0.68) rough 0.3 metal 0.9）；动画 `A_Slash`（25f 一次性）
- Consumes: hero_anims.py 的 `begin/key_all/walign2/wrot` 与 make_mantle 的关键姿态（K 表）模式

- [ ] **Step 1: 写 hero_props.py 生成 SM_Knife**

柄=圆柱 r0.016 h0.11（`M_Grip` (0.16,0.10,0.07)）+ 护手小方块 + 刃=box 变薄拉伸（长 0.28、宽 0.035、厚 0.014→0.004 渐薄，尖端斜切）→ flat + triangulate → tris ≤1200 → 导出 `export/hero_props/SM_Knife.fbx` + 渲染三视图到 `docs/milestones/M6/knife.png`。

- [ ] **Step 2: hero_anims.py 追加 make_slash（K 表一次性 25f）**

```python
def make_slash():
    """25f 一次性挥刀：垂臂→右臂后引上抬→斜劈至前下→收势回垂臂。
    右臂主导（左臂辅助平衡），躯干微前倾随劈。frame 与 Attack.cs 判定窗对齐（劈下帧 f10-f14）。"""
    act = begin("A_Slash")
    K = [
        (0,  0, (0.05, 0.10, -0.98), (0.30, 0.20, -0.92)),   # 垂臂（=Idle 收尾姿态）
        (5,  4, (-0.35, 0.55, 0.75), (-0.15, 0.35, 0.90)),   # 后引上抬：右臂向后上举/肘屈
        (10, 10, (0.15, -0.10, 0.98), (0.35, -0.25, 0.88)),  # 劈至中线：臂快速前下（判定窗开始）
        (14, 12, (0.35, -0.55, 0.72), (0.55, -0.60, 0.55)),  # 劈到底：臂前下伸（判定窗结束）
        (19, 5, (0.20, -0.20, -0.90), (0.30, -0.10, -0.92)), # 收势
        (25, 0, (0.00, 0.06, -1.00), (0.00, 0.06, -1.00)),   # 回 Idle 姿态
    ]
    for f, sp, uaR, faR in K:
        clear_pose()
        wrot("Spine", "Y", sp)
        walign2("RightArm", uaR); walign2("RightForeArm", faR)
        walign2("LeftArm", mir((0.05, 0.10, -0.98)));         # 左臂常量垂摆
        walign2("LeftForeArm", mir((0.30, 0.20, -0.92)))
        wrot("LeftFoot", "Y", FOOT_FIX); wrot("RightFoot", "Y", FOOT_FIX)
        key_all(f)
    return act
```

注册：`acts` 追加、`EXPECT["A_Slash"]=25`、`SHOTS["A_Slash"]=[0,5,10,14,19]`（5 帧——渲染段支持任意长度列表）、循环断言豁免名单追加 `"A_Slash"`。

- [ ] **Step 3: 重跑 + 拷贝 + 断言**

Run: `blender.exe --background --factory-startup --python blender_assets/scripts/hero_anims.py`（看 slash sheet 侧视微调右臂轨迹）→ 拷贝 `SK_Explorer.fbx` 与 `SM_Knife.fbx`：

```bash
cp blender_assets/export/characters/SK_Explorer.fbx game/3D-Demo/Assets/Art/Characters/
mkdir -p game/3D-Demo/Assets/Art/Static/hero_props
cp blender_assets/export/hero_props/SM_Knife.fbx game/3D-Demo/Assets/Art/Static/hero_props/
```

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/hero_props.py blender_assets/scripts/hero_anims.py blender_assets/export/ game/3D-Demo/Assets/Art/ docs/milestones/M6/knife.png docs/milestones/M4/anim_sheet_slash.png
git commit -m "feat(M6-3): 佩刀 SM_Knife + 挥刀动画 A_Slash（25f 一次性）"
```

### Task 11: 攻击系统（Attack.cs + Animator Slash）

**Files:**
- Create: `game/3D-Demo/Assets/Scripts/ICuttable.cs`
- Create: `game/3D-Demo/Assets/Scripts/Attack.cs`
- Modify: `game/3D-Demo/Assets/Editor/AnimatorSetup.cs`（Slash 状态 + 挂刀接线进 Attach）

**Interfaces:**
- Produces: `ICuttable { void Cut(Vector3 dir); }`（Task 12 的 CuttableVine 实现）；`Attack`（左键→`slash` trigger→0.18s 后 OverlapSphere 判定）；Attach 时自动挂 `Attack` 并实例化刀到 RightHand 骨骼
- Consumes: Task 10 的 A_Slash clip 与 SM_Knife FBX

- [ ] **Step 1: 写 ICuttable.cs 与 Attack.cs**

```csharp
using UnityEngine;
// M6-3: 可斩断目标接口——藤蔓等实现之（Attack 判定窗命中即调用）。
public interface ICuttable { void Cut(Vector3 dir); }
```

```csharp
using UnityEngine;
// M6-3: 左键挥刀——触发 Slash 动画 + 判定窗扇形检测（命中 ICuttable）；
// Start 时把 SM_Knife 实例挂到 RightHand 骨骼（随动画摆动）。
public class Attack : MonoBehaviour
{
    public GameObject knifePrefab;                 // SM_Knife.fbx（Assets/Art/Static/hero_props）
    public float hitDelay = 0.18f;                 // 判定窗时刻（对齐 A_Slash f10-f14 中点，渲染后微调）
    public float range = 1.2f, radius = 0.85f, cooldown = 0.7f;
    float next; Animator anim; Transform knife;

    void Start()
    {
        anim = GetComponentInChildren<Animator>();
        var hand = anim ? anim.GetBoneTransform(HumanBodyBones.RightHand) : null;
        if (hand && knifePrefab) knife = Instantiate(knifePrefab, hand).transform;
    }

    void Update()
    {
        if (Time.time < next || Time.timeScale == 0f) return;   // 覆盖暂停菜单期间（timeScale=0）不响应攻击
        if (!Input.GetMouseButtonDown(0)) return;
        next = Time.time + cooldown;
        if (anim) anim.SetTrigger("slash");
        Invoke(nameof(Hit), hitDelay);
    }

    void Hit()
    {
        Vector3 c = transform.position + Vector3.up * 0.9f + transform.forward * (range * 0.6f);
        foreach (var h in Physics.OverlapSphere(c, radius, ~0, QueryTriggerInteraction.Ignore))
        {
            var cut = h.GetComponentInParent<ICuttable>();
            if (cut != null) { cut.Cut(transform.forward); break; }
        }
    }
}
```

（暂停期间不响应通过 `Time.timeScale == 0f` 判断，无外部依赖。）

- [ ] **Step 2: AnimatorSetup 扩展（Slash 状态 + 接线）**

Setup() 追加：

```csharp
ctrl.AddParameter("slash", AnimatorControllerParameterType.Trigger);
var slash = sm.AddState("Slash"); slash.motion = clips["A_Slash"];
T(idle, slash, "slash", AnimatorConditionMode.If, 0f);
T(walk, slash, "slash", AnimatorConditionMode.If, 0f);
T(run, slash, "slash", AnimatorConditionMode.If, 0f);
T(crouchIdle, slash, "slash", AnimatorConditionMode.If, 0f);
T(crouchWalk, slash, "slash", AnimatorConditionMode.If, 0f);
var sBack1 = slash.AddTransition(idle);                          // 播完回（exit 0.8×1.04s≈0.83s）
sBack1.hasExitTime = true; sBack1.exitTime = 0.8f; sBack1.duration = 0.1f;
sBack1.AddCondition(AnimatorConditionMode.IfNot, 0f, "crouch");
var sBack2 = slash.AddTransition(crouchIdle);
sBack2.hasExitTime = true; sBack2.exitTime = 0.8f; sBack2.duration = 0.1f;
sBack2.AddCondition(AnimatorConditionMode.If, 0f, "crouch");
```

Attach() 追加：

```csharp
var atk = player.GetComponent<Attack>(); if (atk == null) atk = player.AddComponent<Attack>();
atk.knifePrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Static/hero_props/SM_Knife.fbx");
```

重跑 `Demo/生成玩家 Animator` → `Demo/接线主角到玩家`。

- [ ] **Step 3: Play 验证**

Play，MCP 模拟左键（`execute_code` 无法注入输入——**改为**：直接调用 `player.GetComponent<Attack>().SendMessage("Hit")` 验证判定逻辑可运行；动画触发用 `anim.SetTrigger("slash")` 观察）。截图：挥刀中帧（手部近景，刀可见且随臂动）。检查握持朝向（不顺手就调 `knife.localRotation`，目标：刃口朝前）。

- [ ] **Step 4: Commit**

```bash
git add game/3D-Demo/Assets/Scripts/ICuttable.cs game/3D-Demo/Assets/Scripts/Attack.cs game/3D-Demo/Assets/Editor/AnimatorSetup.cs
git commit -m "feat(M6-3): 攻击系统（Attack 判定窗+手骨挂刀+Animator Slash 状态）"
```

### Task 12: 藤蔓帘 + 斩断交互

**Files:**
- Modify: `blender_assets/scripts/outdoor_plants.py`（新增 `SM_Vine_Curtain`）
- Create: `game/3D-Demo/Assets/Scripts/CuttableVine.cs`
- Modify: `game/3D-Demo/Assets/Scripts/AudioManager.cs`（+`Chop()`）
- Modify: `game/3D-Demo/Assets/Editor/AudioWiring.cs`（+合成 chop clip）
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（追加 `BuildVines()`）

**Interfaces:**
- Produces: `SM_Vine_Curtain`（宽 5m×垂长 2.6m 藤帘：9 条垂藤+叶面片，原点在帘顶中点）；`CuttableVine : MonoBehaviour, ICuttable`（塌落动画→隐藏）；`AudioManager.Chop()`
- Consumes: Task 11 的 ICuttable；AudioWiring 既有合成模式

- [ ] **Step 1: outdoor_plants.py 追加藤帘**

每条藤=沿垂直曲线（S 弯 ±0.08m 微扰）的锥形管（r 0.05→0.02，~20 段）+ 沿藤每 0.4m 叶片面片（菱形 0.15m，双面）；9 条 × 间距 0.55m；共 ≤2600 tris；材质 `M_Vine`(0.10,0.22,0.08) + `M_Leaf_Dark`。导出 + 渲染特写 `docs/milestones/M6/vine.png` → 拷贝 FBX 到 `Assets/Art/Static/outdoor/`。

- [ ] **Step 2: AudioManager + AudioWiring 加 Chop**

AudioManager：`public AudioClip chop;` + `public void Chop() => OneShot(chop);`
AudioWiring：在既有程序合成段照 `MakeXxx` 模式加 `MakeChop()`（0.15s 白噪声带通+瞬时衰减——"刀切入茎干"闷响），接线到 AudioManager.chop，重跑菜单 `Demo/接线音效`。

- [ ] **Step 3: 写 CuttableVine.cs**

```csharp
using System.Collections;
using UnityEngine;
// M6-3: 藤帘斩断——绕顶部铰链向远侧塌落 80°+微沉（0.9s）后隐藏；移除碰撞、更新目标文案。
public class CuttableVine : MonoBehaviour, ICuttable
{
    Transform player; bool done, hinted;

    void Update()
    {
        if (done) return;
        if (!player) { var p = GameObject.FindGameObjectWithTag("Player"); if (p) player = p.transform; }
        if (!player) return;
        if (!hinted && Vector3.Distance(player.position, transform.position) < 6f)
        {
            hinted = true;
            SimpleUI.Instance?.SetObjective("藤蔓挡住了去路——挥刀砍断（鼠标左键）");
        }
    }

    public void Cut(Vector3 dir)
    {
        if (done) return;
        done = true;
        AudioManager.Instance?.Chop();
        var col = GetComponent<Collider>(); if (col) col.enabled = false;
        SimpleUI.Instance?.SetObjective("继续向北，穿过河谷");
        StartCoroutine(Fall(dir));
    }

    IEnumerator Fall(Vector3 dir)
    {
        float t = 0f;
        Quaternion r0 = transform.rotation; Vector3 p0 = transform.position;
        Vector3 axis = Vector3.Cross(Vector3.up, dir).normalized;   // 倒向玩家挥刀方向
        while (t < 1f)
        {
            t += Time.deltaTime / 0.9f;
            float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(t, 1f));
            transform.rotation = Quaternion.AngleAxis(80f * k, axis) * r0;
            transform.position = p0 + Vector3.down * (0.9f * k);
            yield return null;
        }
        gameObject.SetActive(false);
    }
}
```

- [ ] **Step 4: OutdoorBuilder 追加 BuildVines()**

`OUT_VineCurtain` 放 `(0, -0.1f, 68)`（帘顶世界 y≈-0.1，垂到地面 -1.6 以下）；BoxCollider `size=(5,2.6,0.4)`、`center=(0,-1.3,0)`；挂 `CuttableVine`；**不标** BatchingStatic（会动）。重跑菜单 `Demo/构建户外场景`。

- [ ] **Step 5: Play 验证（先败后成）**

① 传送 `(0,-1.4,60)` 向北走：断言被挡（z 停在 66 左右）；② 触发 HintZone 文案；③ MCP 调 `cut.Cut(Vector3.forward)`（模拟挥刀命中——输入注入不可用时的验证路径）：观察塌落动画截图 2 张（中段+隐藏后）；④ 断言继续走到 z>72。**真刀砍的完整链路（左键→动画→命中）留给 M6-8 用户验收。**

- [ ] **Step 6: Commit**

```bash
git add blender_assets/scripts/outdoor_plants.py game/3D-Demo/Assets/Scripts/CuttableVine.cs game/3D-Demo/Assets/Scripts/AudioManager.cs game/3D-Demo/Assets/Editor/AudioWiring.cs game/3D-Demo/Assets/Editor/OutdoorBuilder.cs game/3D-Demo/Assets/Art/Static/outdoor/SM_Vine_Curtain.fbx docs/milestones/M6/vine.png
git commit -m "feat(M6-3): 藤蔓帘（塌落斩断+提示+Chop 音效）"
```

---

## Milestone M6-4：游泳过河

> 里程碑目标：河谷水面就位；入水自动游泳（固定浮水面+划水），游到对岸自动上岸。**完成后停下汇报等待确认。**

### Task 13: 水域（水面 + WaterVolume）

**Files:**
- Create: `game/3D-Demo/Assets/Scripts/WaterVolume.cs`
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（追加 `BuildWater()`）

**Interfaces:**
- Produces: `WaterVolume.Instance`（静态单例）；`waterLevel`（水面 y=-2.6）；`Contains(Vector3)`（水平矩形范围判定）；`OUT_Water` 水面对象（45×50m，URP Lit 透明水色）
- Consumes: Task 1 河谷段（河床 -3.5、水面 -2.6、z 126-176）

- [ ] **Step 1: 写 WaterVolume.cs（位置判定——CC 不产生 Trigger 事件，沿用 GoalTrigger 经验）**

```csharp
using UnityEngine;
// M6-4: 游泳水域——矩形范围判定（x/z 平面 + 高度上限），供 ThirdPersonController 查询。
public class WaterVolume : MonoBehaviour
{
    public static WaterVolume Instance;
    public float waterLevel = -2.6f;
    public Vector2 xzMin = new Vector2(-22.5f, 126f), xzMax = new Vector2(22.5f, 176f);

    void Awake() { Instance = this; }

    public bool Contains(Vector3 p)
    {
        return p.x > xzMin.x && p.x < xzMax.x && p.z > xzMin.y && p.z < xzMax.y
               && p.y < waterLevel + 0.6f;    // 高度上限：岸上活动不误判
    }
}
```

- [ ] **Step 2: OutdoorBuilder 追加 BuildWater()**

```csharp
// 水面：先评估 Unity 6 URP Water（GameObject > Water Surface）——若项目可用则用其水面；
// 兜底：Plane + URP Lit 透明材质（下方即实现，确定性高，一期采用）。
static void BuildWater()
{
    var go = GameObject.CreatePrimitive(PrimitiveType.Plane);
    go.name = "OUT_Water";
    Object.DestroyImmediate(go.GetComponent<Collider>());          // 水面不参与碰撞（游泳走状态判定）
    go.transform.position = new Vector3(0, -2.6f, 151f);
    go.transform.localScale = new Vector3(4.5f, 1, 5f);            // 45m × 50m
    var mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
    mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 0);        // Transparent
    mat.SetColor("_BaseColor", new Color(0.10f, 0.30f, 0.36f, 0.72f));
    mat.SetFloat("_Smoothness", 0.88f); mat.SetFloat("_Metallic", 0.05f);
    mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
    mat.renderQueue = 3000;
    AssetDatabase.CreateAsset(mat, "Assets/Art/Static/outdoor/M_Water.mat");
    AssetDatabase.SaveAssets();
    go.GetComponent<MeshRenderer>().sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Static/outdoor/M_Water.mat");
    var wv = new GameObject("OUT_WaterVolume").AddComponent<WaterVolume>();   // 判定体与水面同坐标
    wv.transform.position = new Vector3(0, -2.6f, 151f);
}
```

重跑菜单；截图河谷水面（远景一张，验证透明+反光）。

- [ ] **Step 3: Commit**

```bash
git add game/3D-Demo/Assets/Scripts/WaterVolume.cs game/3D-Demo/Assets/Editor/OutdoorBuilder.cs game/3D-Demo/Assets/Art/Static/outdoor/M_Water.mat docs/milestones/M6/
git commit -m "feat(M6-4): 水域（水面+WaterVolume 判定，URP Lit 透明兜底方案）"
```

### Task 14: 游泳状态 + 游泳动画

**Files:**
- Modify: `blender_assets/scripts/hero_anims.py`（新增 `make_swim`）
- Modify: `game/3D-Demo/Assets/Scripts/ThirdPersonController.cs`
- Modify: `game/3D-Demo/Assets/Editor/AnimatorSetup.cs`（Swim 状态）
- Modify: `game/3D-Demo/Assets/Scripts/AudioManager.cs`（+`Splash()`——复用 `land` 或新合成音）

**Interfaces:**
- Produces: `A_Swim`（30f 循环）；`ThirdPersonController.Swimming`；`swimming` Animator 参数 + `Swim` 状态
- Consumes: Task 13 的 `WaterVolume.Instance`

- [ ] **Step 1: hero_anims.py 追加 make_swim**

```python
def make_swim():
    """30f 循环游泳：躯干前倾 52°（身体接近俯卧）+ 双臂交替前划（相位与 climb 同构）+ 腿交替轻踢。"""
    act = begin("A_Swim"); n = 30
    FWD_L, PULL_L = (0.45, 0.10, 0.88), (0.50, -0.35, -0.79)   # 出手前伸 / 划回身侧
    FIN_L, FOUT_L = (0.75, -0.20, 0.63), (0.20, 0.15, 0.97)    # 前臂：随臂伸 / 收向腹下
    for f in range(n + 1):
        ph = 2 * math.pi * f / n
        kL = (1 + math.cos(ph)) / 2
        kR = (1 + math.cos(ph + math.pi)) / 2
        wrot("Spine", "Y", 52); wrot("Spine1", "Y", 10)
        walign2("LeftArm", nlerp(PULL_L, FWD_L, kL))
        walign2("RightArm", nlerp(mir(PULL_L), mir(FWD_L), kR))
        walign2("LeftForeArm", nlerp(FIN_L, FOUT_L, kL))
        walign2("RightForeArm", nlerp(mir(FIN_L), mir(FOUT_L), kR))
        wrot2("LeftUpLeg", [("X", LEG_IN_L), ("Y", -18 * math.sin(ph))])   # 轻踢
        wrot2("RightUpLeg", [("X", LEG_IN_R), ("Y", -18 * math.sin(ph + math.pi))])
        wrot("LeftLeg", "Y", 24 + 10 * max(0.0, math.sin(ph)))
        wrot("RightLeg", "Y", 24 + 10 * max(0.0, math.sin(ph + math.pi)))
        wrot("LeftFoot", "Y", FOOT_FIX); wrot("RightFoot", "Y", FOOT_FIX)
        key_all(f)
    return act
```

注册 acts/EXPECT(30)/SHOTS([0,7,15,22]) → 重跑（--skip-render 快验 + 全量渲染看 sheet）→ 拷贝 FBX。

- [ ] **Step 2: ThirdPersonController 加游泳（仿 climb 接管模式）**

```csharp
// 字段：
public float swimSpeed = 1.0f, swimDepth = 1.15f;   // 泳速 / 原点沉入水面深度（水面约在胸口）
public bool Swimming { get; private set; }
WaterVolume water;

// Awake 追加：water = WaterVolume.Instance; （Instance 可能后注册——Update 里再兜底）

// Update 开头（climb 分支之前）插入：
UpdateSwim();
if (Swimming) { TickSwim(); SyncAnimator(); return; }

// 新方法：
void UpdateSwim()
{
    if (water == null) water = WaterVolume.Instance;
    if (water == null) { Swimming = false; return; }
    bool inside = water.Contains(transform.position);
    if (!Swimming && inside && !(climb && climb.IsClimbing))
    {
        Swimming = true; velocityY = 0f;
        AudioManager.Instance?.Splash();
    }
    else if (Swimming && !inside) Swimming = false;   // 出区（上岸/离河）：重力接管
}

void TickSwim()
{
    float h = Input.GetAxisRaw("Horizontal"), v = Input.GetAxisRaw("Vertical");
    float yaw = cameraPivot ? cameraPivot.eulerAngles.y : 0f;
    Vector3 dir = Quaternion.Euler(0, yaw, 0) * new Vector3(h, 0, v);
    if (dir.sqrMagnitude > 1f) dir.Normalize();
    if (dir.sqrMagnitude > 0.01f)
    {
        var look = Quaternion.LookRotation(dir);
        transform.rotation = Quaternion.Slerp(transform.rotation, look, turnLerp * Time.deltaTime);
    }
    Vector3 move = dir * swimSpeed;
    float targetY = water.waterLevel - swimDepth + 0.04f * Mathf.Sin(Time.time * 2.2f);   // 固定浮升+微浮沉
    move.y = (targetY - transform.position.y) * 4f;                                       // 弹性逼近（受河床物理限制）
    cc.Move(move * Time.deltaTime);
}

// SyncAnimator 追加：
anim.SetBool("swimming", Swimming);
```

- [ ] **Step 3: AnimatorSetup 加 Swim**

```csharp
ctrl.AddParameter("swimming", AnimatorControllerParameterType.Bool);
var swim = sm.AddState("Swim"); swim.motion = clips["A_Swim"]; swim.speed = 1.0f;
T(idle, swim, "swimming", AnimatorConditionMode.If, 0f);
T(walk, swim, "swimming", AnimatorConditionMode.If, 0f);
T(run, swim, "swimming", AnimatorConditionMode.If, 0f);
T(swim, idle, "swimming", AnimatorConditionMode.IfNot, 0f);
```

AudioManager：`Splash()`（复用 `land` clip 低音量 0.15，或 AudioWiring 新合成——先复用 land）。重跑 Animator 两菜单。

- [ ] **Step 4: Play 验证（先败后成）**

① 传送北岸 `(0,-1.4,120)` 向北走入水：断言 `Swimming==true`；② 松手 5s：断言 y 稳定在 `max(-3.75, 河床)` ±0.15（浮水面行为）；③ 按 W 游到 z>176：断言上岸 `Swimming==false`、y 回升到岸面；④ 截图：入水瞬间 / 河中游动（俯视机位）/ 上岸各 1 张。

- [ ] **Step 5: Commit**

```bash
git add blender_assets/scripts/hero_anims.py blender_assets/export/characters/SK_Explorer.fbx game/3D-Demo/Assets/Art/Characters/SK_Explorer.fbx game/3D-Demo/Assets/Scripts/ThirdPersonController.cs game/3D-Demo/Assets/Editor/AnimatorSetup.cs game/3D-Demo/Assets/Scripts/AudioManager.cs docs/milestones/M6/
git commit -m "feat(M6-4): 游泳状态（固定浮水面+划水+自动上岸）与 A_Swim 动画"
```

---

## Milestone M6-5：爬绳上崖

> 里程碑目标：**斜绳横跨深渊**——南岸崖边按 W 抓绳、沿绳爬升横越到对岸崖顶；**绳下即深渊，松手坠入即死**（死亡判定 M6-7 接入）。**完成后停下汇报等待确认。**

### Task 15: 绳索资产 + 崖壁摆放

**Files:**
- Modify: `blender_assets/scripts/outdoor_props.py`（新增 `SM_Rope` / `SM_Stake`）
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（追加 `BuildRope()` / `BuildAbyssMist()`）
- Create: `game/3D-Demo/Assets/Scripts/MistDrift.cs`（深渊雾层浮动）

**Interfaces:**
- Produces: `SM_Rope`（长 22.7m 直绳，**原点在绳底端**，几何沿本地 +Y 延伸；φ 6cm + 三段螺旋纹）；`SM_Stake`（锚桩，原点=桩底，高 0.5m）；`OUT_Rope_1`（斜跨深渊：南端 `(0, -1.0, 193.5)` → 北端 `(0, 3.4, 215.8)`，对象位置=南端、旋转 `FromToRotation(up, 北-南)`）；`M_Mist`（URP Unlit 透明深灰蓝，资产化）+ `OUT_Mist_1~4`（深渊雾层薄板 y -3/-10/-17/-24，alpha 0.25→0.8 渐没入黑暗）+ `MistDrift`（雾层浮动/呼吸）
- Consumes: Task 1 深渊几何（南岸高台 -1.5 至 z=194、深渊底 -32、崖顶 y=3 起于 z≈216）

- [ ] **Step 1: outdoor_props.py 追加两件**

SM_Rope：主体圆柱（r 0.030，**长 22.7m 沿本地 +Y、40 段**）+ 三股螺旋细棱（每段螺旋半径 0.036/管径 0.011，~1200 tris）；`M_Rope`（(0.45,0.36,0.22) rough 0.95）。**原点=绳南底端**（对象位置即南端锚点，斜向由旋转给出）。SM_Stake：圆柱 r0.05 h0.5（**原点=桩底**）+ 顶环（~400 tris），`M_Metal_Dark`。导出 + 渲染绳特写到 `docs/milestones/M6/rope.png` → 拷贝 FBX。

- [ ] **Step 2: OutdoorBuilder 追加 BuildRope()**

```csharp
// 斜绳横跨深渊：南端锚点 (0, -1.0, 193.5)（南岸高台 -1.5 的崖边；桩底着地、桩顶 -1.0 即绳南端）；
// 北端锚点 (0, 3.4, 215.8)（崖顶 y=3 起于 z≈216，215.8 处地形 ≈2.94；北桩底 2.94、桩顶 3.44）。
// SM_Rope 原点在南底端、几何沿本地 +Y 长 22.7m；旋转 FromToRotation(up, 北-南) 即斜跨深渊。
static void BuildRope()
{
    InstantiateFbxNoCollider("SM_Stake", new Vector3(0f, -1.5f, 193.5f));    // 南端桩（崖边）
    InstantiateFbxNoCollider("SM_Stake", new Vector3(0f, 2.94f, 215.8f));    // 北端桩（崖顶）
    var rope = InstantiateFbxNoCollider("SM_Rope", new Vector3(0f, -1.0f, 193.5f));
    rope.name = "OUT_Rope_1";                 // 绳本体不加碰撞（爬绳走 RopeSystem 状态判定）
    Vector3 north = new Vector3(0f, 3.4f, 215.8f) - rope.transform.position;   // 南→北斜向
    rope.transform.rotation = Quaternion.FromToRotation(Vector3.up, north.normalized);
}
```

（`InstantiateFbxNoCollider`=Task 2 的 `InstantiateFbx` 去掉 MeshCollider 与静态标记的变体——追加助手。）

**深渊雾层（同 Step 追加）**：`Build()` 中在 `BuildRope()` 后调用 `BuildAbyssMist()`——4 层水平薄雾板让深渊“看不见底”（从崖边俯瞰：雾渐没入黑暗）。雾板会动 → **不标静态、关阴影**（M5 静态批处理教训）。

```csharp
// 深渊雾层：4 层水平薄雾板（Cube 薄板 36×0.06×14）从上到下渐浓没入黑暗——“看不见底”。
// 透明材质共享 M_Mist；雾板会动（MistDrift 浮动）→ 不标静态、关阴影。
static void BuildAbyssMist()
{
    var mat = GetOrCreateMistMat();
    float[] ys = { -3f, -10f, -17f, -24f };
    float[] alphas = { 0.25f, 0.45f, 0.62f, 0.8f };
    for (int i = 0; i < ys.Length; i++)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = "OUT_Mist_" + (i + 1);
        Object.DestroyImmediate(go.GetComponent<BoxCollider>());                 // 不参与碰撞
        go.transform.position = new Vector3(0f, ys[i], 201f);                   // 深渊带 z 194-208 中心
        go.transform.localScale = new Vector3(36f, 0.06f, 14f);
        var r = go.GetComponent<MeshRenderer>();
        r.sharedMaterial = mat;
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        r.receiveShadows = false;
        go.AddComponent<MistDrift>().alphaBase = alphas[i];
    }
}

static Material GetOrCreateMistMat()   // 仿 M_Flame 的资产化模式
{
    const string path = "Assets/Art/Static/outdoor/M_Mist.mat";
    var m = AssetDatabase.LoadAssetAtPath<Material>(path);
    if (m != null) return m;
    m = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
    m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 0f);                       // 透明/Alpha
    m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
    m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
    m.SetFloat("_ZWrite", 0f); m.renderQueue = 3000;
    m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
    m.SetColor("_BaseColor", new Color(0.08f, 0.09f, 0.12f, 0.5f));            // 深灰蓝（MPB 覆写 alpha）
    AssetDatabase.CreateAsset(m, path);
    return m;
}
```

**MistDrift.cs**（新建，仿 FireFlicker 的极简结构）：

```csharp
using UnityEngine;
// M6-5: 深渊雾层漂移——慢速上下浮动 + alpha 呼吸（相位随实例错开）。
public class MistDrift : MonoBehaviour
{
    public float bobAmp = 0.4f, bobSpeed = 0.15f, alphaBase = 0.5f, alphaAmp = 0.12f;
    Vector3 basePos; Color baseCol; float phase;
    Renderer r; MaterialPropertyBlock mpb;
    void Start()
    {
        basePos = transform.position; phase = Random.value * 6.28f;
        r = GetComponent<Renderer>(); mpb = new MaterialPropertyBlock();
        baseCol = r.sharedMaterial.GetColor("_BaseColor");      // 共享材质取底色
    }
    void Update()
    {
        transform.position = basePos + Vector3.up * (Mathf.Sin(Time.time * bobSpeed + phase) * bobAmp);
        var c = baseCol;
        c.a = Mathf.Clamp01(alphaBase + Mathf.Sin(Time.time * bobSpeed * 0.7f + phase) * alphaAmp);
        r.GetPropertyBlock(mpb); mpb.SetColor("_BaseColor", c); r.SetPropertyBlock(mpb);
    }
}
```

- [ ] **Step 3: 跑菜单 + 截图验证**

重跑 `Demo/构建户外场景`；Play 传送南岸高台 `(0,-1.4,188)` 向北：截图（崖边双桩+斜绳横跨全黑深渊+对岸崖壁）存 `docs/milestones/M6/rope_abyss.png`；再从崖边俯视深渊：截图（4 层漂浮雾渐没入黑暗、“看不见底”）存 `docs/milestones/M6/abyss_mist.png`。

- [ ] **Step 4: Commit**

```bash
git add blender_assets/scripts/outdoor_props.py game/3D-Demo/Assets/Editor/OutdoorBuilder.cs game/3D-Demo/Assets/Scripts/MistDrift.cs game/3D-Demo/Assets/Art/Static/outdoor/ docs/milestones/M6/rope.png docs/milestones/M6/rope_abyss.png docs/milestones/M6/abyss_mist.png
git commit -m "feat(M6-5): 绳索/锚桩资产 + 崖壁摆放 + 深渊漂浮雾层"
```

### Task 16: RopeSystem（抓绳/攀爬/顶翻越）

**Files:**
- Create: `game/3D-Demo/Assets/Scripts/RopeSystem.cs`
- Modify: `game/3D-Demo/Assets/Scripts/ThirdPersonController.cs`（绳态接管分支 + Animator climbing 合并）
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（绳对象挂 RopeSystem）

**Interfaces:**
- Produces: `RopeSystem.IsRoping`（public 只读）；攀爬时复用 `climbing` Animator 参数（与 ClimbSystem 共用 A_Climb 动画）
- Consumes: Task 15 的 `OUT_Rope_1`（Transform 原点=绳南底端，本地 up=斜绳轴向）；现有 `ClimbSystem` 的接管写法

- [ ] **Step 1: 写 RopeSystem.cs**

```csharp
using UnityEngine;
// M6-5: 爬绳（斜绳横跨深渊版）——靠近绳南端+按 W+面向绳 → 抓绳（投影吸附到绳轴）。
// 轴=本地 up（对象已旋转，即南→北斜向）；W/S 沿轴上下；到北端自动顶翻越上崖顶；
// 空格=松手坠落（绳下即深渊，坠入由 M6-7 的 AbyssVolume 判死）；S 回到南端落地。
// 结构仿 ClimbSystem；挂在绳对象上（对象原点=绳南底端；本组件不在玩家上，运行时查 Player）。
public class RopeSystem : MonoBehaviour
{
    public float ropeLength = 22.7f;                       // 南端原点沿 +up（斜向）全长
    public float grabRadius = 0.85f, climbSpeed = 2.0f, topOutSpeed = 2.0f;
    public float hangOffset = 0.9f, sideOffset = 0.25f;    // 吊挂姿态：身体在轴点下 0.9m、侧偏 0.25m（渲染后校准）
    public bool IsRoping { get; private set; }
    public static RopeSystem Active;                       // TPC 分支用（组件在绳上而非玩家）

    CharacterController cc;
    Transform playerT;
    float ropeT;                                           // 攀爬进度（沿轴米数）
    bool topping; float topT; Vector3 topFrom, topTo;

    Vector3 Axis => transform.up;                          // 斜绳轴（南→北向上）

    void Update()
    {
        if (!playerT)
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            if (!p) return;
            playerT = p.transform; cc = p.GetComponent<CharacterController>();
        }
        if (IsRoping) { TickRope(); return; }

        // 抓绳条件：离绳轴最近点 < grabRadius；处于绳底段（t<3，只能从南端上绳）；按 W；面向绳
        Vector3 rel = playerT.position - transform.position;
        float t = Mathf.Clamp(Vector3.Dot(rel, Axis), 0f, ropeLength);
        Vector3 near = transform.position + Axis * t;
        if ((playerT.position - near).magnitude > grabRadius || t > 3f) return;
        if (Input.GetAxisRaw("Vertical") <= 0.1f) return;
        Vector3 face = near - playerT.position; face.y = 0f;
        if (face.sqrMagnitude < 0.001f) return;
        face.Normalize();
        if (Vector3.Dot(playerT.forward, face) < 0.4f) return;
        IsRoping = true; Active = this; ropeT = t;
        SnapToRope(face);
    }

    void SnapToRope(Vector3 face)
    {
        Vector3 target = RopePoint(ropeT) - face * sideOffset;   // 站在绳的来侧 0.25m
        target.y -= hangOffset;                                  // 吊挂：身体在轴点下 0.9m
        cc.Move(target - playerT.position);
        Vector3 f = Axis; f.y = 0f;
        playerT.rotation = Quaternion.LookRotation(f.normalized, Vector3.up);   // 面朝行进方向（北）
    }

    Vector3 RopePoint(float t) => transform.position + Axis * t;

    void TickRope()
    {
        if (topping)
        {
            topT += Time.deltaTime * topOutSpeed;
            float k = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(topT));
            cc.Move(Vector3.Lerp(topFrom, topTo, k) - playerT.position);
            if (topT >= 1f) { topping = false; IsRoping = false; Active = null; }
            return;
        }

        if (Input.GetButtonDown("Jump")) { IsRoping = false; Active = null; return; }   // 空格松手坠落
        float v = Input.GetAxisRaw("Vertical");

        // 北端到顶：进度达全长 → 翻越上崖顶（崖顶地面 y=3，落点 z≈216.3）
        if (v > 0.1f && ropeT >= ropeLength - 0.4f)
        {
            topping = true; topT = 0f;
            topFrom = playerT.position;
            topTo = new Vector3(transform.position.x, 3.05f, 216.3f);
            return;
        }
        // 南端到底：S 持续 → 落地松手（站回南岸崖边）
        if (v < -0.1f && ropeT <= 0.15f) { IsRoping = false; Active = null; return; }

        ropeT = Mathf.Clamp(ropeT + v * climbSpeed * Time.deltaTime, 0f, ropeLength);
        Vector3 face = Axis; face.y = 0f;
        SnapToRope(face.normalized);
    }
}
```

- [ ] **Step 2: ThirdPersonController 集成**

```csharp
// 字段：RopeSystem rope;
// Start 追加：rope = GetComponent<RopeSystem>();   // ——不对：RopeSystem 挂在绳对象上！
```

**修正**：RopeSystem 不属于 Player，TPC 无法 `GetComponent` 拿它。改为：RopeSystem 抓绳时向 Player 暴露静态引用或事件——**最简做法：RopeSystem 提供 `public static RopeSystem Active`**（BeginRope 时赋值 Instance/Active=this，松手置 null）。TPC 分支：

```csharp
var rope = RopeSystem.Active;
if ((climb && climb.IsClimbing) || (rope && rope.IsRoping)) { velocityY = 0f; airLocked = false; SyncAnimator(); return; }
```

SyncAnimator：`anim.SetBool("climbing", (climb && climb.IsClimbing) || (RopeSystem.Active && RopeSystem.Active.IsRoping));`

其余 TPC 改动为两行替换（climb 分支条件 + SyncAnimator）。`public static RopeSystem Active` 已在 Step 1 代码内置（抓绳设 this；两处松手/翻越完成置 null）。

- [ ] **Step 3: OutdoorBuilder：绳对象挂 RopeSystem**

`BuildRope()` 中绳对象附加：`rope.AddComponent<RopeSystem>();`（`ropeLength=22.7` / `climbSpeed=2.0` 均为组件默认值，无需额外赋值）。重跑菜单保存。

- [ ] **Step 4: Play 验证（先败后成）**

① 传送南岸高台 `(0,-1.4,188)` 朝北：断言 `RopeSystem.Active==null`（未抓）；② 按 W 走近崖边绳南端：断言抓绳（`Active.IsRoping==true`）；③ 持续 W：断言沿轴爬升：z 从 ≈193.5 递增至 ≈215.8、y 从 ≈-0.6 递增至 ≈2.5，到北端自动翻越后 `IsRoping==false`、站上崖顶（y≈3.05、z≈216.3）；④ **松手验证**：爬至中段（`ropeT`≈11）按空格 → 断言坠落开始（`IsRoping==false`、y 递减；坠入深渊即死由 M6-7 的 AbyssVolume 接管——到时此步升级为死亡断言）；⑤ 截图：抓绳中 / 半空横越（俯视下方深渊）/ 登顶远眺各 1 张。

- [ ] **Step 5: Commit**

```bash
git add game/3D-Demo/Assets/Scripts/RopeSystem.cs game/3D-Demo/Assets/Scripts/ThirdPersonController.cs game/3D-Demo/Assets/Editor/OutdoorBuilder.cs docs/milestones/M6/
git commit -m "feat(M6-5): RopeSystem 爬绳（吸附/上下爬/顶翻越）+ TPC 接管集成"
```

---

## Milestone M6-6：崖顶遗迹与检查点

> 里程碑目标：崖顶遗迹区（残墙/断柱/拱门/火盆）可探索，走到终点触发"序章完成"；沿路火盆=检查点（走近自动记录+提示）。**完成后停下汇报等待确认。**

### Task 17: 崖顶遗迹 + 终点触发

**Files:**
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（追加 `BuildRuins()`）
- Modify: `game/3D-Demo/Assets/Scripts/GoalTrigger.cs`（文案参数化）
- Modify: `game/3D-Demo/Assets/Scripts/SimpleUI.cs`（`ShowComplete(string)` 重载）

**Interfaces:**
- Produces: `OUT_Ruins_*` 组（崖顶 y=3、z 216-254：残墙 4 段/断柱 4/拱门 1/后续 Task 18 的火盆 1）；`OUT_Goal`（空对象 + GoalTrigger radius=2，文案"序章完成\n你走出了峡谷"）
- Consumes: 现有 `SM_Wall_C/D`、`SM_Pillar_Broken`、`SM_Arch` FBX（复用 temple 套件）

- [ ] **Step 1: GoalTrigger/SimpleUI 文案参数化（向后兼容）**

```csharp
// GoalTrigger 加字段：
public string message = "探索完成！\n你取得了圣物";   // 默认=原宝物文案（向后兼容）
// 触发处改： SimpleUI.Instance.ShowComplete(message);

// SimpleUI 改：
public void ShowComplete(string title) { if (complete) { complete.text = title; complete.gameObject.SetActive(true); } SetObjective(""); }
public void ShowComplete() => ShowComplete("探索完成！\n你取得了圣物");   // 旧调用保留
```

- [ ] **Step 2: OutdoorBuilder 追加 BuildRuins()**

```csharp
// 崖顶遗迹（地形平台 y=3、z 216-254）：残墙半高缩放（2.5m）沿边摆；断柱散布；拱门在 (0,3,238)；
// 终点空对象 (0,3,242) + GoalTrigger{radius=2, message="序章完成\n你走出了峡谷"}。
// 全部静态件标 BatchingStatic（无运行时位移）。
static void BuildRuins()
{
    MakeStone("OUT_Ruins_Wall1", "SM_Wall_C", new Vector3(-8f, 3f, 224f), 90f, 0.42f);   // 0.42≈半高缩放
    MakeStone("OUT_Ruins_Wall2", "SM_Wall_D", new Vector3(8f, 3f, 224f), -90f, 0.42f);
    MakeStone("OUT_Ruins_Wall3", "SM_Wall_A", new Vector3(0f, 3f, 252f), 0f, 0.42f);
    MakeStone("OUT_Ruins_Wall4", "SM_Wall_B", new Vector3(-10f, 3f, 240f), 90f, 0.42f);
    MakeStone("OUT_Ruins_Pillar1", "SM_Pillar_Broken", new Vector3(-5f, 3f, 232f), 0f, 1f);
    MakeStone("OUT_Ruins_Pillar2", "SM_Pillar_Broken", new Vector3(5f, 3f, 228f), 40f, 1f);
    MakeStone("OUT_Ruins_Pillar3", "SM_Pillar_Broken", new Vector3(-4f, 3f, 246f), 80f, 1f);
    MakeStone("OUT_Ruins_Pillar4", "SM_Pillar_Whole", new Vector3(4f, 3f, 248f), 0f, 1f);
    MakeStone("OUT_Ruins_Arch", "SM_Arch", new Vector3(0f, 3f, 238f), 0f, 1f);
    var goal = new GameObject("OUT_Goal");
    goal.transform.position = new Vector3(0f, 3f, 242f);
    var gt = goal.AddComponent<GoalTrigger>(); gt.radius = 2f;
    gt.message = "序章完成\n你走出了峡谷";
}
// MakeStone = 通用助手：InstantiateFbx + 位置/朝向/缩放 + BatchingStatic（与 InstantiateFbx 合流，加 rot/scale 参数即可）
```

- [ ] **Step 3: 跑菜单 + Play 验证 + 截图**

重跑 `Demo/构建户外场景`；传送 `(0, 3.2, 220)` 向北走到 (0,3,242)：断言 `SimpleUI` 完成面板出现（complete 文本="序章完成…"）。截图：遗迹全景 / 拱门 / 完成面板各 1 张。

- [ ] **Step 4: Commit**

```bash
git add game/3D-Demo/Assets/Editor/OutdoorBuilder.cs game/3D-Demo/Assets/Scripts/GoalTrigger.cs game/3D-Demo/Assets/Scripts/SimpleUI.cs docs/milestones/M6/
git commit -m "feat(M6-6): 崖顶遗迹（残墙/断柱/拱门）+ 终点触发文案参数化"
```

### Task 18: 火盆检查点（沿路三座 + 走近记录提示）

**Files:**
- Create: `game/3D-Demo/Assets/Scripts/CheckpointSystem.cs`
- Modify: `game/3D-Demo/Assets/Scripts/SimpleUI.cs`（+`Flash(string)`）
- Modify: `game/3D-Demo/Assets/Scripts/AudioManager.cs`（+`Checkpoint()`）
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（追加 `BuildCheckpoints()`）

**Interfaces:**
- Produces: `CheckpointSystem.Respawn`（static Vector3）/ `HasCheckpoint`（static bool）；`SimpleUI.Flash(string)`（中下小字 2s 淡出）；`OUT_Brazier_Cp1/2/3`（草原 (3.5,-1.5,72) / 河谷北岸 (-3,-1.5,180) / 崖顶遗迹 (4,3,232)）——每座=SM_Brazier + 火焰球（`M_Flame`）+ 点光 `Torch_M6_*`
- Consumes: temple 的 `SM_Brazier` FBX；M5 的 FireFlicker/Bloom 氛围链路（`Torch` 前缀命名即被 `Tools/M5/Setup Atmosphere` 幂等接管）

- [ ] **Step 1: 写 CheckpointSystem.cs**

```csharp
using UnityEngine;
// M6-6: 火盆检查点——走近 2.5m 自动记录复活点（一期仅运行时内存，不写盘）+ 提示+音效。
// 视觉语言：火盆常燃=沿路光源与路标；三期末将升级为 F 互动点燃特写（见 spec 4.4）。
public class CheckpointSystem : MonoBehaviour
{
    public static Vector3 Respawn;
    public static bool HasCheckpoint;

    Transform player;
    void Update()
    {
        if (!player) { var p = GameObject.FindGameObjectWithTag("Player"); if (p) player = p.transform; }
        if (!player) return;
        if (Vector3.Distance(player.position, transform.position) > 2.5f) return;
        if (HasCheckpoint && Vector3.Distance(Respawn, transform.position) < 0.5f) return;  // 本点已记录
        Respawn = player.position;
        HasCheckpoint = true;
        SimpleUI.Instance?.Flash("检查点已记录");
        AudioManager.Instance?.Checkpoint();
    }
}
```

- [ ] **Step 2: SimpleUI.Flash + AudioManager.Checkpoint**

```csharp
// SimpleUI 追加（字段区加 Transform hudRoot；Awake 构建 canvas 后存 hudRoot = canvasGo.transform）：
Text flash;
public void Flash(string s)
{
    if (flash == null)
    {
        flash = MakeText(hudRoot, Vector2.zero, TextAnchor.LowerCenter, "", 30);
        var rt = flash.rectTransform;
        rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0f); rt.pivot = new Vector2(0.5f, 0f);
        rt.anchoredPosition = new Vector2(0, 160); rt.sizeDelta = new Vector2(900, 60);
    }
    StopCoroutine(nameof(FlashFade)); flash.text = s; flash.color = Color.white;
    StartCoroutine(nameof(FlashFade));
}
System.Collections.IEnumerator FlashFade()
{
    yield return new WaitForSecondsRealtime(1.6f);   // 暂停(timeScale=0)期间也能计时
    for (float a = 1f; a > 0f; a -= Time.unscaledDeltaTime * 1.5f) { flash.color = new Color(1, 1, 1, a); yield return null; }
}

// AudioManager 追加：
public void Checkpoint() => OneShot(goalChime, 0.6f);   // 复用完成钟声低音量（区分强弱）
```

- [ ] **Step 3: OutdoorBuilder 追加 BuildCheckpoints()**

```csharp
// 沿路三座火盆检查点。火盆=父空对象（OUT_Brazier_CpN）+ SM_Brazier(fbx) + 火焰球(Sphere, M_Flame)
// + 点光（命名 Torch_M6_N，供 FireFlicker/Bloom 链路）+ CheckpointSystem。
static void BuildCheckpoints()
{
    Brazier("OUT_Brazier_Cp1", new Vector3(3.5f, -1.5f, 72f));
    Brazier("OUT_Brazier_Cp2", new Vector3(-3f, -1.5f, 180f));
    Brazier("OUT_Brazier_Cp3", new Vector3(4f, 3f, 232f));
}
static void Brazier(string name, Vector3 pos)
{
    var root = new GameObject(name); root.transform.position = pos;
    var mesh = (GameObject)PrefabUtility.InstantiatePrefab(
        AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Static/temple/SM_Brazier.fbx"));
    mesh.transform.SetParent(root.transform, false);
    var flame = GameObject.CreatePrimitive(PrimitiveType.Sphere);
    Object.DestroyImmediate(flame.GetComponent<Collider>());
    flame.name = "Flame"; flame.transform.SetParent(root.transform, false);
    flame.transform.localPosition = new Vector3(0, 1.02f, 0);
    flame.transform.localScale = Vector3.one * 0.35f;
    flame.GetComponent<MeshRenderer>().sharedMaterial = GetOrCreateFlameMat();
    var lt = new GameObject("Torch_" + name.Replace("OUT_Brazier_", "")).AddComponent<Light>();
    lt.transform.SetParent(root.transform, false); lt.transform.localPosition = new Vector3(0, 1.25f, 0);
    lt.type = LightType.Point; lt.color = new Color(1f, 0.6f, 0.3f); lt.intensity = 6f; lt.range = 12f;
    lt.gameObject.AddComponent<FireFlicker>();
    root.AddComponent<CheckpointSystem>();
}
// GetOrCreateFlameMat：Assets/Art/Static/outdoor/M_Flame.mat（URP/Unlit，_BaseColor=HDR 橙 (3,1.6,0.5)）
```

（跑一次 `Tools/M5/Setup Atmosphere` 让 Bloom 链路对新 Torch 生效；该菜单幂等。）

- [ ] **Step 4: Play 验证 + 截图**

① 传送 `(0,-1.4,68)` 走向 Cp1：断言 `CheckpointSystem.HasCheckpoint==true` 且 `Respawn≈(3.5,…,72)` 附近；截图 Flash 提示（1 张）；② 再走远再回来：断言不重复触发（Respawn 不变）。

- [ ] **Step 5: Commit**

```bash
git add game/3D-Demo/Assets/Scripts/CheckpointSystem.cs game/3D-Demo/Assets/Scripts/SimpleUI.cs game/3D-Demo/Assets/Scripts/AudioManager.cs game/3D-Demo/Assets/Editor/OutdoorBuilder.cs game/3D-Demo/Assets/Art/Static/outdoor/M_Flame.mat docs/milestones/M6/
git commit -m "feat(M6-6): 火盆检查点×3（走近记录+Flash 提示）+ 沿路火光"
```

---

## Milestone M6-7：血条 / 摔伤 / 死亡重生 / ESC 菜单

> 里程碑目标：血条 HUD；摔落伤害 + 深渊即死 + 只狼风死亡黑屏 + 检查点重生；ESC 暂停菜单（继续/退出生效，保存与回档灰置）。**完成后停下汇报等待确认。**

### Task 19: 血条 + 摔落伤害 + 死亡重生

**Files:**
- Create: `game/3D-Demo/Assets/Scripts/PlayerHealth.cs`
- Create: `game/3D-Demo/Assets/Scripts/AbyssVolume.cs`（深渊即死区）
- Modify: `game/3D-Demo/Assets/Scripts/SimpleUI.cs`（+血条 +死亡黑幕）
- Modify: `game/3D-Demo/Assets/Scripts/AudioManager.cs`（+`Damage()`）
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（接线 PlayerHealth 进 Player——或并入 Task 2 的 `InstantiateFbx` 段落的接线函数 `WirePlayerAddons()`）

**Interfaces:**
- Produces: `PlayerHealth.Hp / Damage(float) / Kill()`（深渊等无条件即死）；`AbyssVolume`（盒区判定：y<-4 且 z 194-208 坠入即死）；`SimpleUI.SetHealth(float01) / ShowDeath() / HideDeath()`（死亡黑幕=只狼风朱红双行大字“失足迷途／归火重启”）；`AudioManager.Damage()`
- Consumes: `CheckpointSystem.Respawn/HasCheckpoint`（Task 18）、`ThirdPersonController.Swimming`（Task 14）

- [ ] **Step 1: 写 PlayerHealth.cs**

```csharp
using System.Collections;
using UnityEngine;
// M6-7: 血量/摔落伤害/死亡重生。伤害面板=摔落（apex 落差>4.5m 起算，14 HP/m）；
// 死亡：禁控→只狼风黑幕（朱红楷体大字“失足迷途／归火重启”渐入）→2.4s 后回最近检查点（无检查点则出生点）→回满血。
public class PlayerHealth : MonoBehaviour
{
    public float max = 100f;
    public float fallSafe = 4.5f, fallDamagePerM = 14f;
    public float Hp { get; private set; }

    ThirdPersonController tpc;
    float apexY; bool falling;

    void Awake() { Hp = max; tpc = GetComponent<ThirdPersonController>(); }

    void Start()
    {
        if (!CheckpointSystem.HasCheckpoint) CheckpointSystem.Respawn = transform.position;   // 无检查点=出生点
        SimpleUI.Instance?.SetHealth(1f);
    }

    void Update()
    {
        if (Hp <= 0f) return;
        var cc = GetComponent<CharacterController>();
        if (tpc && tpc.Swimming) { falling = false; apexY = transform.position.y; return; }   // 泳态不计落差
        if (!cc.isGrounded) { apexY = Mathf.Max(apexY, transform.position.y); falling = true; }
        else if (falling)
        {
            float drop = apexY - transform.position.y;
            falling = false; apexY = transform.position.y;
            if (drop > fallSafe) Damage((drop - fallSafe) * fallDamagePerM);
        }
    }

    public void Damage(float d)
    {
        if (Hp <= 0f) return;
        Hp = Mathf.Max(0f, Hp - d);
        SimpleUI.Instance?.SetHealth(Hp / max);
        SimpleUI.Instance?.Flash("-" + Mathf.RoundToInt(d));
        AudioManager.Instance?.Damage();
        if (Hp <= 0f) Die();
    }

    public void Kill()          // 坠入深渊等无条件即死（不按摔落落差，直接进入死亡流程）
    {
        if (Hp <= 0f) return;
        Hp = 0f;
        SimpleUI.Instance?.SetHealth(0f);
        Die();
    }

    void Die()
    {
        if (tpc) tpc.enabled = false;
        SimpleUI.Instance?.ShowDeath();
        Invoke(nameof(Respawn), 2.4f);
    }

    void Respawn()
    {
        transform.position = CheckpointSystem.Respawn + Vector3.up * 0.1f;
        Hp = max;
        SimpleUI.Instance?.SetHealth(1f);
        SimpleUI.Instance?.HideDeath();
        if (tpc) tpc.enabled = true;
    }
}
```

（注：死亡后位置用 `transform.position` 直设——CharacterController 会跟随 transform 传送，无需 disable CC。）

- [ ] **Step 2: SimpleUI 血条与死亡黑幕**

```csharp
// 血条（左上角，objective 下方）：两层 Image（底色 0.25 灰 / 填充红），Filled/Horizontal。
Image hpFill;
public void SetHealth(float k)
{
    if (hpFill == null)
    {
        var bg = MakeImage(hudRoot, new Vector2(24, -60), new Vector2(320, 22), new Color(0f, 0f, 0f, 0.45f));
        hpFill = MakeImage(bg.transform, Vector2.zero, new Vector2(316, 18), new Color(0.72f, 0.18f, 0.16f));
        hpFill.type = Image.Type.Filled; hpFill.fillMethod = Image.FillMethod.Horizontal; hpFill.fillAmount = 1f;
    }
    hpFill.fillAmount = Mathf.Clamp01(k);
    hpFill.color = k > 0.3f ? new Color(0.72f, 0.18f, 0.16f) : new Color(0.85f, 0.5f, 0.12f);   // 低血变橙
}
// 死亡黑幕（只狼风）：全屏黑幕 0.7s 渐入 → 两行朱红书法大字 0.5s 随后浮现——
// 上行“失足迷途”/ 下行“归火重启”（用户定稿文案），楷体优先逐级回退（KaiTi→STKaiti→SimSun→默认雅黑）；
// 全流程用 unscaledDeltaTime（与血条/Flash 同一节奏，不受 timeScale 影响）。
Image deathVeil; Text deathL1, deathL2; bool deathUIBuilt;
public void ShowDeath()
{
    EnsureDeathUI();
    deathVeil.gameObject.SetActive(true);
    StartCoroutine(DeathFade());
}
void EnsureDeathUI()
{
    if (deathUIBuilt) return;
    deathUIBuilt = true;
    var kai = Font.CreateDynamicFontFromOSFont(new[] { "KaiTi", "STKaiti", "SimSun" }, 80);
    if (!kai) kai = font;   // 回退默认雅黑
    deathVeil = MakeImage(hudRoot, Vector2.zero, Vector2.zero, new Color(0, 0, 0, 0));
    var vrt = deathVeil.rectTransform;
    vrt.anchorMin = Vector2.zero; vrt.anchorMax = Vector2.one;   // 全屏拉伸
    vrt.offsetMin = vrt.offsetMax = Vector2.zero;
    deathL1 = MakeBigText(kai, "失足迷途", new Vector2(0, 70));
    deathL2 = MakeBigText(kai, "归火重启", new Vector2(0, -50));
    deathVeil.gameObject.SetActive(false);
}
Text MakeBigText(Font f, string s, Vector2 pos)
{
    var t = MakeText(deathVeil.transform, Vector2.zero, TextAnchor.MiddleCenter, s, 80);
    t.font = f; t.color = new Color(0.62f, 0.14f, 0.12f, 0f);    // 朱红（只狼“死”字同系色）
    var rt = t.rectTransform;
    rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f); rt.pivot = new Vector2(0.5f, 0.5f);
    rt.anchoredPosition = pos; rt.sizeDelta = new Vector2(700, 110);
    return t;
}
System.Collections.IEnumerator DeathFade()
{
    for (float t = 0; t < 1f; t += Time.unscaledDeltaTime / 0.7f)          // 黑幕 0.7s
    { deathVeil.color = new Color(0, 0, 0, 0.9f * Mathf.SmoothStep(0f, 1f, t)); yield return null; }
    deathVeil.color = new Color(0, 0, 0, 0.9f);
    for (float t = 0; t < 1f; t += Time.unscaledDeltaTime / 0.5f)          // 文字 0.5s 随后浮现
    {
        float a = Mathf.SmoothStep(0f, 1f, t);
        deathL1.color = deathL2.color = new Color(0.62f, 0.14f, 0.12f, a);
        yield return null;
    }
}
public void HideDeath()
{
    if (!deathUIBuilt) return;
    deathVeil.gameObject.SetActive(false);
    deathVeil.color = new Color(0, 0, 0, 0);
    deathL1.color = deathL2.color = new Color(0.62f, 0.14f, 0.12f, 0f);
}
// MakeImage 助手：new GameObject(name, typeof(Image)) + SetParent + RectTransform 配置（anchoredPosition/sizeDelta）
```

- [ ] **Step 3: AudioManager.Damage()**

```csharp
public void Damage() => OneShot(land, 0.5f);   // 复用落地实录音低音量（过渡方案，M6-8 打磨可换）
```

- [ ] **Step 4: AbyssVolume.cs + OutdoorBuilder 接线（`WirePlayerAddons()`，在 Build 末尾调用）**

**AbyssVolume.cs**（深渊即死区：盒心 (0,-20,201)、尺寸 (80,32,14) → z 194-208、|x|<40、y -36~-4）：

```csharp
using UnityEngine;
// M6-7: 深渊即死区——玩家进入盒区（坠入 y<-4）立即死亡，不等落地。
public class AbyssVolume : MonoBehaviour
{
    public Bounds box = new Bounds(new Vector3(0f, -20f, 201f), new Vector3(80f, 32f, 14f));
    PlayerHealth ph; Transform playerT;
    void Update()
    {
        if (!playerT)
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            if (!p) return;
            playerT = p.transform; ph = p.GetComponent<PlayerHealth>();
        }
        if (ph && box.Contains(playerT.position)) ph.Kill();
    }
}
```

`WirePlayerAddons()` 追加建区（幂等）：

```csharp
static void WirePlayerAddons()
{
    var player = GameObject.Find("Player");
    if (player == null) return;
    if (!player.GetComponent<PlayerHealth>()) player.AddComponent<PlayerHealth>();
    if (!player.GetComponent<Attack>())   // Task 11 的接线在此统一（幂等）
    {
        var atk = player.AddComponent<Attack>();
        atk.knifePrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Static/hero_props/SM_Knife.fbx");
    }
    if (!GameObject.Find("OUT_AbyssVolume"))
        new GameObject("OUT_AbyssVolume").AddComponent<AbyssVolume>();   // 默认盒=深渊带
}
```

- [ ] **Step 5: Play 验证（先败后成）**

① 跳下 3m 高台：断言无伤（落差 3m<4.5m，Hp=100）；② 传送 `(0, 8, 70)` 自由落体到草原（落差≈9.5m）：断言 Hp=100-(9.5-4.5)×14=30、血条变短、Flash"-70"；③ 再摔到死：断言黑幕渐入→朱红双行大字“失足迷途／归火重启”浮现（楷体）——**截死亡画面 1 张**；2.4s 后回到 Cp1 附近且 Hp=100。④ **深渊即死复验**：传送南岸高台 `(0, -1.4, 192)` 朝北走出崖边——断言坠入深渊带（y<-4）**瞬间**死亡（不等落地、不按落差）→“失足迷途／归火重启”黑幕 → 重生回 Cp2 `(-3,-1.5,180)` 附近；再验爬绳中段松手同样坠渊即死；⑤ 截图：血条（满/低血）1 张。

- [ ] **Step 6: Commit**

```bash
git add game/3D-Demo/Assets/Scripts/PlayerHealth.cs game/3D-Demo/Assets/Scripts/AbyssVolume.cs game/3D-Demo/Assets/Scripts/SimpleUI.cs game/3D-Demo/Assets/Scripts/AudioManager.cs game/3D-Demo/Assets/Editor/OutdoorBuilder.cs docs/milestones/M6/
git commit -m "feat(M6-7): 血条+摔落伤害+死亡重生（接检查点）"
```

### Task 20: ESC 暂停菜单

**Files:**
- Create: `game/3D-Demo/Assets/Scripts/PauseMenu.cs`
- Modify: `game/3D-Demo/Assets/Scripts/SimpleUI.cs`（+`BuildMenu()`/`ShowMenu(bool)`）
- Modify: `game/3D-Demo/Assets/Scripts/CameraFollow.cs`（暂停冻结）
- Modify: `game/3D-Demo/Assets/Editor/OutdoorBuilder.cs`（`WirePlayerAddons` 追加接线）

**Interfaces:**
- Produces: `PauseMenu`（ESC 切换暂停：`Time.timeScale 0/1`、光标解锁、面板显隐；保存/回档按钮灰置禁用）；`PauseMenu.Paused`（static 只读）
- Consumes: SimpleUI 构建的面板按钮

- [ ] **Step 1: 写 PauseMenu.cs**

```csharp
using UnityEngine;
// M6-7: ESC 暂停菜单——继续/退出生效；保存/回到存档点灰置（三期待存档系统接入）。
public class PauseMenu : MonoBehaviour
{
    public static bool Paused { get; private set; }

    void Update()
    {
        if (!Input.GetKeyDown(KeyCode.Escape)) return;
        SetPaused(!Paused);
    }

    void SetPaused(bool on)
    {
        Paused = on;
        Time.timeScale = on ? 0f : 1f;
        Cursor.lockState = on ? CursorLockMode.None : CursorLockMode.Locked;
        Cursor.visible = on;
        SimpleUI.Instance?.ShowMenu(on);
    }

    public void Resume() => SetPaused(false);

    public void Quit()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }
}
```

- [ ] **Step 2: SimpleUI 菜单面板**

```csharp
// 面板（全屏半透明黑 Image alpha 0.75）+ 标题"已暂停" + 四按钮：
// 继续（onClick=Resume）/ 保存（interactable=false）/ 回到存档点（interactable=false）/ 退出（onClick=Quit）
GameObject menuPanel;
public void ShowMenu(bool on) { if (menuPanel) menuPanel.SetActive(on); }
// BuildMenu 在 Awake 构建（默认隐藏）：
//   Button 用 Image(底色 0.15 灰) + 子 Text；按钮 RectTransform 竖直排列 (0, 60/-10/-80/-150)、尺寸 320×56。
//   接线：btn.onClick.AddListener(() => FindFirstObjectByType<PauseMenu>().Resume())（Unity 6 API；Quit 按钮同理接 .Quit()）。
```

- [ ] **Step 3: CameraFollow 暂停冻结 + 接线**

```csharp
// CameraFollow.LateUpdate 开头加：
if (Time.timeScale == 0f) return;      // M6-7: 暂停时不响应鼠标（Esc 解锁光标后防止视角漂移）
```

`WirePlayerAddons()` 追加：`if (!player.GetComponent<PauseMenu>()) player.AddComponent<PauseMenu>();`

- [ ] **Step 4: Play 验证 + 截图**

① ESC：断言 `Time.timeScale==0`、光标解锁、面板可见（截图 1 张）；② 点"继续"（MCP 直接调 `Resume()`）：断言恢复；③ 点"退出"（编辑器）：断言退出 Play；④ 移动/游泳/攀爬各态下 ESC 恢复后无卡死。

- [ ] **Step 5: Commit**

```bash
git add game/3D-Demo/Assets/Scripts/PauseMenu.cs game/3D-Demo/Assets/Scripts/SimpleUI.cs game/3D-Demo/Assets/Scripts/CameraFollow.cs game/3D-Demo/Assets/Editor/OutdoorBuilder.cs docs/milestones/M6/
git commit -m "feat(M6-7): ESC 暂停菜单（继续/退出生效，保存与回档灰置）"
```

---

## Milestone M6-8：打磨与一期交付

> 里程碑目标：性能达标（打包 ≥60fps）、Console 清零、真实打包冒烟（重点复检"模型与碰撞分离"类问题）、一期总验收、文档。**完成后停下汇报等待用户总验收。**

### Task 21: 性能与视觉打磨

**Files:**
- Modify: 视结果调整 `VegetationScatter.cs` 密度常量 / `OutdoorFxSetup.cs` 参数 / `OutdoorBuilder.cs` 摆位
- 产出: `docs/milestones/M6/perf.md`（采样记录）

**Interfaces:**
- Consumes: M5-5 采样法（Δ`Time.frameCount`/Δ`Time.realtimeSinceStartup`；`Profiler.GetTotalAllocatedMemoryLong()`+GC 对比）

- [ ] **Step 1: 三视点帧率采样**

草原 `(0,0,80)` 朝北 / 河谷 `(0,0,150)` / 崖顶 `(0,3,230)`：每点两轮采样记录到 `perf.md`。**编辑器态目标 ≥70fps**（留打包余量）。

- [ ] **Step 2: 达标调优（不达标时按序）**

① 草密度 4m→5m 格；② 雾 end 240→200；③ 树实体改 Instancing（材质 enableInstancing）；④ 阴影距离 `QualitySettings.shadowDistance` 100→60。每改一项重采样。

- [ ] **Step 3: 视觉微调（截图对比 2-3 轮）**

太阳强度/角度、雾色、曝光、草树分布观感——对照 spec"写实丛林"目标（观感≈85%）。关键镜头：出门第一眼（台阶下望草原）、河谷反光、绳区仰视、遗迹火盆。

- [ ] **Step 4: Console 清零三查（M5-5 口径）**

清空 → 编译 → Play 启动 → 全程运行——三段 0 Error / 0 Warning（MCP 工具自提示除外）。

- [ ] **Step 5: Commit**

```bash
git add docs/milestones/M6/perf.md game/3D-Demo/Assets/
git commit -m "feat(M6-8): 性能采样与打磨（帧率达标+视觉微调+Console 清零）"
```

### Task 22: 打包冒烟 + 一期总验收 + 文档

**Files:**
- 产出: `docs/milestones/M6/report.md`；Modify: `README.md`（键位/菜单/里程碑表）

**Interfaces:**
- Consumes: 全部前序任务

- [ ] **Step 1: 真实打包冒烟**

Build Settings 确认仅 `Demo.unity`；Build 到 `Builds/M6/demo.exe` 跑全程：出门→草原→蹲缝→砍藤→游河→爬绳→遗迹→终点。**重点复检**：① 模型与碰撞无分离（M5 静态批处理教训——火盆/藤/绳不标静态）；② 60fps+；③ 无报错日志。

- [ ] **Step 2: 用户总验收**

交付：打包 exe + 全流程截图集（`docs/milestones/M6/M6_acceptance/`）；列出已知不足（如音频为程序合成、火焰为发光球近似）。**等用户验收反馈**。

- [ ] **Step 3: 写 report.md + 更新 README**

report.md 结构：① 任务清单与完成状态；② 验收结果表；③ 修复记录（本里程碑内）；④ 性能数据；⑤ 已知不足与三期待办（火盆点燃特写改造见 spec 4.4）。README 更新：键位表（+C 蹲/左键挥刀/ESC）、角色能力表、里程碑状态表（+M6 一期）、文档索引。

- [ ] **Step 4: Commit**

```bash
git add docs/milestones/M6/report.md README.md
git commit -m "docs(M6-8): 一期验收报告 + README 更新"
```

---

## 计划自审（Self-Review）

**1. Spec 覆盖检查**
| Spec 要求 | 对应任务 |
|---|---|
| 七段关卡（出口楼梯/草原/岩缝/藤/河谷/深渊斜绳/崖顶遗迹） | T1-T3 / T5-T6 / T9 / T12 / T13 / T15-T16 / T17 |
| 蹲行（C，头顶净空限制） | T7-T8 |
| 挥刀（左键、前方判定、砍藤） | T10-T12 |
| 游泳（固定浮水面、划水、上岸、无消耗） | T13-T14 |
| 爬绳（靠近+前推抓、沿绳移动、顶翻越） | T15-T16 |
| 血条 + 摔落伤害 + 死亡重生 | T19 |
| 火盆检查点（一期走近自动记录+提示） | T18 |
| ESC 菜单（继续/退出生效；保存/回档灰置） | T20 |
| 写实丛林氛围（天空/雾/后处理/植被） | T4-T6 / T21 |
| 性能（打包 ≥60fps）与打包冒烟 | T21-T22 |
| 三期预留（火盆拆分为独立对象→点燃生长动画） | spec 4.4 已记录；本计划不实现（T18 注释指向） |
| 全程序化资产（Blender 自研） | T1/T5/T7/T10/T12/T15 全部 Blender 脚本 |
| 里程碑停检（用户约定） | M6-1~M6-8 各节尾任务内注明"停下汇报" |

**2. 占位符扫描**：所有 Task 的代码步骤均含可直接粘贴的实现或精确参数；无"TBD/稍后补充"。少数标注"执行时按渲染微调"的数值（蹲姿角度、A_Slash 帧窗、蹲行 state.speed）均为**带初值的校准步骤**且有验证图/断言，不属于占位符。

**3. 类型/接口一致性**：`Crouching`(T8)/`Swimming`(T14)/`IsRoping`(T16)/`RopeSystem.Active`(T16)/`CheckpointSystem.Respawn·HasCheckpoint`(T18)/`PlayerHealth.Hp·Damage`(T19)/`SimpleUI.SetHealth·Flash·ShowDeath·HideDeath·ShowMenu`(T18-T20)/`AudioManager.Chop·Splash·Checkpoint·Damage`(T12/T14/T18/T19)/`ICuttable.Cut(Vector3)`(T11-T12) 在定义与消费处逐一核对一致。

**4. 风险与回退**：URP Water 评估失败 → T13 已内置 URP Lit 透明兜底；蹲姿脚部穿地 → T7 渲染校准循环；握刀朝向 → T11 Play 校准步骤。
