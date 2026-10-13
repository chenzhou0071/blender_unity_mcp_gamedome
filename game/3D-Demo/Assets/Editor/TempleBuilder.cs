using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

// M6-1: 神庙重做——金字塔外壳 + 封顶大房间 + 楼梯间 + 前庭 + 出口衔接（菜单「Demo/重建神庙」）。
// 幂等：先拆旧（旧 A/B 厅灰盒 + 神庙区 z<24 的视觉件/火光），再按新布局重建；产物统一 Temple_* 前缀，重跑先清。
// 布局：金字塔 @(0,-0.02,6)（SM_Pyramid 原点=底边中心，北面 +z）；房间 x±12 / z±10、地板顶 y=6、天花 y=14；
// 石门在房间北墙 z=10；楼梯间 SM_GrandStair @(0,0,19) 自 z10(y6) 降至 z19(y0)；北门洞 z22~24；
// 前庭 z24~34；北缘 8 级 SM_Step 接峡谷坡道（y0→-1.5，z34→46）。
// 原则沿用 KitPlacer/OutdoorBuilder：逻辑件（StoneDoor/PressurePlate/PushBlock/Player 的脚本与碰撞）保留迁位；
// 新增视觉件一律实体（MeshCollider 非凸、静态）；会动的对象（石门视觉=石门子物）不标静态。
// 注：检查点火盆按名 Temple_BrazierHall/Court 保留给 Task 18 挂 CheckpointSystem——重跑本菜单会清 Temple_*，之后需补挂。
public static class TempleBuilder
{
    const string FbxDir = "Assets/Art/Static/temple";
    const string OutFbxDir = "Assets/Art/Static/outdoor";
    const string Scene = "Assets/Scenes/Demo.unity";
    // A/B 两种地砖模型厚度不同（实测顶面 A=pos+0.326 / B=pos+0.300，差 0.026）——
    // 棋盘交替铺设时须给 A 型下沉 0.026 找平，否则每块砖边界 2.6cm 高差，走路"一震一震"（用户 bug 实锤）
    const float TileATrim = 0.026f;

    static int seq;

    [MenuItem("Demo/重建神庙")]
    public static void Build()
    {
        EditorSceneManager.OpenScene(Scene, OpenSceneMode.Single);
        seq = 0;
        CleanupOld();
        BuildPyramid();
        BuildRoom();
        BuildStairwell();
        BuildForecourt();
        BuildTorchesAndBraziers();
        RelocateLogic();
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[TempleBuilder] 神庙重建完成（金字塔+房间+楼梯间+前庭）");
    }

    // ---------- ① 拆旧 ----------
    static void CleanupOld()
    {
        int n = 0;
        // 旧灰盒 A/B 厅（M3 起保留的逻辑体；被金字塔房间取代）
        string[] gray = { "ClimbableLedge", "Altar", "Treasure",
                          "WallA_S", "WallA_E", "WallA_W", "WallAB_L", "WallAB_R", "WallAB_Top",
                          "WallB_E", "WallB_W", "WallB_N", "FloorA", "FloorB" };
        foreach (var name in gray)
        {
            var go = GameObject.Find(name);
            if (go) { Object.DestroyImmediate(go); n++; }
        }
        // 神庙区（z<24）旧视觉件 VIZ_*（石门/压板/推块的跟随视觉是逻辑件子物，非根，不受影响）；
        // 旧火盆点光 TorchA_*；本菜单上次产物 Temple_*/Torch_*（火焰球为 Torch 子物随灭）
        var doomed = new List<GameObject>();
        foreach (var t in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (t == null || t.parent != null) continue;
            bool kill = (t.name.StartsWith("VIZ_") && t.position.z < 24f)
                     || t.name.StartsWith("Temple_") || t.name.StartsWith("Torch_")
                     || t.name is "TorchA_L" or "TorchA_R" or "TorchB_L" or "TorchB_R";
            if (kill) doomed.Add(t.gameObject);
        }
        foreach (var go in doomed) { Object.DestroyImmediate(go); n++; }
        if (n > 0) Debug.Log($"[TempleBuilder] 拆旧：清理 {n} 个对象");
    }

