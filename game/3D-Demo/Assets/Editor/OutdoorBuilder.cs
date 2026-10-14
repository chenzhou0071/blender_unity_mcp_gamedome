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
        BuildGorge();               // M6-2 Task 9: 岩缝段巨石阵（蹲行通过/站立被挡）
        BuildVines();               // M6-3 Task 12: 藤帘（斩断通过）
        BuildWater();               // M6-4 Task 13: 河谷水面 + WaterVolume 判定体
        BuildRope();                // M6-5 Task 15: 斜绳横跨深渊 + 双锚桩
        BuildAbyssMist();           // M6-5 Task 15: 深渊雾层（4 层渐没入黑暗）
        EnsureGroundOutside();      // 收编灰盒遗留大地坪：材质对齐峡谷地形色（用户：灰板与地面色不一致）
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        Debug.Log("[OutdoorBuilder] 户外场景构建完成");
    }

    static void CleanupOUT()
    {
        // 只清本构建器管理的 OUT_ 对象；保护其它系统产物（2026-10-13 修复：曾误清植被与光照过渡）：
        //   OUT_Veg_* 植被（散布器全量重建代价高，由「散布植被」菜单自管） / OUT_Zone_* 光照过渡（「户外氛围」菜单自管）
        foreach (var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
            if (go.name.StartsWith("OUT_") && !go.name.StartsWith("OUT_Veg_") && !go.name.StartsWith("OUT_Zone_"))
                Object.DestroyImmediate(go);
    }

    static GameObject InstantiateFbx(string name, Vector3 pos, Quaternion rot)
    {
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>($"{FbxDir}/{name}.fbx");
        var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        go.name = "OUT_" + name;
        // 同 KitPlacer：以 prefab 自带轴向修正（Blender Z-up→Unity Y-up 的 X 旋转）为基准，再叠加摆位旋转。
        // 注意不能用 SetPositionAndRotation——那会重置 prefab 根上的 270° 轴补偿，导致模型躺平。
        go.transform.position = pos;
        go.transform.rotation = rot * fbx.transform.rotation;
        go.AddComponent<MeshCollider>();               // 静态地形：convex=false 默认
        UnityEditor.GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        return go;
    }

    static void PlaceTerrain() { InstantiateFbx("SM_CanyonTerrain", Vector3.zero, Quaternion.identity); }

    // M6-5 Task 15: FBX 实体变体——去掉 MeshCollider 与静态标记（会动的对象：绳/桩/雾层由各自系统控制）。
    static GameObject InstantiateFbxNoCollider(string name, Vector3 pos)
    {
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>($"{FbxDir}/{name}.fbx");
        var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        go.name = "OUT_" + name;
        go.transform.position = pos;
        go.transform.rotation = fbx.transform.rotation;    // 保留 prefab 轴补偿（Blender Z-up→Unity Y-up）
        return go;
    }

    // 灰盒遗留的 40×50 大地坪（GroundOutside，不属 OUT_ 前缀所以 CleanupOUT 清不到它）：
    // 默认材质是 URP 包内 Lit.mat（灰 0.5），与峡谷地形（M_Terrain 纯色沙 0.63/0.58/0.50）割裂。
    // 生成独立材质资产 M_GroundOutside.mat（基色/平滑度读取地形 FBX 内嵌材质），对象存在才处理（不新建），幂等。
    static void EnsureGroundOutside()
    {
        var go = GameObject.Find("GroundOutside");
        if (go == null) return;
        var mr = go.GetComponent<MeshRenderer>();
        if (mr == null) return;

        // 目标参数：从峡谷地形 FBX 内嵌材质读（取不到时回退实测定档值）
        Color baseCol = new Color(0.63f, 0.58f, 0.50f, 1f);
        float smooth = 0.5f;
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath($"{FbxDir}/SM_CanyonTerrain.fbx"))
        {
            var tm = o as Material;
            if (tm == null) continue;
            if (tm.HasProperty("_BaseColor")) baseCol = tm.GetColor("_BaseColor");
            if (tm.HasProperty("_Smoothness")) smooth = tm.GetFloat("_Smoothness");
            break;
        }

        const string matPath = "Assets/Settings/M_GroundOutside.mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mat == null)
        {
            mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            AssetDatabase.CreateAsset(mat, matPath);
        }
        mat.SetColor("_BaseColor", baseCol);     // 幂等：重跑时跟随地形色更新
        mat.SetFloat("_Smoothness", smooth);
        EditorUtility.SetDirty(mat);
        AssetDatabase.SaveAssetIfDirty(mat);
        mr.sharedMaterial = mat;
        Debug.Log("[OutdoorBuilder] GroundOutside 大地坪材质已对齐峡谷地形色 " + baseCol.ToString("F2"));
    }

    // M6-2 Task 9: 岩缝石件摆位（支持非均匀缩放与倾倒——压顶要压扁、斜靠石要倾斜）。
    // 轴映射：prefab 根自带轴补偿旋转（Blender Z-up→Unity Y-up 的 -90°X），localScale 作用于
    // 旋转前的模型本地空间：x=宽、y=进深、z=高（经旋转映射到世界 y）。等比石件三轴同值即可。
    // 2026-10-13 巨石岗重做：加 spin（世界空间欧拉角，左乘叠加于轴补偿之上——斜靠门左右石倾倒方向相反）。
    static void MakeRock(string goName, string fbxName, Vector3 pos, Vector3 spin, Vector3 scale)
    {
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>($"{FbxDir}/{fbxName}.fbx");
        var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        go.name = goName;
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(spin) * fbx.transform.rotation;  // 不可用 SetPositionAndRotation：会重置轴补偿
        go.transform.localScale = scale;
        go.AddComponent<MeshCollider>();                  // 静态地形：convex=false 默认
        UnityEditor.GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
    }

    // 岩台顶面落位（巨石岗重做）：从高处向下打射线、只认峡谷地形根——基座/门柱石要垫在坡上而非浮空。
    // 用 RaycastAll 穿透先行石件（先落的石头会挡住单发射线导致误判「未命中」回退——2026-10-13 修复）。
    static float TerrainY(float x, float z)
    {
        var hits = Physics.RaycastAll(new Vector3(x, 40f, z), Vector3.down, 200f, ~0, QueryTriggerInteraction.Ignore);
        float best = float.MaxValue;
        foreach (var h in hits)
            if (h.collider.transform.root.name == "OUT_SM_CanyonTerrain" && h.distance < best)
                best = h.distance;
        if (best < float.MaxValue) return 40f - best;
        Debug.LogWarning($"[OutdoorBuilder] TerrainY({x},{z}) 未命中峡谷地形，回退 -1.5");
        return -1.5f;
    }

    // 固定种子 [a,b) 随机浮点（幂等重跑一致）
    static float RR(System.Random rnd, float a, float b) { return a + (float)rnd.NextDouble() * (b - a); }

    // 缝内隐藏暖光（巨石岗重做）：只当补光，不投影——避免碎影干扰蹲行动作辨识
    static void MakeLamp(string goName, Vector3 pos)
    {
        var go = new GameObject(goName);
        go.transform.position = pos;
        var l = go.AddComponent<Light>();
        l.type = LightType.Point;
        l.range = 10f;
        l.intensity = 0.9f;
        l.color = new Color(1f, 0.78f, 0.55f);
        l.shadows = LightShadows.None;
    }

    // M6-2 Task 9 巨石岗重做（2026-10-13 用户反馈"很多超大的石头垒在这一整块突出的地方"）：
    // 三层堆叠——南口门柱(C yaw 内旋)+门楣 → 斜靠门×3（D 楔石成对相向斜倚 12° + B 压顶）
    // → 北口 C 巨岩；基座 C 垫岩台坡、顶冠 C 压顶、侧翼 A 补缝；缝内 2 处隐藏暖光。
    // 通行（缝底 y=-1.5）：压顶底面离地 1.40m（站立 1.8 被挡、停 z≈98.6）；斜靠门在蹲行身位
    // （h≤1.0）净宽 ≥1.3m（蹲行 1.15 通过）；门间 10.5m 全开天 = 结构天窗。固定 seed 77 幂等。
    static void BuildGorge()
    {
        Physics.SyncTransforms();   // 保险：PlaceTerrain 新建的地形 collider 同步后才能被 TerrainY 命中
        const float Floor = -1.5f, LeanDeg = 12f;
        float c = Mathf.Cos(LeanDeg * Mathf.Deg2Rad), s = Mathf.Sin(LeanDeg * Mathf.Deg2Rad);
        const float dw = 4.10f / 2f, dh = 7.23f / 2f;      // D 石实测 (4.10, 2.90, 7.23) 的半宽/半高
        float ox = dw * c - dh * s;                        // ≈1.25 内底棱 → 石心的世界 x 偏移（倾 12° 后）
        float oy = dw * s + dh * c;                        // ≈3.96 内底棱 → 石心的世界 y 偏移
        const float GapHalf = 1.025f, Sink = 0.75f;        // 门缝半宽（缝底净宽 2.05）/ 内侧下沉（外半埋进岩台）
        var rnd = new System.Random(77);

        // ---- 斜靠门 ×3：D 楔石对 + B 压顶（z 100.5 / 111 / 121.5）----
        float[] gateZ = { 100.5f, 111f, 121.5f };
        for (int i = 0; i < gateZ.Length; i++)
        {
            float zL = gateZ[i] + RR(rnd, -0.4f, 0.4f), zR = gateZ[i] + RR(rnd, -0.4f, 0.4f);
            // 左石：绕世界 Z 顺时针 12°（顶部向中心倾）——内底棱精确落在 (-GapHalf, Floor-Sink)
            MakeRock($"OUT_Gorge_Lean_L{i}", "SM_GorgeRock_D",
                     new Vector3(-(GapHalf + ox), Floor + oy - Sink, zL),
                     new Vector3(RR(rnd, -2f, 2f), RR(rnd, -5f, 5f), -LeanDeg), Vector3.one);
            // 右石：镜像（逆时针 +12°）
            MakeRock($"OUT_Gorge_Lean_R{i}", "SM_GorgeRock_D",
                     new Vector3(GapHalf + ox, Floor + oy - Sink, zR),
                     new Vector3(RR(rnd, -2f, 2f), RR(rnd, -5f, 5f), LeanDeg), Vector3.one);
            // 压顶：B 压扁（宽 2.96×进深 3.18×高 1.77），底面离地 1.40m（中心 = Floor+1.40+高/2）
            MakeRock($"OUT_Gorge_Cap{i}", "SM_GorgeRock_B",
                     new Vector3(0f, Floor + 1.40f + 2.46f * 0.72f * 0.5f, gateZ[i]),
                     new Vector3(RR(rnd, -2f, 2f), RR(rnd, -4f, 4f), 0f), new Vector3(0.72f, 0.8f, 0.72f));
        }

        // ---- 南口门柱 ×2 + 门楣（z 96.6，岩台渐入段的"门面"）：C 巨岩 yaw 内旋对视缝口 ----
        MakeRock("OUT_Gorge_Mouth_L", "SM_GorgeRock_C",
                 new Vector3(-5.9f, TerrainY(-5.9f, 96.6f) - 0.8f + 4.55f * 1.06f * 0.5f, 96.6f),
                 new Vector3(0f, 25f, 0f), Vector3.one * 1.06f);
        MakeRock("OUT_Gorge_Mouth_R", "SM_GorgeRock_C",
                 new Vector3(5.9f, TerrainY(5.9f, 96.6f) - 0.8f + 4.55f * 1.06f * 0.5f, 96.6f),
                 new Vector3(0f, -35f, 0f), Vector3.one * 1.06f);
        MakeRock("OUT_Gorge_Mouth_Top", "SM_GorgeRock_B",
                 new Vector3(0f, Floor + 3.3f + 2.46f * 0.5f, 96.6f),
                 new Vector3(0f, RR(rnd, -4f, 4f), 0f), Vector3.one);

        // ---- 基座 C ×6：垫岩台坡（缝两侧 |x|≈5.8-6.3 交替、TerrainY 落位、埋 1.4-1.8）----
        for (int i = 0; i < 6; i++)
        {
            float z = 100.5f + i * 5.3f + RR(rnd, -1f, 1f);
            float x = (i % 2 == 0 ? -1f : 1f) * RR(rnd, 5.8f, 6.3f);
            float sc = RR(rnd, 0.62f, 0.78f), sink = RR(rnd, 1.4f, 1.8f);
            MakeRock($"OUT_Gorge_Found{i}", "SM_GorgeRock_C",
                     new Vector3(x, TerrainY(x, z) - sink + 4.55f * sc * 0.5f, z),
                     new Vector3(RR(rnd, -3f, 3f), RR(rnd, -180f, 180f), RR(rnd, -3f, 3f)), Vector3.one * sc);
        }

        // ---- 顶冠 C ×3：压在两门之间上方（底面离地 5.5m——剪影成岗、不遮缝内天光）----
        for (int i = 0; i < 3; i++)
        {
            float z = 105.75f + i * 5.25f + RR(rnd, -0.8f, 0.8f);
            float sc = RR(rnd, 0.85f, 1.05f);
            MakeRock($"OUT_Gorge_Crown{i}", "SM_GorgeRock_C",
                     new Vector3(RR(rnd, -0.8f, 0.8f), Floor + 5.5f + 4.55f * sc * 0.5f, z),
                     new Vector3(RR(rnd, -3f, 3f), RR(rnd, -180f, 180f), RR(rnd, -3f, 3f)), Vector3.one * sc);
        }

        // ---- 北口 C ×2（z 128.5 / 129，岩台渐出段收尾）----
        MakeRock("OUT_Gorge_Exit_L", "SM_GorgeRock_C",
                 new Vector3(-5.6f, TerrainY(-5.6f, 128.5f) - 0.9f + 4.55f * 0.9f * 0.5f, 128.5f),
                 new Vector3(0f, 30f, 0f), Vector3.one * 0.9f);
        MakeRock("OUT_Gorge_Exit_R", "SM_GorgeRock_C",
                 new Vector3(5.7f, TerrainY(5.7f, 129f) - 0.9f + 4.55f * 0.9f * 0.5f, 129f),
                 new Vector3(0f, -32f, 0f), Vector3.one * 0.9f);

        // ---- 侧翼 A ×4：外缘补缝（|x| 7.6-8.2、scale 1.7-1.9、埋 1.3）----
        for (int i = 0; i < 4; i++)
        {
            float z = 99f + i * 8.5f + RR(rnd, -1f, 1f);
            float x = (i % 2 == 0 ? -1f : 1f) * RR(rnd, 7.6f, 8.2f);
            float sc = RR(rnd, 1.7f, 1.9f);
            MakeRock($"OUT_Gorge_Wing{i}", "SM_GorgeRock_A",
                     new Vector3(x, TerrainY(x, z) - 1.3f + 2.56f * sc * 0.5f, z),
                     new Vector3(RR(rnd, -4f, 4f), RR(rnd, -180f, 180f), RR(rnd, -4f, 4f)), Vector3.one * sc);
        }

        // ---- 缝内隐藏暖光 ×2（门间开天段 z 103.5 / 116；无阴影补光——缝内看得清蹲行动作）----
        MakeLamp("OUT_Gorge_Light_1", new Vector3(0f, Floor + 1.3f, 103.5f));
        MakeLamp("OUT_Gorge_Light_2", new Vector3(0f, Floor + 1.3f, 116f));

        var hint = new GameObject("OUT_Gorge_Hint");
        hint.transform.position = new Vector3(0, -1.5f, 92f);
        var hz = hint.AddComponent<HintZone>(); hz.text = "岩缝太窄——按 C 蹲下通过"; hz.radius = 6f;
        Debug.Log("[OutdoorBuilder] 巨石岗：斜靠门 3 + 压顶 3 + 南口 3 + 基座 6 + 顶冠 3 + 北口 2 + 侧翼 4 + 微光 2 + 提示区");
    }

    // M6-3 Task 12: 藤帘（z 68 岩缝北段）——挥刀斩断即塌落（CuttableVine）。
    // 原点=帘顶中点：放 (0,-0.1,68) 后帘面从 y-0.1 垂到地面以下。碰撞盒在 prefab 本地空间
    // （x=宽、y=进深、z=高——同 MakeRock 轴映射注释），竖直范围本地 z -2.6..0；会动，不标 BatchingStatic。
    static void BuildVines()
    {
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>($"{FbxDir}/SM_Vine_Curtain.fbx");
        var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        go.name = "OUT_VineCurtain";
        go.transform.position = new Vector3(0f, -0.1f, 68f);
        go.transform.rotation = fbx.transform.rotation;      // 保留轴补偿（Blender Z-up→Unity Y-up）；帘宽 5m 沿世界 x
        var box = go.AddComponent<BoxCollider>();
        box.size = new Vector3(5f, 0.4f, 2.6f);               // 本地：x 宽 / y 进深 / z 高
        box.center = new Vector3(0f, 0f, -1.3f);              // 本地 z -2.6..0 = 帘顶零点向下垂
        go.AddComponent<CuttableVine>();
        Debug.Log("[OutdoorBuilder] 藤帘：OUT_VineCurtain (0,-0.1,68) 盒 5×2.6×0.4 + CuttableVine");
    }

    // M6-4 Task 13: 河谷水面——100×30m 水平盘面（URP Lit 透明水色兜底方案；反馈加宽至与河谷同宽）。
    // 水面不参与碰撞（游泳走 WaterVolume 状态判定）；透明材质参数补全 SrcBlend/DstBlend/ZWrite
    // （同 GetOrCreateMistMat 模式——只设 _Surface/_Blend 缺混合因子会渲染成不透明）。
    static void BuildWater()
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Plane);
        go.name = "OUT_Water";
        Object.DestroyImmediate(go.GetComponent<Collider>());          // 水面不参与碰撞（游泳走状态判定）
        go.transform.position = new Vector3(0, -2.6f, 149.5f);
        go.transform.localScale = new Vector3(10f, 1, 3f);           // 100m × 30m：横贯河谷全宽（贴合地图，两缘埋入崖壁/河岸下）

        const string matPath = "Assets/Art/Static/outdoor/M_Water.mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        bool isNew = mat == null;
        if (isNew) mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 0);        // Transparent/Alpha
        mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
        mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        mat.SetFloat("_ZWrite", 0f);
        mat.SetColor("_BaseColor", new Color(0.10f, 0.30f, 0.36f, 0.72f));
        mat.SetFloat("_Smoothness", 0.88f); mat.SetFloat("_Metallic", 0.05f);
        mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        mat.renderQueue = 3000;
        if (isNew) AssetDatabase.CreateAsset(mat, matPath);            // 幂等：重跑仅刷新参数（GUID 稳定）
        else { EditorUtility.SetDirty(mat); AssetDatabase.SaveAssetIfDirty(mat); }
        go.GetComponent<MeshRenderer>().sharedMaterial = mat;

        var wv = new GameObject("OUT_WaterVolume").AddComponent<WaterVolume>();   // 判定体与水面同坐标
        wv.transform.position = new Vector3(0, -2.6f, 149.5f);
        Debug.Log("[OutdoorBuilder] 水面：OUT_Water 100×30 @ (0,-2.6,149.5) + OUT_WaterVolume 判定");
    }

    // M6-5 Task 15: 绳索与锚桩——斜绳横跨深渊（南岸崖边 → 对岸崖顶）。
    // 锚点：南端 (0,-1.0,193.5)（南岸高台 -1.5，桩底着地、桩顶 -1.0 即绳南端）；
    //      北端 (0,3.4,215.8)（崖顶 y=3 起于 z≈216，215.8 处地形 ≈2.94；北桩底 2.94、桩顶 3.44）。
    // SM_Rope 原点=南底端、几何沿本地 +Y 长 22.7m（Blender 沿 +y 建模）——
    // 故直接 rotation=FromToRotation(up, 北-南)（不乘 fbx 轴补偿：本地 +Y 数据即绳轴，RopeSystem.Axis=transform.up 自洽）。
    static void BuildRope()
    {
        InstantiateFbxNoCollider("SM_Stake", new Vector3(0f, -1.5f, 193.5f)).name = "OUT_Stake_S";   // 南端桩（崖边）
        InstantiateFbxNoCollider("SM_Stake", new Vector3(0f, 2.94f, 215.8f)).name = "OUT_Stake_N";   // 北端桩（崖顶）
        var rope = InstantiateFbxNoCollider("SM_Rope", new Vector3(0f, -1.0f, 193.5f));
        rope.name = "OUT_Rope_1";                // 绳本体不加碰撞（爬绳走 RopeSystem 状态判定）
        Vector3 north = new Vector3(0f, 3.4f, 215.8f) - rope.transform.position;   // 南→北斜向
        rope.transform.rotation = Quaternion.FromToRotation(Vector3.up, north.normalized);
        rope.AddComponent<RopeSystem>();         // M6-5 Task 16: 爬绳系统（绳长/速度用组件默认值）
        Debug.Log("[OutdoorBuilder] 斜绳：OUT_Rope_1 22.7m 跨深渊 + 双桩（南 -1.5 / 北 2.94）+ RopeSystem");
    }

    // M6-5 Task 15: 深渊雾层——4 层水平薄雾板（Cube 薄板 36×0.06×14）从上到下渐浓没入黑暗——“看不见底”。
    // 透明材质共享 M_Mist；雾板会动（MistDrift 浮动）→ 不标静态、关阴影（M5 静态批处理教训）。
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
        Debug.Log("[OutdoorBuilder] 深渊雾层：OUT_Mist_1~4（y -3/-10/-17/-24、alpha 0.25→0.8）");
    }

    // M6-5: 雾材质资产化（仿 M_Water 的幂等模式——只设 _Surface/_Blend 缺混合因子会渲染成不透明）。
    static Material GetOrCreateMistMat()
    {
        const string path = "Assets/Art/Static/outdoor/M_Mist.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        bool isNew = m == null;
        if (isNew)
            m = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
        m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 0f);                       // 透明/Alpha
        m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
        m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        m.SetFloat("_ZWrite", 0f);
        m.SetColor("_BaseColor", new Color(0.16f, 0.18f, 0.23f, 0.5f));            // 灰蓝雾色（比谷底黑略亮→可辨；MPB 运行时覆写 alpha）
        m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        m.renderQueue = 3000;
        if (isNew) AssetDatabase.CreateAsset(m, path);                                // 幂等：重跑仅刷新参数（GUID 稳定）
        else { EditorUtility.SetDirty(m); AssetDatabase.SaveAssetIfDirty(m); }
        return m;
    }
}