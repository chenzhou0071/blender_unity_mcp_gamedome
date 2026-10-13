using UnityEngine;
using UnityEditor;
using UnityEngine.SceneManagement;
using UnityEditor.SceneManagement;

// M6-1 Task6: 植被散布器（菜单 Demo/散布植被；幂等——每次清除 OUT_Veg_* 全量重建）
//   · 射线 (x,40,z) 向下且 IgnoreTriggers（避开过渡 Zone 触发盒），要求命中 OUT_SM_CanyonTerrain 根
//   · 坡度 v4（用户反馈"坡上要有草树"）：草 n.y>0.60（<53°）/ 灌木 >0.72 / 树 >0.78；|x|>48 不撒；
//     蜿蜒路带（|x-PathX(z)|<3.2）不撒树/灌木（草可）
//   · 高程带：草 z44-176；灌木/树 z46-126（河谷 126-176 只草——按计划）；河谷洼地 z140-160 且 y<-2 不撒草
//   · v4 样式扩充（用户反馈"多一些样式"）：树 6 样式 C30/A15/B15/D18/E12/F10 + 12% 空穴；
//     灌木 3 样式均分；草 2 样式（芦苇 15%）。密度：草 5m 格×2 / 灌 8m 格×2 / 树 5m 格
//   · 草坪：OUT_Veg_Lawn 1m 网格 + 噪声有机边缘（±34 名义 ±噪声≈5m），路带开槽露沙色弯土路（M_Lawn）
//   · 草材质 enableInstancing；树/灌木标 BatchingStatic；yaw 随机、缩放 0.8-1.3；固定种子=可复现
//   · v5（2026-10-13 用户反馈"坡上树换巨石"）：巨石岗域 z90-132 且 |x|<16 不撒树/灌木、草坪退让
//   · v6（2026-10-14 用户反馈"树有颗挡住路了"）：树冠水平半径（localBounds 水平两轴×实例缩放，
//     避开随机 yaw 后世界 AABB 膨胀 ~1.4×）距路心 < 1.8 的不留（= 冠缘悬入路面 ≥ 0.4m）；超限即销毁
public static class VegetationScatter
{
    const string FbxDir      = "Assets/Art/Static/outdoor";
    const string RootName    = "OUT_Veg_Root";
    const string TerrainRoot = "OUT_SM_CanyonTerrain";
    // 密度与区域（草地 y≈-1.7 平坦草原；z46 出门即林）
    //  v4 密度（2026-10-13 用户反馈后二次扩充：坡上补植、覆盖 ±48、样式扩充）：
    //  草 5m 格×2 丛；灌木 8m 格×2 丛；树 5m 格——预期 ≈ 草 900 / 灌 220 / 树 190
    const float GrassGrid = 5f, BushGrid = 8f, TreeGrid = 5f;
    const float XLimit = 48f;                     // 散布半宽（崖壁由坡度过滤兜底）
    const float GrassSlope = 0.60f;               // 草可长到 ~53° 坡（山坡须有草）
    const float BushSlope  = 0.72f;
    const float TreeSlope  = 0.78f;
    const float GrassZ0 = 44f, GrassZ1 = 176f;    // 草区（含河谷段）
    const float TreeZ0  = 46f, TreeZ1  = 126f;    // 灌木/树区（河谷只草）
    const float TreeThinZ = 96f;                  // 岩缝后渐稀阈值
    const float PathHalfTree = 3.2f;              // 树/灌木让路半宽
    const float PathHalfLawn = 2.2f;              // 草坪开槽半宽（露出沙色土路）
    const int   Seed = 20261013;
    static int seq;

    // 蜿蜒林间路中心线：z'=z-46；z=46 处 cx=0 正对门口、起步平缓，随后先右摆≈2m、中段回中、后段左甩≈5m
    static float PathX(float z)
    {
        float t = z - 46f;
        return 6f * Mathf.Sin(t / 13f) * Mathf.Cos(t / 17f);
    }