    // ---------- ② 金字塔外壳 ----------
    static void BuildPyramid()
    {
        // 沉 2cm：底边与大地坪顶面（GroundOutside 顶 -0.02）严丝合缝
        Solid("SM_Pyramid", new Vector3(0, -0.02f, 6f), 0f);
    }

    // ---------- ③ 房间内装（地板/周墙/天花/壁柱） ----------
    static void BuildRoom()
    {
        float F = LevelSpec.RoomFloorY, C = LevelSpec.RoomCeilY;   // 6 / 14
        // 地板：M5 同款 SM_FloorTile_A/B 2m 遗迹地砖满铺 24×20（A/B 交替 + 随机 90° 转向，顶面 y=6 与 FloorPad 齐平）
        // 物理面统一由 FloorPad（精确平面盒，顶=6.0）承接——地砖纯视觉不挂碰撞，与门/压板/出生点同体系
        //（原 SM_HallFloor 整块 + 中央 SM_FloorInlay 浮雕已弃用：浮雕网格顶面低于名义面，推块零接触会打滑）。
        // A 型找平（TileATrim）：否则 A 砖顶凸出 FloorPad 4.6cm，视觉上"脚陷进砖里"
        for (int i = 0; i < 12; i++)
            for (int j = 0; j < 10; j++)
            {
                bool isA = (i + j) % 2 == 0;
                var tile = Spawn(isA ? "SM_FloorTile_A" : "SM_FloorTile_B",
                                 new Vector3(-11f + 2f * i, F - 0.30f - (isA ? TileATrim : 0f), -9f + 2f * j), Random.Range(0, 4) * 90f);
                if (tile) { tile.name = $"Temple_HallTile_{i:00}{j:00}"; Static(tile); }
            }
        FloorPad();

        // 周墙：4m 墙段双层层叠（层1 基座 6 高 4.2 / 层2 基座 10 高 4，重叠 0.2 防装配缝透光；
        // 上层向外微推 12mm 防层间前表面共面闪烁）。内表面贴 x±12 / z±10。
        string prev = "";
        for (int layer = 0; layer < 2; layer++)
        {
            float y = layer == 0 ? F : F + 4f;
            float hz = (layer == 0 ? 4.2f : 4f) / 3.015f;   // 墙段原始高 3.015m
            float ex = layer == 0 ? 0f : 0.012f;            // 外推量（防共面）
            for (int i = 0; i < 6; i++)                     // 南墙（内朝 +z）
                prev = WallPiece(prev, new Vector3(-10f + 4f * i, y, -10.25f - ex), 0f, 4f, hz);
            for (int i = 0; i < 5; i++)                     // 东墙（内朝 -x）
                prev = WallPiece(prev, new Vector3(12.25f + ex, y, -8f + 4f * i), -90f, 4f, hz);
            for (int i = 0; i < 5; i++)                     // 西墙（内朝 +x）
                prev = WallPiece(prev, new Vector3(-12.25f - ex, y, -8f + 4f * i), 90f, 4f, hz);
            if (layer == 0)
            {
                for (int i = 0; i < 3; i++)                 // 北墙门洞两侧（门宽 3：留 x±1.5）
                {
                    prev = WallPiece(prev, new Vector3(-10.25f + 3.5f * i, y, 10.25f + ex), 180f, 3.5f, hz);
                    prev = WallPiece(prev, new Vector3(10.25f - 3.5f * i, y, 10.25f + ex), 180f, 3.5f, hz);
                }
            }
            else
            {
                for (int i = 0; i < 6; i++)                 // 北墙上层全幅（中央 3m 段即门楣）
                    prev = WallPiece(prev, new Vector3(-10f + 4f * i, y, 10.25f + ex), 180f, 4f, hz);
            }
        }

        // 天花：6×4 梁板件拼铺（原点=顶面中心 → y=14；4 列 × 5 行）
        for (int i = 0; i < 4; i++)
            for (int j = 0; j < 5; j++)
                Solid("SM_Ceiling_A", new Vector3(-9f + 6f * i, C, -8f + 4f * j), 0f);

        // 壁柱（沿内墙 4m 间隔，正面朝房间；南墙避让火盆、北墙避让门洞、东西墙各 5 根）
        foreach (var x in new[] { -8f, -4f, 4f, 8f })
        {
            Solid("SM_Pilaster", new Vector3(x, F, -9.67f), 0f);    // 南墙朝北
            Solid("SM_Pilaster", new Vector3(x, F, 9.67f), 180f);   // 北墙朝南
        }
        foreach (var z in new[] { -8f, -4f, 0f, 4f, 8f })
        {
            Solid("SM_Pilaster", new Vector3(-11.67f, F, z), 90f);  // 西墙朝东
            Solid("SM_Pilaster", new Vector3(11.67f, F, z), -90f);  // 东墙朝西
        }
    }

