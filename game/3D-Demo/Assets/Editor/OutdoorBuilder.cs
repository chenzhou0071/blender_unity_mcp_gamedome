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
}