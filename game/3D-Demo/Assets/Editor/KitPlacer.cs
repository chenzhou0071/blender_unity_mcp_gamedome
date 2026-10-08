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
        Spawn("SM_Altar", new Vector3(0, 3f, 19f), 0f);

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

        // ---- 6) 装饰：石柱×4 / 破柱×2（一立一躺）/ 火盆×4 / 台阶 / 碎石×6
        foreach (var x in new[] { -7f, 7f })
            foreach (var z in new[] { -5f, 5f })
                Spawn("SM_Pillar_Whole", new Vector3(x, 0, z), Random.Range(0, 4) * 90f);
        Spawn("SM_Pillar_Broken", new Vector3(-6.5f, 0, 2.5f), 40f);
        var fallen = Spawn("SM_Pillar_Broken", new Vector3(6.2f, 0.30f, 4.5f), 0f);
        if (fallen) fallen.transform.rotation = Quaternion.Euler(0, 20, 0)
            * Quaternion.Euler(0, 0, 90) * Quaternion.Euler(270, 0, 0);
        foreach (var p in new[] {
            new Vector3(-3, 0, -6f), new Vector3(3, 0, -6f),
            new Vector3(-3, 0, 12.5f), new Vector3(3, 0, 12.5f) })
        {
            RetintFire(Spawn("SM_Brazier", p, 0f));
            AlignTorchLight(p);   // 火盆点光对齐火焰光心（重跑不回退）
        }
        Spawn("SM_Stairs", new Vector3(0, 0, 20.9f), 180f);
        var rubble = new[] {
            new Vector3(2.4f, 0, 7.2f), new Vector3(-2.6f, 0, 7.3f),
            new Vector3(-9.2f, 0, -6.5f), new Vector3(8.8f, 0, -6.8f),
            new Vector3(3.6f, 0, 13.2f), new Vector3(-5.4f, 0, 20.4f) };
        for (int i = 0; i < rubble.Length; i++)
        {
            var go = Spawn(i % 2 == 0 ? "SM_Debris_A" : "SM_Debris_B", rubble[i],
                           Random.Range(0, 4) * 90f);
            if (go) go.transform.localScale = Vector3.one * Random.Range(0.8f, 1.25f);
        }

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
        // 墙后挡板：封住墙板内腔与装配缝的掠射透视（细白缝透出天空盒的根因），
        // 深色石面从缝里看即"石缝阴影"观感；位于墙板背面外 0.1m，正常视角被墙板遮住
        {
            var back = GameObject.CreatePrimitive(PrimitiveType.Cube);
            back.name = $"VIZ_Back_{grayName}";
            Object.DestroyImmediate(back.GetComponent<Collider>());
            var front = Quaternion.Euler(0, yaw, 0) * Vector3.forward;   // 正面（朝室内）方向
            back.transform.rotation = Quaternion.Euler(0, yaw, 0);
            back.transform.position = new Vector3(cx, 2.95f, cz) - front * 0.35f;
            back.transform.localScale = new Vector3(len, 6f, 0.12f);
            back.GetComponent<MeshRenderer>().sharedMaterial = EnsureWallBackMaterial();
            vizCount++;
        }
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

    // ---------- 墙后挡板材质 ----------
    // 深色粗糙石面：墙板装配缝掠射透视时看到的"内衬"，不再透出天空盒
    static Material EnsureWallBackMaterial()
    {
        const string path = "Assets/Art/Static/temple/M_WallBack.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) { Debug.LogError("[KitPlacer] 找不到 URP/Lit shader，挡板材质创建失败"); return null; }
            m = new Material(shader);
            m.name = "M_WallBack";
            AssetDatabase.CreateAsset(m, path);
        }
        m.SetColor("_BaseColor", new Color(0.17f, 0.14f, 0.11f, 1f));
        m.SetFloat("_Smoothness", 0.05f);
        m.SetFloat("_Metallic", 0f);
        EditorUtility.SetDirty(m);
        return m;
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

    // 火光对齐：把火盆附近（水平 2.5m 内）的 Torch* 点光移到火焰光心位置，
    // 让照明从火焰本身发出，而不是悬在盆口上方
    static void AlignTorchLight(Vector3 brazierPos)
    {
        const float FireCoreY = 1.1f;   // 火焰光心：盆口 0.85 与焰尖 1.38 之间偏下
        const float MaxDist = 2.5f;     // 火盆与光的水平匹配半径
        var firePos = new Vector3(brazierPos.x, brazierPos.y + FireCoreY, brazierPos.z);
        foreach (var l in Object.FindObjectsByType<Light>(
                     FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (l.type != LightType.Point || !l.name.StartsWith("Torch")) continue;
            var p = l.transform.position;
            if (new Vector2(p.x - brazierPos.x, p.z - brazierPos.z).magnitude > MaxDist) continue;
            l.transform.position = firePos;
            EditorUtility.SetDirty(l);
        }
    }

    static void CleanupOld()
    {
        int n = 0;
        foreach (var t in Object.FindObjectsByType<Transform>(
                     FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (t.name.StartsWith("VIZ_")) { Object.DestroyImmediate(t.gameObject); n++; }
        if (n > 0) Debug.Log($"[KitPlacer] 已清理旧视觉件 {n} 个");
    }
}