    // ---------- ④ 楼梯间（大楼梯 + 两侧内墙 + 封顶 + 门厅地砖） ----------
    static void BuildStairwell()
    {
        Solid("SM_GrandStair", new Vector3(0, 0, 19f), 0f);   // 原点=低端底中心；顶步 z10(y6) 接门
        // 两侧内墙 x=±5（z 10..22 各三段 ×2 层：基座 0/4.925 高 5.13，叠 0.2 → 总高 ~10 遮蔽视线）
        // + 楼梯两侧贴沿内墙 x=±2.55（内表面 x=±2.3 贴楼梯沿）：楼梯两侧原为 2.7m 宽敞开黑缝（大厅视角穿帮），
        //   砌内墙后从大厅/门厅完全看不到缝，楼梯保持 4.6m 宽不加宽。
        string prev = "";
        for (int layer = 0; layer < 2; layer++)
        {
            float y = layer == 0 ? 0f : 4.925f;
            float ex = layer == 0 ? 0f : 0.012f;
            for (int i = 0; i < 3; i++)
            {
                prev = WallPiece(prev, new Vector3(5.25f + ex, y, 12f + 4f * i), -90f, 4f, 1.7f);
                prev = WallPiece(prev, new Vector3(-5.25f - ex, y, 12f + 4f * i), 90f, 4f, 1.7f);
                prev = WallPiece(prev, new Vector3(2.55f + ex, y, 12f + 4f * i), -90f, 4f, 1.7f);
                prev = WallPiece(prev, new Vector3(-2.55f - ex, y, 12f + 4f * i), 90f, 4f, 1.7f);
            }
        }
        // 封顶：6 块 SM_Ceiling_A 拼盖 x±6 × z10..22（顶面 y=10.2，与内墙顶 10.05 咬合）——仰视不再见金字塔内壳黑块
        for (int i = 0; i < 2; i++)
            for (int j = 0; j < 3; j++)
                Solid("SM_Ceiling_A", new Vector3(-3f + 6f * i, 10.2f, 12f + 4f * j), 0f);
        // 坡底门厅地砖满铺 3×3（迭代 3 用户：不要偷工减料，可塞进墙里）：
        // x -3..3 两侧塞入内墙；z 18.5..24.5 南端抵楼梯第一级、北端贴门洞
        // 行 z=23.5 整体沉 1cm（顶 0.01）防门外与前庭地砖（顶 0.02）共面闪烁；其余行顶 y0.02
        // A 型找平（TileATrim）：消除 A/B 厚度差 2.6cm（走路颠簸次因）
        // 物理面由 Temple_StairFloorPad 平面盒承接（同大厅 FloorPad 惯例）：砖模型中央有 5~9cm
        // 龟裂凹坑，直接挂 MeshCollider 会让玩家每块砖"陷坑-爬沿"——走路一震一震（用户 bug 主因）
        for (int i = 0; i < 3; i++)
            for (int j = 0; j < 3; j++)
            {
                bool isA = (i + j) % 2 == 0;
                var tile = Spawn(isA ? "SM_FloorTile_A" : "SM_FloorTile_B",
                                 new Vector3(-2f + 2f * i, (j == 2 ? -0.29f : -0.28f) - (isA ? TileATrim : 0f), 19.5f + 2f * j), Random.Range(0, 4) * 90f);
                if (tile) { tile.name = $"Temple_StairTile_{i}{j}"; Static(tile); }
            }
        var stairPad = new GameObject("Temple_StairFloorPad");
        stairPad.transform.position = new Vector3(0f, -0.08f, 21.5f);   // 盒高 0.2 → 顶面=0.02
        var sbc = stairPad.AddComponent<BoxCollider>();
        sbc.size = new Vector3(6f, 0.2f, 6f);   // x±3 × z18.5..24.5
        Static(stairPad);
    }

