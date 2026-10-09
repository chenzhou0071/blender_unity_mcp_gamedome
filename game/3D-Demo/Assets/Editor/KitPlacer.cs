using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

// M3-3: 用 Blender 生成的正式资产替换灰盒。
// 原则：原灰盒对象保留为逻辑体（脚本/碰撞/tag/layer 一律不动），仅禁用其渲染；
//       正式资产作为视觉件（VIZ_ 前缀）摆放——需要跟随动画的（石门/压力板/推块/宝物）
//       挂为子物体自动跟随；视觉件可重复执行清理（重跑本菜单会先清掉 VIZ_ 再重建）。
public static class KitPlacer
{
    const string FbxDir = "Assets/Art/Static/temple";
    static int vizCount;

    [MenuItem("Demo/用正式资产替换灰盒")]
    public static void Replace()
    {
        if (GameObject.Find("FloorA") == null || GameObject.Find("WallA_S") == null)
        {
            Debug.LogError("[KitPlacer] 场景中未找到灰盒关卡，请先执行「Demo/构建灰盒关卡」");
            return;
        }
        var scene = EditorSceneManager.OpenScene("Assets/Scenes/Demo.unity", OpenSceneMode.Single);
        CleanupOld();
        vizCount = 0;

        // ---- 1) 地板：2m 网格铺地砖（顶面与灰盒碰撞面 y=0 对齐；灰盒禁渲染保留碰撞）
        Tiled("FloorA", -10f, -8f, 20, 16, -0.30f);
        Tiled("FloorB", -8f, 8f, 16, 14, -0.30f);

        // ---- 2) 外墙与隔墙：4m 墙段两层铺满（A/B/C/D 加权随机；灰盒禁渲染保留碰撞）
        WallRun("WallA_S", 0f, -8f, true, 20f, 0f);     // 内侧朝 +Z
        WallRun("WallA_E", 10f, 0f, false, 16f, -90f);  // 内侧朝 -X
        WallRun("WallA_W", -10f, 0f, false, 16f, 90f);  // 内侧朝 +X
        WallRun("WallAB_L", -5.75f, 8f, true, 8.5f, 180f);
        WallRun("WallAB_R", 5.75f, 8f, true, 8.5f, 180f);
        WallRun("WallB_E", 8f, 15f, false, 14f, -90f);
        WallRun("WallB_W", -8f, 15f, false, 14f, 90f);
        WallRun("WallB_N", 0f, 22f, true, 16f, 180f);
        // 门楣（灰盒 3×2 @ y4~6）：单块墙段缩放盖住
        Hide("WallAB_Top");
        var lintel = Spawn("SM_Wall_A", new Vector3(0, 4f, 8f), 180f);
        if (lintel) lintel.transform.localScale = new Vector3(0.75f, 2f / 3f, 1f);

        // ---- 3) 门洞装饰：石门框 + 拱门（贴 A 厅一侧墙面）
        Spawn("SM_DoorFrame", new Vector3(0, 0, 8f), 0f);
        Spawn("SM_Arch", new Vector3(0, 0, 7.70f), 0f);

        // ---- 4) 机关/道具：灰盒保留为逻辑体，视觉挂子物体（跟随开门/下沉/被推动画）
        var door = Normalize("StoneDoor");          // 石门：缩放归一，碰撞尺寸转存 BoxCollider
        if (door) Spawn("SM_StoneDoor", new Vector3(0, 0, 8f), 180f, door.transform);
        var plate = Normalize("PressurePlate");
        if (plate) Spawn("SM_PressurePlate", new Vector3(4, 0, -2f), 0f, plate.transform);
        var block = Normalize("PushBlock");
        if (block) Spawn("SM_PushBlock", new Vector3(-2, 0, -2f), 15f, block.transform);
        var treasure = Normalize("Treasure", 1.5f); // 宝物：SphereCollider 半径由 0.4 缩放换算为世界 1.5
        if (treasure) Spawn("SM_Treasure", new Vector3(0, 4.0f, 19f), 0f, treasure.transform);
        // 祭坛（无脚本；灰盒保留碰撞，视觉独立摆放，底面贴石台顶 y=3）
        Hide("Altar");
        SpawnSolid("SM_Altar", new Vector3(0, 3f, 19f), 0f);   // 视觉精确碰撞（叠在灰盒盒体上，无副作用）

        // ---- 5) 攀爬石台：灰盒（Climbable layer + 碰撞）禁渲染；四周墙段贴面（嵌入台体内，
        //         外表面与碰撞面重合）+ 顶面地砖
        Hide("ClimbableLedge");
        string prevP = "";
        for (int i = 0; i < 3; i++)     // 南立面（正面朝房间）
        {
            prevP = PickWallVariant(prevP);
            WallPiece(prevP, new Vector3(-2 + 2 * i, 0, 16.25f), 180f, 0.5f);
        }
        for (int i = 0; i < 2; i++)     // 北立面
        {
            prevP = PickWallVariant(prevP);
            WallPiece(prevP, new Vector3(-1.5f + 3 * i, 0, 19.75f), 0f, 0.75f);
        }
        WallPiece(PickWallVariant(""), new Vector3(3.25f, 0, 18f), 90f, 1f);    // 东立面
        WallPiece(PickWallVariant(""), new Vector3(-3.25f, 0, 18f), -90f, 1f);  // 西立面
        for (int i = 0; i < 3; i++)     // 顶面 6 块地砖（2×2 网格，顶面 y=3）
            for (int j = 0; j < 2; j++)
                Spawn((i + j) % 2 == 0 ? "SM_FloorTile_A" : "SM_FloorTile_B",
                      new Vector3(-2 + 2 * i, 2.7f, 17 + 2 * j), (i + j) % 2 * 90f);

        // ---- 6) 装饰：石柱×4 / 破柱×2（一立一躺）/ 火盆×4 / 台阶 / 碎石×6（全部实体碰撞）
        foreach (var x in new[] { -7f, 7f })
            foreach (var z in new[] { -5f, 5f })
                SpawnSolid("SM_Pillar_Whole", new Vector3(x, 0, z), Random.Range(0, 4) * 90f);
        SpawnSolid("SM_Pillar_Broken", new Vector3(-6.5f, 0, 2.5f), 40f);
        var fallen = SpawnSolid("SM_Pillar_Broken", new Vector3(6.2f, 0.30f, 4.5f), 0f);
        if (fallen) fallen.transform.rotation = Quaternion.Euler(0, 20, 0)
            * Quaternion.Euler(0, 0, 90) * Quaternion.Euler(270, 0, 0);
        var braziers = new[] {
            new Vector3(-3, 0, -6f), new Vector3(3, 0, -6f),
            new Vector3(-3, 0, 12.5f), new Vector3(3, 0, 12.5f) };
        var torchNames = new[] { "TorchA_L", "TorchA_R", "TorchB_L", "TorchB_R" };
        for (int i = 0; i < braziers.Length; i++)
        {
            RetintFire(SpawnSolid("SM_Brazier", braziers[i], 0f));
            EnsureTorchLight(braziers[i], torchNames[i]);   // 火盆点光：确保存在并对齐火焰光心
        }
        SpawnSolid("SM_Stairs", new Vector3(0, 0, 20.9f), 180f);
        var rubble = new[] {
            new Vector3(2.4f, 0, 7.2f), new Vector3(-2.6f, 0, 7.3f),
            new Vector3(-9.2f, 0, -6.5f), new Vector3(8.8f, 0, -6.8f),
            new Vector3(3.6f, 0, 13.2f), new Vector3(-5.4f, 0, 20.4f) };
        for (int i = 0; i < rubble.Length; i++)
        {
            var go = SpawnSolid(i % 2 == 0 ? "SM_Debris_A" : "SM_Debris_B", rubble[i],
                                Random.Range(0, 4) * 90f);
            if (go) go.transform.localScale = Vector3.one * Random.Range(0.8f, 1.25f);
        }

        ApplyLightingMood();   // M3-5 光照氛围（清晨）：晨光/淡蓝天空（幂等施加）
        // SpawnFogPatches();  // 低空雾团：M3-5 验收"偏假"暂缓；代码/资产已就位，地图扩大后再启用

        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
        Debug.Log($"[KitPlacer] 灰盒替换完成：视觉件 {vizCount} 个" +
                  "（灰盒保留为逻辑体，碰撞/脚本/引用未动）");
    }