    [MenuItem("Demo/散布植被")]
    public static void Scatter()
    {
        if (EditorApplication.isPlaying)
        {
            Debug.LogWarning("[VegetationScatter] 请先退出 Play 模式再执行");
            return;
        }

        string[] names = { "SM_GrassTuft", "SM_Grass_Reed", "SM_Bush_A", "SM_Bush_B", "SM_Bush_C", "SM_Tree_A", "SM_Tree_B", "SM_Tree_C", "SM_Tree_D", "SM_Tree_E", "SM_Tree_F" };
        var prefabs = new GameObject[names.Length];
        for (int i = 0; i < names.Length; i++)
        {
            prefabs[i] = AssetDatabase.LoadAssetAtPath<GameObject>($"{FbxDir}/{names[i]}.fbx");
            if (prefabs[i] == null)
            {
                Debug.LogError($"[VegetationScatter] 缺少资产 {FbxDir}/{names[i]}.fbx");
                return;
            }
        }
        EnableGrassInstancing();

        // 清旧（幂等：清所有顶层 OUT_Veg_*；先收集再销毁——边遍历边销毁会因 root 销毁后
        // 访问其子对象报 MissingReferenceException）
        var olds = new System.Collections.Generic.List<GameObject>();
        foreach (var t in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsSortMode.None))
            if (t.parent == null && t.name.StartsWith("OUT_Veg_"))
                olds.Add(t.gameObject);
        foreach (var go in olds) UnityEngine.Object.DestroyImmediate(go);

        Random.InitState(Seed);
        seq = 0;
        var root  = new GameObject(RootName);
        var gGrass = new GameObject("OUT_Veg_Grass").transform; gGrass.SetParent(root.transform, false);
        var gBush  = new GameObject("OUT_Veg_Bush").transform;  gBush.SetParent(root.transform, false);
        var gTree  = new GameObject("OUT_Veg_Tree").transform;  gTree.SetParent(root.transform, false);

        BuildLawn(root.transform);   // 草坪先铺（此时树/灌木未生成，射线只碰地形）

        int nG = 0, nB = 0, nA = 0, nB2 = 0, nC = 0, nD = 0, nE = 0, nF = 0;

        // ---- 草：5m 格×2 丛（z44-176；坡上限 53°；河谷洼地 z140-160 且 y<-2 跳过；芦苇 15%）----
        for (float z = GrassZ0; z < GrassZ1 + 0.01f; z += GrassGrid)
            for (float x = -XLimit; x < XLimit + 0.01f; x += GrassGrid)
                for (int k = 0; k < 2; k++)
                {
                    Vector3 p, n;
                    if (!Sample(x, z, out p, out n)) continue;
                    if (n.y < GrassSlope) continue;
                    if (p.z >= 140f && p.z <= 160f && p.y < -2.0f) continue;
                    Place(Random.value < 0.15f ? prefabs[1] : prefabs[0], p, gGrass, false); nG++;
                }

        // ---- 灌木：8m 格×2 丛（z46-126 与树同区；河谷只草；让路带；3 样式均分）----
        for (float z = TreeZ0; z < TreeZ1 + 0.01f; z += BushGrid)
            for (float x = -XLimit; x < XLimit + 0.01f; x += BushGrid)
                for (int k = 0; k < 2; k++)
                {
                    Vector3 p, n;
                    if (!Sample(x, z, out p, out n)) continue;
                    if (n.y < BushSlope) continue;
                    if (Mathf.Abs(p.x - PathX(p.z)) < PathHalfTree) continue;
                    if (p.z > 90f && p.z < 132f && Mathf.Abs(p.x) < 16f) continue;   // v5 巨石岗域：坡上树/灌换巨石
                    Place(prefabs[2 + Random.Range(0, 3)], p, gBush, true); nB++;
                }