    // ---------- ⑤ 前庭（z24~34）+ 北缘台阶 ----------
    static void BuildForecourt()
    {
        // 中央 20 宽 2m 地砖拼铺（顶 y=0.02，与地形面错开防共面）；A 型找平（TileATrim）同门厅
        // 物理面由 Temple_CourtFloorPad 平面盒承接（同门厅：砖体龟裂凹坑不能直接当走行碰撞）
        for (int i = 0; i < 10; i++)
            for (int j = 0; j < 5; j++)
            {
                bool isA = (i + j) % 2 == 0;
                var go = Spawn(isA ? "SM_FloorTile_A" : "SM_FloorTile_B",
                               new Vector3(-9f + 2f * i, -0.28f - (isA ? TileATrim : 0f), 25f + 2f * j), Random.Range(0, 4) * 90f);
                if (go) { go.name = $"Temple_CourtTile_{i}{j}"; Static(go); }
            }
        var courtPad = new GameObject("Temple_CourtFloorPad");
        courtPad.transform.position = new Vector3(0f, -0.08f, 29.25f);   // 盒高 0.2 → 顶面=0.02
        var cbc = courtPad.AddComponent<BoxCollider>();
        cbc.size = new Vector3(20f, 0.2f, 9.5f);   // x±10 × z24.5..34，北端止于北缘台阶
        Static(courtPad);
        // 两侧石柱（整/破）与碎石点缀——迭代 5（用户）：门口这几根柱子换灰石（专属材质，不动共享 M_Stone 的墙/砖）
        var pillarMat = PillarGrayMat();
        PaintPillar(Solid("SM_Pillar_Whole", new Vector3(-11.5f, -0.05f, 26.5f), Random.Range(0, 4) * 90f), pillarMat);
        PaintPillar(Solid("SM_Pillar_Whole", new Vector3(11.5f, -0.05f, 26.5f), Random.Range(0, 4) * 90f), pillarMat);
        PaintPillar(Solid("SM_Pillar_Whole", new Vector3(-11.5f, -0.05f, 31.5f), Random.Range(0, 4) * 90f), pillarMat);
        PaintPillar(Solid("SM_Pillar_Whole", new Vector3(11.5f, -0.05f, 31.5f), Random.Range(0, 4) * 90f), pillarMat);
        PaintPillar(Solid("SM_Pillar_Broken", new Vector3(-10.8f, -0.05f, 29f), 40f), pillarMat);
        PaintPillar(Solid("SM_Pillar_Broken", new Vector3(10.8f, -0.05f, 29f), 220f), pillarMat);
        var debris = new[] { new Vector3(-6.5f, -0.05f, 24.8f), new Vector3(6.2f, -0.05f, 25.3f),
                             new Vector3(-5.8f, -0.05f, 33.2f), new Vector3(6.8f, -0.05f, 32.6f) };
        for (int i = 0; i < debris.Length; i++)
            Solid(i % 2 == 0 ? "SM_Debris_A" : "SM_Debris_B", debris[i], Random.Range(0, 4) * 90f);
        // 北缘 8 级台阶（原出口工程参数：每级降 0.19、进 1.5m；嵌在峡谷坡道 y0→-1.5 上）
        for (int i = 0; i < 8; i++)
            Solid("SM_Step", new Vector3(0, -0.19f * i, 34f + 1.5f * i), 0f, null, OutFbxDir);
    }