    // ---------- 工具 ----------

    static GameObject Spawn(string asset, Vector3 worldPos, float yaw, Transform parent = null)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{FbxDir}/{asset}.fbx");
        if (prefab == null)
        {
            Debug.LogError($"[KitPlacer] 缺少资产 {FbxDir}/{asset}.fbx（先复制 FBX 并等待导入）");
            return null;
        }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
        go.name = $"VIZ_{asset}_{vizCount++:D3}";
        go.transform.position = worldPos;
        // 以 prefab 自带的轴向修正（Blender Z-up→Unity Y-up 的 X 旋转）为基准，再按 yaw 绕世界 Y
        go.transform.rotation = Quaternion.Euler(0, yaw, 0) * prefab.transform.rotation;
        return go;
    }

    // 装饰件实体碰撞：给视觉件所有带 MeshFilter 的节点挂 MeshCollider（non-convex，静态装饰用）。
    // M3-5 验收反馈：石柱/火盆/碎石/祭坛/台阶此前是可穿模的纯视觉件。
    // 墙体/地板/机关不用（灰盒逻辑体已带碰撞，见 Hide() 注释）。
    static GameObject SpawnSolid(string asset, Vector3 worldPos, float yaw, Transform parent = null)
    {
        var go = Spawn(asset, worldPos, yaw, parent);
        if (go == null) return null;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
        {
            if (mf.sharedMesh == null || mf.GetComponent<MeshCollider>() != null) continue;
            var mc = mf.gameObject.AddComponent<MeshCollider>();
            mc.sharedMesh = mf.sharedMesh;
        }
        return go;
    }

    // 灰盒禁渲染（保留为逻辑体：碰撞/脚本/tag/layer 不动）
    static GameObject Hide(string name)
    {
        var go = GameObject.Find(name);
        if (go == null) { Debug.LogWarning($"[KitPlacer] 未找到 {name}"); return null; }
        var r = go.GetComponent<Renderer>();
        if (r) r.enabled = false;
        return go;
    }

    // 缩放归一（子物体不变形），原世界尺寸转移给碰撞体，保证碰撞不变
    static GameObject Normalize(string name, float sphereWorldRadius = 0f)
    {
        var go = Hide(name);
        if (go == null) return null;
        var s = go.transform.localScale;
        go.transform.localScale = Vector3.one;
        var bc = go.GetComponent<BoxCollider>();
        if (bc) { bc.size = s; bc.center = Vector3.zero; }
        var sc = go.GetComponent<SphereCollider>();
        if (sc) { sc.radius = sphereWorldRadius; sc.center = Vector3.zero; }
        return go;
    }

    // 地面整片铺设：2m 网格 A/B 交替 + 随机转向
    static void Tiled(string grayName, float x0, float z0, int w, int d, float y)
    {
        Hide(grayName);
        for (int i = 0; i < w / 2; i++)
            for (int j = 0; j < d / 2; j++)
            {
                var go = Spawn((i + j) % 2 == 0 ? "SM_FloorTile_A" : "SM_FloorTile_B",
                               new Vector3(x0 + 1 + 2 * i, y, z0 + 1 + 2 * j),
                               Random.Range(0, 4) * 90f);
                if (go) go.name = $"VIZ_{grayName}_{i:00}{j:00}";
            }
    }

    // 一面墙：灰盒禁渲染；4m 墙段两层铺满（A/B/C/D 加权随机，避免相邻重复），段宽按面长均分
    static void WallRun(string grayName, float cx, float cz, bool alongX, float len, float yaw)
    {
        Hide(grayName);
        // 注：曾有墙后深色挡板封装配缝透视，M3-5 验收反馈"墙后黑墙穿帮"，已删除
        int n = Mathf.CeilToInt(len / 4f);
        float w = len / n;
        string prev = "";
        for (int layer = 0; layer < 2; layer++)
        {
            float ly = layer * 2.94f;   // 层间重叠 0.12：盖住上下段交界处倒角消耗+jitter 造成的装配隙缝
            Vector3 nudge = layer == 1 ? Quaternion.Euler(0, yaw, 0) * Vector3.forward * 0.012f
                                       : Vector3.zero;  // 上层墙面外凸 12mm：防前表面共面闪烁，兼作接缝线脚
            for (int i = 0; i < n; i++)
            {
                float t = -len / 2f + w / 2f + i * w;
                var pos = alongX ? new Vector3(cx + t, ly, cz)
                                 : new Vector3(cx, ly, cz + t);
                var asset = PickWallVariant(prev);
                prev = asset;
                var go = Spawn(asset, pos + nudge, yaw);
                // 横向微放大 2.5%：相邻段端面各让出 0.025 倒角后仍保有重叠，消掉竖直交界缝
                if (go) go.transform.localScale = new Vector3(w / 4f * 1.025f, 1f, 1f);
            }
        }
    }

    // 石台贴面单块墙段（sx=0.5→2m / 0.75→3m / 1→4m）
    static void WallPiece(string asset, Vector3 pos, float yaw, float sx)
    {
        var go = Spawn(asset, pos, yaw);
        if (go) go.transform.localScale = new Vector3(sx * 1.04f, 1f, 1f);  // 相邻贴面同样留重叠
    }

    // ---------- 墙体变体随机 ----------
    // 池权重 A×2 / B×2 / C×1 / D×1；避免与上一块相同（随机但不呆板）
    static string PickWallVariant(string prev)
    {
        string[] pool = { "SM_Wall_A", "SM_Wall_A", "SM_Wall_B", "SM_Wall_B", "SM_Wall_C", "SM_Wall_D" };
        var pick = pool[Random.Range(0, pool.Length)];
        for (int tries = 0; tries < 8 && pick == prev; tries++)
            pick = pool[Random.Range(0, pool.Length)];
        return pick;
    }

    // ---------- 火焰半透明材质 ----------
    // URP/Unlit + Alpha 混合：FBX 内嵌的不透明 M_Fire 材质换为独立半透明材质
    static Material EnsureFireMaterial(string name, Color c)
    {
        string path = $"Assets/Art/Static/temple/{name}.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null)
        {
            var shader = Shader.Find("Universal Render Pipeline/Unlit");
            if (shader == null) { Debug.LogError("[KitPlacer] 找不到 URP/Unlit shader，火焰材质创建失败"); return null; }
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

    // 火盆视觉件：把 FBX 内嵌的 M_Fire / M_Fire_Core 槽换为半透明版（其余槽不动）
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

    // 火盆点光：确保火盆附近（水平 2.5m 内）存在 Torch* 点光并对齐火焰光心，
    // 让照明从火焰本身发出（盆口 0.85 与焰尖 1.38 之间偏下）；缺失（如 B 厅火盆）则新建。
    // 光照参数在此统一定义，重跑菜单幂等生效。
    static void EnsureTorchLight(Vector3 brazierPos, string lightName)
    {
        const float FireCoreY = 1.1f;   // 火焰光心高度
        const float MaxDist = 2.5f;     // 火盆与光的水平匹配半径
        var firePos = new Vector3(brazierPos.x, brazierPos.y + FireCoreY, brazierPos.z);
        Light l = null;
        foreach (var c in Object.FindObjectsByType<Light>(
                     FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (c.type != LightType.Point || !c.name.StartsWith("Torch")) continue;
            var p = c.transform.position;
            if (new Vector2(p.x - brazierPos.x, p.z - brazierPos.z).magnitude <= MaxDist)
            { l = c; break; }
        }
        if (l == null)
        {
            l = new GameObject(lightName).AddComponent<Light>();
            l.type = LightType.Point;
            Debug.Log($"[KitPlacer] 新建火盆点光 {lightName} @ {brazierPos}");
        }
        l.transform.position = firePos;
        l.color = new Color(1f, 0.60f, 0.30f);      // 暖橙
        l.intensity = 2.2f;
        l.range = 8.5f;
        l.shadows = LightShadows.Soft;              // 石柱/墙体的投影让火光有体积感
        EditorUtility.SetDirty(l);
    }

    // ---------- M3-5 光照氛围（清晨版） ----------
    // 验收反馈：M3-4 夜景太暗（可玩性佳但看不清），改为清晨古墓——
    // 明亮晨光 + 淡金天空 + 浅雾；火光保留（暗处/室内仍有暖光）。
    // 幂等：每次重建场景统一施加；后续微调数值只改这一处。
    static void ApplyLightingMood()
    {
        // 雾：线性距离雾 10~60m（M3-5 验收：低空雾团效果偏假，恢复此前线性雾方案；
        // 雾团代码保留在 SpawnFogPatches，待地图扩大后再启用）
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogColor = new Color(0.50f, 0.49f, 0.47f);
        RenderSettings.fogStartDistance = 10f;
        RenderSettings.fogEndDistance = 60f;
        // 环境光：清晨天光（M3-5 二调：0.22→0.16，压暗一档）
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.16f, 0.17f, 0.20f);
        // 太阳 → 清晨暖阳（斜射、暖金、柔和阴影；M3-5 二调：0.75→0.55）
        var sun = RenderSettings.sun;
        if (sun != null)
        {
            sun.intensity = 0.55f;
            sun.color = new Color(1.0f, 0.90f, 0.72f);
            sun.shadows = LightShadows.Soft;
            EditorUtility.SetDirty(sun);
        }
        // 天光补光：无阴影弱冷光从对侧（西向东）照，防止背光侧墙面死黑（清晨天空散射的近似）
        var fill = EnsureFillLight();
        if (fill != null)
        {
            fill.transform.rotation = Quaternion.Euler(35f, 90f, 0f);   // 从西上方照向东（主光对侧）
            fill.intensity = 0.18f;
            fill.color = new Color(0.62f, 0.70f, 0.85f);
            fill.shadows = LightShadows.None;
            EditorUtility.SetDirty(fill);
        }
        // 天空：程序化清晨天空（淡蓝穹顶 + 微亮地平线下），全局生效所见即所得
        const string skyPath = "Assets/Art/Static/temple/M_MorningSky.mat";
        var sky = AssetDatabase.LoadAssetAtPath<Material>(skyPath);
        if (sky == null)
        {
            var sh = Shader.Find("Skybox/Procedural");
            if (sh != null)
            {
                sky = new Material(sh);
                sky.name = "M_MorningSky";
                AssetDatabase.CreateAsset(sky, skyPath);
            }
            else Debug.LogWarning("[KitPlacer] 找不到 Skybox/Procedural shader");
        }
        if (sky != null)
        {
            sky.SetColor("_SkyTint", new Color(0.68f, 0.72f, 0.82f));      // 清晨淡蓝
            sky.SetColor("_GroundColor", new Color(0.42f, 0.40f, 0.37f));  // 地平线下
            sky.SetFloat("_Exposure", 0.95f);                              // M3-5 二调：1.35→0.95（压暗一档）
            sky.SetFloat("_AtmosphereThickness", 0.55f);
            sky.SetFloat("_SunSize", 0.03f);
            EditorUtility.SetDirty(sky);
            RenderSettings.skybox = sky;
        }
        // 相机：保持 Skybox 清屏（配合清晨天空）
        var cam = Camera.main;
        if (cam != null)
        {
            cam.clearFlags = CameraClearFlags.Skybox;
            EditorUtility.SetDirty(cam);
        }
        Debug.Log("[KitPlacer] 光照氛围已施加（清晨）：晨光 0.55 / 线性雾 10~60m / 淡蓝天空");
    }

    // 天光补光：确保存在一盏名为 FillLight 的无影方向光（重建时复用，幂等配置）
    static Light EnsureFillLight()
    {
        foreach (var c in Object.FindObjectsByType<Light>(
                     FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (c.name == "FillLight" && c.type == LightType.Directional) return c;
        var go = new GameObject("FillLight");
        var l = go.AddComponent<Light>();
        l.type = LightType.Directional;
        Debug.Log("[KitPlacer] 新建天光补光 FillLight");
        return l;
    }

    // ---------- M3-5 低空可见雾团 ----------
    // 验收反馈"看不出有雾、都在空中"：关掉全局距离雾，改为低空（0.8~2.2m）一团团
    // 明显可见的白雾缓缓飘动（每团 2~3 张交叉雾片，FogDrift 脚本驱动漂移/呼吸）。
    static void SpawnFogPatches()
    {
        var mat = EnsureFogMaterial();
        if (mat == null) return;
        // 雾团锚点（x,z）：柱子间/墙角/火盆附近浓，中央走道留薄
        var spots = new[] {
            new Vector2(-7f, -3f), new Vector2(-4.5f, 4f), new Vector2(6f, -2f),
            new Vector2(5.5f, 6f), new Vector2(-6f, 6.5f), new Vector2(0.5f, 10.6f),
            new Vector2(-5f, 13f), new Vector2(5f, 14f), new Vector2(-3f, 19f), new Vector2(4f, 20f) };
        int cards = 0;
        foreach (var c in spots)
        {
            float baseY = Random.Range(0.9f, 2.0f);
            int n = Random.Range(2, 4);
            for (int k = 0; k < n; k++)
            {
                var g = GameObject.CreatePrimitive(PrimitiveType.Quad);
                g.name = $"VIZ_Fog_{vizCount++:D3}";
                Object.DestroyImmediate(g.GetComponent<Collider>());   // 无碰撞，不挡玩家
                g.transform.SetPositionAndRotation(
                    new Vector3(c.x + Random.Range(-1.2f, 1.2f),
                                baseY + Random.Range(-0.3f, 0.3f),
                                c.y + Random.Range(-1.2f, 1.2f)),
                    Quaternion.Euler(Random.Range(-8f, 8f), Random.Range(0f, 360f), Random.Range(-8f, 8f)));
                float s = Random.Range(3f, 5.5f);
                g.transform.localScale = new Vector3(s, s * Random.Range(0.6f, 0.85f), 1f);
                var mr = g.GetComponent<MeshRenderer>();
                mr.sharedMaterial = mat;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                mr.receiveShadows = false;
                g.AddComponent<FogDrift>().Init(Random.Range(0.5f, 1.6f),
                    Random.Range(0.15f, 0.4f), Random.Range(0f, 6.28f), 0.10f);
                cards++;
            }
        }
        Debug.Log($"[KitPlacer] 低空雾团已摆放：{spots.Length} 团 / {cards} 片");
    }

    // 雾片材质（URP Unlit 透明、双面、不写深度；幂等施加便于调参）
    static Material EnsureFogMaterial()
    {
        const string path = "Assets/Art/Static/temple/M_FogCard.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null)
        {
            var shader = Shader.Find("Universal Render Pipeline/Unlit");
            if (shader == null) { Debug.LogError("[KitPlacer] 找不到 URP/Unlit shader，雾材质创建失败"); return null; }
            m = new Material(shader);
            m.name = "M_FogCard";
            AssetDatabase.CreateAsset(m, path);
        }
        m.SetTexture("_BaseMap", EnsureFogTexture());
        m.SetColor("_BaseColor", new Color(0.76f, 0.79f, 0.83f, 0.24f));   // 清晨冷灰白：可见但不挡视线
        m.SetFloat("_Surface", 1f);                                        // Transparent
        m.SetFloat("_Blend", 0f);                                          // Alpha 混合
        m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
        m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        m.SetFloat("_ZWrite", 0f);
        m.SetFloat("_Cull", (float)UnityEngine.Rendering.CullMode.Off);   // 双面：从任意侧可见
        m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
        EditorUtility.SetDirty(m);
        return m;
    }

    // 雾团纹理（程序化软团噪声，仅生成一次；径向淡出边缘防方片穿帮）
    static Texture2D EnsureFogTexture()
    {
        const string path = "Assets/Art/Static/temple/T_GroundFog.png";
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        if (tex != null) return tex;
        const int S = 256;
        var t = new Texture2D(S, S, TextureFormat.RGBA32, false);
        var px = new Color[S * S];
        for (int y = 0; y < S; y++)
            for (int x = 0; x < S; x++)
            {
                float u = x / (S - 1f), v = y / (S - 1f);
                float n = 0f, amp = 1f, freq = 3f;
                for (int o = 0; o < 4; o++)
                { n += amp * Mathf.PerlinNoise(u * freq + 7.3f, v * freq + 2.9f); amp *= 0.5f; freq *= 2f; }
                n /= 1.875f;
                float r = Mathf.Sqrt((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 2f;
                float fade = Mathf.Clamp01(1f - r); fade = fade * fade * (3f - 2f * fade);
                float a = Mathf.Clamp01((n - 0.42f) * 2.2f) * fade;
                px[y * S + x] = new Color(1f, 1f, 1f, a);
            }
        t.SetPixels(px); t.Apply();
        System.IO.File.WriteAllBytes(path, t.EncodeToPNG());
        Object.DestroyImmediate(t);
        AssetDatabase.ImportAsset(path);
        if (AssetImporter.GetAtPath(path) is TextureImporter imp)
        {
            imp.alphaIsTransparency = true;
            imp.wrapMode = TextureWrapMode.Clamp;
            imp.SaveAndReimport();
        }
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }

    static void CleanupOld()
    {
        int n = 0;
        foreach (var t in Object.FindObjectsByType<Transform>(
                     FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (t.name.StartsWith("VIZ_") || t.name.StartsWith("Torch")) { Object.DestroyImmediate(t.gameObject); n++; }
        if (n > 0) Debug.Log($"[KitPlacer] 已清理旧视觉件/火光 {n} 个");
    }
}