        // ---- 树：5m 格（z46-126；蜿蜒路带不撒；z>96 渐稀 50%；12% 空穴；6 样式加权）----
        for (float z = TreeZ0; z < TreeZ1 + 0.01f; z += TreeGrid)
            for (float x = -XLimit; x < XLimit + 0.01f; x += TreeGrid)
            {
                Vector3 p, n;
                if (!Sample(x, z, out p, out n)) continue;
                if (n.y < TreeSlope) continue;
                if (Mathf.Abs(p.x - PathX(p.z)) < PathHalfTree) continue;
                if (p.z > 90f && p.z < 132f && Mathf.Abs(p.x) < 16f) continue;   // v5 巨石岗域：坡上树/灌换巨石
                if (z > TreeThinZ && Random.value < 0.5f) continue;
                if (Random.value < 0.12f) continue;
                float r = Random.value;
                int pi = r < 0.30f ? 2          // C 主乔木
                       : r < 0.45f ? 0          // A 圆锥层冠
                       : r < 0.60f ? 1          // B 高瘦
                       : r < 0.78f ? 3          // D 阔叶圆冠
                       : r < 0.90f ? 4          // E 针叶杉
                       : 5;                     // F 枯树
                GameObject pf = prefabs[pi + 5];
                var go = Place(pf, p, gTree, true);
                // v6 树冠压路剔除：树冠水平半径 = max(localBounds.x/y) × 实例缩放（同管线树资产 local z=高轴）；
                // 不用世界 bounds：随机 yaw 会把水平 AABB 膨胀至 (a+b)/√2（≈1.4×）导致误剔。
                // 判定：冠缘悬入开槽路面 ≥0.4m（dPath − cr < 2.2 − 0.4）即销毁
                float cr = 0f;
                foreach (var rd in go.GetComponentsInChildren<Renderer>(true))
                {
                    var e = rd.localBounds.extents;
                    cr = Mathf.Max(cr, Mathf.Max(e.x, e.y));
                }
                cr *= go.transform.localScale.x;
                if (cr > Mathf.Abs(p.x - PathX(p.z)) - 1.8f)
                {
                    UnityEngine.Object.DestroyImmediate(go);
                    continue;
                }
                if (pf == prefabs[7]) nC++;
                else if (pf == prefabs[5]) nA++;
                else if (pf == prefabs[6]) nB2++;
                else if (pf == prefabs[8]) nD++;
                else if (pf == prefabs[9]) nE++;
                else nF++;
            }

        int nT = nA + nB2 + nC + nD + nE + nF;
        Debug.Log($"[VegetationScatter] 散布完成：草 {nG} / 灌木 {nB} / 树 {nT}" +
                  $"（A {nA} / B {nB2} / C {nC} / D {nD} / E {nE} / F {nF}）" +
                  "——预期量级 草 700-1100 / 灌木 160-280 / 树 150-260");
        if (nG < 500 || nG > 1200) Debug.LogWarning($"[VegetationScatter] 草 {nG} 偏离预期 700-1100（查射线条件与密度常量）");
        if (nB < 120 || nB > 340) Debug.LogWarning($"[VegetationScatter] 灌木 {nB} 偏离预期 160-280");
        if (nT < 110 || nT > 300) Debug.LogWarning($"[VegetationScatter] 树 {nT} 偏离预期 150-260");

        EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
        EditorSceneManager.SaveOpenScenes();
        AssetDatabase.SaveAssets();
        Debug.Log("[VegetationScatter] 场景已保存（OUT_Veg_Root：草/灌木/树三组）");
    }

    // 采样：格内抖动 ±2.2m → 从 y40 向下 → 命中地形根（坡度不在此判，由各散布循环按类型分级）
    static bool Sample(float x, float z, out Vector3 hit, out Vector3 nrm)
    {
        hit = Vector3.zero; nrm = Vector3.up;
        float px = x + Random.Range(-2.2f, 2.2f);
        float pz = z + Random.Range(-2.2f, 2.2f);
        if (Mathf.Abs(px) > XLimit) return false;
        RaycastHit h;
        if (!Physics.Raycast(new Vector3(px, 40f, pz), Vector3.down, out h, 200f, ~0, QueryTriggerInteraction.Ignore))
            return false;
        if (h.collider.transform.root.name != TerrainRoot) return false;
        hit = h.point; nrm = h.normal;
        return true;
    }

    static GameObject Place(GameObject prefab, Vector3 pos, Transform parent, bool markStatic)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        go.name = $"Veg_{prefab.name}_{seq++:D4}";
        go.transform.position = pos;
        go.transform.localScale = Vector3.one * Random.Range(0.8f, 1.3f);
        go.transform.rotation = Quaternion.Euler(0, Random.Range(0f, 360f), 0) * prefab.transform.rotation;
        go.transform.SetParent(parent, true);
        if (markStatic) GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        return go;
    }

    // 草坪（v4）：1m 网格贴地形（+0.03 防 z-fighting）；左右边界 ±34 + 噪声摆动（有机毛边，
    // 消除方块感）；蜿蜒路带开槽露沙色土路；谷口 z118+ 概率跳格渐变收边；顶点坡度 0.80
    static float Hash01(float x, float z)
    {
        float v = Mathf.Sin(x * 127.1f + z * 311.7f) * 43758.5453f;
        return v - Mathf.Floor(v);
    }

    // 有机边界噪声：7m 大尺度（±5m 摆动）+ 细尺度（±1.5m）；确定性、可复现
    static float EdgeNoise(float x, float z)
    {
        return (Hash01(Mathf.Floor(x / 7f), Mathf.Floor(z / 7f)) * 2f - 1f) * 5f
             + (Hash01(x * 0.37f, z * 0.37f) * 2f - 1f) * 1.5f;
    }

    static void BuildLawn(Transform parent)
    {
        const float step = 1f, z0 = 46f, z1 = 126f;
        int nx = Mathf.RoundToInt((XLimit * 2f) / step) + 1;
        int nz = Mathf.RoundToInt((z1 - z0) / step) + 1;

        var pos = new System.Collections.Generic.List<Vector3>();
        var ok  = new bool[nx, nz];
        var idx = new int[nx, nz];
        for (int ix = 0; ix < nx; ix++)
            for (int iz = 0; iz < nz; iz++)
            {
                idx[ix, iz] = -1;
                RaycastHit h;
                ok[ix, iz] = Physics.Raycast(new Vector3(-XLimit + ix * step, 40f, z0 + iz * step),
                                             Vector3.down, out h, 200f, ~0, QueryTriggerInteraction.Ignore)
                             && h.collider.transform.root.name == TerrainRoot && h.normal.y >= 0.80f;
                if (ok[ix, iz]) { idx[ix, iz] = pos.Count; pos.Add(h.point + Vector3.up * 0.03f); }
            }

        var tris = new System.Collections.Generic.List<int>();
        for (int ix = 0; ix < nx - 1; ix++)
            for (int iz = 0; iz < nz - 1; iz++)
            {
                if (!ok[ix, iz] || !ok[ix + 1, iz] || !ok[ix, iz + 1] || !ok[ix + 1, iz + 1]) continue;
                float xc = -XLimit + (ix + 0.5f) * step, zc = z0 + (iz + 0.5f) * step;
                float en = EdgeNoise(xc, zc);
                if (Mathf.Abs(xc) > 34f + en) continue;                               // 左右有机边界（±34 名义 ± 噪声）
                if (zc > 88f && zc < 134f && Mathf.Abs(xc) < 16f + en * 0.5f) continue; // v5 巨石岗域：草坪退让露岩土
                if (zc > 118f + en * 0.8f && Random.value < (zc - 118f - en * 0.8f) / 8f * 0.85f) continue; // 谷口渐变收边
                if (Mathf.Abs(xc - PathX(zc)) < PathHalfLawn) continue;              // 路带开槽
                int a = idx[ix, iz], b = idx[ix + 1, iz], c = idx[ix, iz + 1], d = idx[ix + 1, iz + 1];
                tris.Add(a); tris.Add(c); tris.Add(b);
                tris.Add(b); tris.Add(c); tris.Add(d);
            }

        var mesh = new Mesh { name = "LawnMesh" };
        mesh.SetVertices(pos);
        mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals();
        var go = new GameObject("OUT_Veg_Lawn");
        go.transform.SetParent(parent, false);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        go.AddComponent<MeshRenderer>().sharedMaterial = LawnMaterial();
        GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        Debug.Log($"[VegetationScatter] 草坪：{pos.Count} 顶点 / {tris.Count / 3} 三角（z46-126，路带开槽）");
    }

    static Material LawnMaterial()
    {
        const string path = "Assets/Settings/M_Lawn.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null)
        {
            var sh = Shader.Find("Universal Render Pipeline/Lit");
            if (sh == null) { Debug.LogError("[VegetationScatter] URP/Lit 未找到，草坪材质创建失败"); return null; }
            m = new Material(sh);
            AssetDatabase.CreateAsset(m, path);
        }
        m.SetColor("_BaseColor", new Color(0.26f, 0.37f, 0.13f));  // 草绿（略亮于草簇 M_Grass 0.20/0.30/0.11）
        m.SetFloat("_Smoothness", 0.05f);
        EditorUtility.SetDirty(m);
        AssetDatabase.SaveAssets();
        return m;
    }

    static void EnableGrassInstancing()
    {
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath($"{FbxDir}/SM_GrassTuft.fbx"))
        {
            var m = o as Material;
            if (m != null && !m.enableInstancing)
            {
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
            }
        }
        AssetDatabase.SaveAssets();
    }
}