    // ---------- ⑥ 火把与火盆（Torch_* 点光 → FireFlicker/Bloom 链路） ----------
    static void BuildTorchesAndBraziers()
    {
        // 壁挂火把：房间东西墙各 2（壁挂 y7.8，取壁柱 z=0/±4/±8 之间的空档中心 z=±6，避免嵌入壁柱）
        // + 楼梯间两侧各 1（半坡 @z14：楼梯面 y≈3.33，挂点抬到 y5.5=面上 2.2m，挂内侧通道墙 x=±2.3 内表面）
        // + 石门左右边框竖条上各 1（框条 x=±2.2~2.7 表面 z≈9.94；挂 y9.0 照门洞与大厅北侧；
        //   开门时门板 x±1.5 从火把内侧(z9.80)升起，与火把 x±2.45 无干涉）
        MountTorch("Torch_Hall_A1", new Vector3(-11.99f, 7.8f, -6f), 90f);
        MountTorch("Torch_Hall_A2", new Vector3(-11.99f, 7.8f, 6f), 90f);
        MountTorch("Torch_Hall_B1", new Vector3(11.99f, 7.8f, -6f), -90f);
        MountTorch("Torch_Hall_B2", new Vector3(11.99f, 7.8f, 6f), -90f);
        MountTorch("Torch_Stair_L", new Vector3(-2.29f, 5.5f, 14f), 90f);
        MountTorch("Torch_Stair_R", new Vector3(2.29f, 5.5f, 14f), -90f);
        MountTorch("Torch_Door_L", new Vector3(-2.45f, 9.0f, 9.93f), 180f);
        MountTorch("Torch_Door_R", new Vector3(2.45f, 9.0f, 9.93f), 180f);
        // 检查点火盆（Task 18 按名挂 CheckpointSystem）：房间南墙正中（石门对墙）/ 前庭中央
        MakeBrazier("Temple_BrazierHall", new Vector3(0, LevelSpec.RoomFloorY + 0.05f, -9.2f), "Torch_Hall");
        MakeBrazier("Temple_BrazierCourt", new Vector3(0, 0.05f, 28f), "Torch_Court");
        // 无形补光（暖白、无阴影、不叫 Torch → 不会被挂火焰/闪烁/火盆音效）：
        // 大厅 4 盏四角分布（y10 靠顶、range 30 交叉覆盖 → "至少能看清人"）；楼梯间 1 盏提底光（用户：楼梯那边亮一点点）
        MakeFillLight("Temple_Fill_Hall_A1", new Vector3(-6.5f, 10f, -5f), 1.9f, 30f);
        MakeFillLight("Temple_Fill_Hall_A2", new Vector3(-6.5f, 10f, 5f), 1.9f, 30f);
        MakeFillLight("Temple_Fill_Hall_B1", new Vector3(6.5f, 10f, -5f), 1.9f, 30f);
        MakeFillLight("Temple_Fill_Hall_B2", new Vector3(6.5f, 10f, 5f), 1.9f, 30f);
        MakeFillLight("Temple_Fill_Stair", new Vector3(0f, 9f, 15.5f), 1.2f, 16f);
    }

    // ---------- ⑦ 逻辑件迁位（石门/压板/推块/玩家/相机） ----------
    static void RelocateLogic()
    {
        var door = GameObject.Find("StoneDoor");
        if (door) door.transform.position = LevelSpec.DoorPos;   // 视觉件是其子物自动跟随；closedPos 于 Play 的 Awake 缓存新位
        var plate = GameObject.Find("PressurePlate");
        if (plate) plate.transform.position = LevelSpec.PlatePos;
        var block = GameObject.Find("PushBlock");
        if (block)
        {
            var rb = block.GetComponent<Rigidbody>();
            if (rb) { rb.linearVelocity = Vector3.zero; rb.angularVelocity = Vector3.zero; }
            block.transform.position = LevelSpec.BlockPos;
        }
        var player = GameObject.Find("Player");
        if (player) { player.transform.position = LevelSpec.PlayerSpawn; player.transform.rotation = Quaternion.identity; }
        var cam = Camera.main;
        if (cam)
        {
            cam.transform.position = new Vector3(0, 9.6f, -8.6f);   // 编辑态初始机位：室内南侧俯望石门
            cam.transform.LookAt(new Vector3(0, 8f, 6f));
        }
        else Debug.LogWarning("[TempleBuilder] Camera.main 未找到，初始机位未设置");
    }

