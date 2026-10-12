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
        EnsureGroundOutside();      // 收编灰盒遗留大地坪：材质对齐峡谷地形色（用户：灰板与地面色不一致）
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
}