    // ---------- 工具 ----------
    static GameObject Spawn(string asset, Vector3 pos, float yaw, string name = null, string dir = null)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{dir ?? FbxDir}/{asset}.fbx");
        if (prefab == null)
        {
            Debug.LogError($"[TempleBuilder] 缺少资产 {dir ?? FbxDir}/{asset}.fbx（先复制 FBX 并等待导入）");
            return null;
        }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        go.name = name ?? $"Temple_{asset}_{seq++:D3}";
        go.transform.position = pos;
        // 以 prefab 自带轴向修正（Blender Z-up→Unity Y-up 的 X 旋转）为基准，再按 yaw 绕世界 Y
        go.transform.rotation = Quaternion.Euler(0, yaw, 0) * prefab.transform.rotation;
        return go;
    }

    static void Solidify(GameObject go)
    {
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null || mf.GetComponent<MeshCollider>() != null) continue;
            var mc = mf.gameObject.AddComponent<MeshCollider>();
            mc.sharedMesh = mf.sharedMesh;
        }
    }

    static void Static(GameObject go) =>
        GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);

    static GameObject Solid(string asset, Vector3 pos, float yaw, string name = null, string dir = null)
    {
        var go = Spawn(asset, pos, yaw, name, dir);
        if (go == null) return null;
        Solidify(go);
        Static(go);
        return go;
    }

    // 前庭柱专属灰石材质（幂等，独立资产）：门口柱子换灰（迭代 5 用户需求）。
    // 定档 v2：初版抄台阶灰(0.68)在背光阴影里与 M_Stone(0.72/0.66/0.57) 几乎无差，
    // 上调为浅灰白 —— 暗处也能读出灰调；独立材质 → 不动墙/地砖共享的 M_Stone。
    static Material PillarGrayMat()
    {
        const string matPath = "Assets/Settings/M_Pillar_Gray.mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mat == null)
        {
            mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            AssetDatabase.CreateAsset(mat, matPath);
        }
        mat.SetColor("_BaseColor", new Color(0.80f, 0.80f, 0.80f, 1f));   // 浅灰白（迭代 5 定档 v2）
        mat.SetFloat("_Smoothness", 0.10f);
        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssetIfDirty(mat);
        return mat;
    }

    static void PaintPillar(GameObject go, Material mat)
    {
        if (go == null || mat == null) return;
        foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
            r.sharedMaterial = mat;
    }

    // 房间地板物理面：精确平面盒（顶面=RoomFloorY=6.0）。地砖为纯视觉件（顶=6.0 与台面齐平）；
    // 推块（Y 冻结悬浮于 6.0）需要精确接触面，物理统一由本 pad 承接（防浮雕地板时代的打滑回归）。
    static void FloorPad()
    {
        var pad = new GameObject("Temple_FloorPad");
        pad.transform.position = new Vector3(0, LevelSpec.RoomFloorY - 0.25f, 0f);   // 盒高 0.5 → 顶面=6.0
        var bc = pad.AddComponent<BoxCollider>();
        bc.size = new Vector3(2 * LevelSpec.RoomHalfX + 0.4f, 0.5f, 2 * LevelSpec.RoomHalfZ + 0.4f);   // 每边多 0.2 防墙脚缝
        Static(pad);
    }

    // 墙段（实体+静态）：原宽 4m / 原高 3.015m；width=横向实际宽，hz=纵向缩放比
    static string WallPiece(string prev, Vector3 pos, float yaw, float width, float hz)
    {
        var asset = PickWallVariant(prev);
        var go = Spawn(asset, pos, yaw);
        if (go)
        {
            go.transform.localScale = new Vector3(width / 4f * 1.025f, 1f, hz);   // 横向 2.5% 重叠消交界缝
            Solidify(go);
            Static(go);
        }
        return asset;
    }

    static string PickWallVariant(string prev)
    {
        string[] pool = { "SM_Wall_A", "SM_Wall_A", "SM_Wall_B", "SM_Wall_B", "SM_Wall_C", "SM_Wall_D" };
        var pick = pool[Random.Range(0, pool.Length)];
        for (int tries = 0; tries < 8 && pick == prev; tries++)
            pick = pool[Random.Range(0, pool.Length)];
        return pick;
    }

    static void MountTorch(string lightName, Vector3 wallPos, float yaw)
    {
        var go = Spawn("SM_Torch", wallPos, yaw);
        if (go) Static(go);
        // 火心 ≈ 局部 (0, 0.88, 0.55)（SM_Torch 头注）→ 点光设于火焰光心
        MakeTorchLight(lightName, wallPos + Quaternion.Euler(0, yaw, 0) * new Vector3(0, 0.88f, 0.55f));
    }

    static void MakeBrazier(string name, Vector3 pos, string lightName)
    {
        var go = Solid("SM_Brazier", pos, 0f, name);
        RetintFire(go);
        MakeTorchLight(lightName, pos + new Vector3(0, 1.1f, 0f));   // 火焰光心（KitPlacer 口径：盆口 0.85 与焰尖之间）
    }

    // 火光点光：暖橙 3.2 / 射程 10.5 / 无阴影（迭代 3：加亮；迭代 4：关阴影——10 个点光软阴影=60 张 shadow map，
    // atlas 溢出被 Unity 强制降 4 倍分辨率 → 走动时阴影/表面闪变（用户反馈"走路一闪一闪，光变大后更严重"）；
    // 室内暗处火光阴影本就不明显，光晕氛围不依赖阴影，关后闪烁根源消除）
    static void MakeTorchLight(string name, Vector3 pos)
    {
        var l = new GameObject(name).AddComponent<Light>();
        l.type = LightType.Point;
        l.color = new Color(1f, 0.60f, 0.30f);
        l.intensity = 3.2f;
        l.range = 10.5f;
        l.shadows = LightShadows.None;
        l.transform.position = pos;
    }

    // 无形补光：暖白、无阴影——只提室内底光（"密室太黑"），不改变室外氛围与火把明暗对比。
    // 强度/射程由调用点给（大厅四角 1.9/30 交叉覆盖、楼梯间 1.2/16——迭代 2 用户：看清人 + 楼梯亮一点）
    static void MakeFillLight(string name, Vector3 pos, float intensity, float range)
    {
        var l = new GameObject(name).AddComponent<Light>();
        l.type = LightType.Point;
        l.color = new Color(1f, 0.9f, 0.82f);
        l.intensity = intensity;
        l.range = range;
        l.shadows = LightShadows.None;
        l.transform.position = pos;
    }

    // ---------- 火焰半透明材质（复制自 KitPlacer:245-288：FBX 内嵌不透明 M_Fire → 独立半透明材质） ----------
    static Material EnsureFireMaterial(string name, Color c)
    {
        string path = $"Assets/Art/Static/temple/{name}.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null)
        {
            var shader = Shader.Find("Universal Render Pipeline/Unlit");
            if (shader == null) { Debug.LogError("[TempleBuilder] 找不到 URP/Unlit shader，火焰材质创建失败"); return null; }
            m = new Material(shader);
            m.name = name;
            AssetDatabase.CreateAsset(m, path);
        }
        m.SetFloat("_Surface", 1f);   // Transparent
        m.SetFloat("_Blend", 0f);     // Alpha Blend
        m.SetOverrideTag("RenderType", "Transparent");
        m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        m.SetInt("_ZWrite", 0);
        m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
        m.SetColor("_BaseColor", c);
        EditorUtility.SetDirty(m);
        return m;
    }

    static void RetintFire(GameObject go)
    {
        if (!go) return;
        var fire = EnsureFireMaterial("M_Fire", new Color(1f, 0.55f, 0.15f, 0.45f));
        var core = EnsureFireMaterial("M_Fire_Core", new Color(1f, 0.85f, 0.40f, 0.9f));
        foreach (var r in go.GetComponentsInChildren<Renderer>())
        {
            var mats = r.sharedMaterials;
            bool changed = false;
            for (int i = 0; i < mats.Length; i++)
            {
                if (mats[i] == null) continue;
                if (mats[i].name.StartsWith("M_Fire_Core")) { mats[i] = core; changed = true; }
                else if (mats[i].name.StartsWith("M_Fire")) { mats[i] = fire; changed = true; }
            }
            if (changed) r.sharedMaterials = mats;
        }
    }
}
