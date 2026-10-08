using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class GrayboxBuilder
{
    [MenuItem("Demo/构建灰盒关卡")]
    public static void Build()
    {
        EnsureLayer(LevelSpec.LayerClimbable);
        EnsureTag(LevelSpec.TagPushable);
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // 地板
        Box("FloorA", new Vector3(0, -0.25f, 0), new Vector3(20, 0.5f, 16));
        Box("FloorB", new Vector3(0, -0.25f, 15), new Vector3(16, 0.5f, 14));
        // Room A 外墙
        Box("WallA_S", new Vector3(0, WallH2(), -8), new Vector3(20, L2(), 0.5f));
        Box("WallA_E", new Vector3(10, L2(), 0), new Vector3(0.5f, L2(), 16));
        Box("WallA_W", new Vector3(-10, L2(), 0), new Vector3(0.5f, L2(), 16));
        // 共用墙 + 门洞（左右两段 + 门楣）
        Box("WallAB_L", new Vector3(-5.75f, L2(), 8), new Vector3(8.5f, L2(), 0.5f));
        Box("WallAB_R", new Vector3(5.75f, L2(), 8), new Vector3(8.5f, L2(), 0.5f));
        Box("WallAB_Top", new Vector3(0, 5f, 8), new Vector3(3f, 2f, 0.5f));
        // Room B 外墙
        Box("WallB_E", new Vector3(8, L2(), 15), new Vector3(0.5f, L2(), 14));
        Box("WallB_W", new Vector3(-8, L2(), 15), new Vector3(0.5f, L2(), 14));
        Box("WallB_N", new Vector3(0, L2(), 22), new Vector3(16, L2(), 0.5f));

        // 石门
        var door = Box("StoneDoor", LevelSpec.DoorPos, new Vector3(3f, 4f, 0.4f));
        door.AddComponent<StoneDoor>();

        // 攀爬石台
        var ledge = Box("ClimbableLedge", LevelSpec.LedgeCenter, LevelSpec.LedgeSize);
        ledge.layer = LayerMask.NameToLayer(LevelSpec.LayerClimbable);

        // 压力板 + 推石块
        var plate = Box("PressurePlate", LevelSpec.PlatePos, new Vector3(1.2f, 0.1f, 1.2f));
        var plateComp = plate.AddComponent<PressurePlate>();
        plateComp.door = door.GetComponent<StoneDoor>();

        var block = Box("PushBlock", LevelSpec.BlockPos, Vector3.one);
        block.tag = LevelSpec.TagPushable;
        var rb = block.AddComponent<Rigidbody>();
        rb.mass = 50f;
        rb.constraints = RigidbodyConstraints.FreezeRotation | RigidbodyConstraints.FreezePositionY;
        block.AddComponent<PushBlock>();

        // 祭坛 + 宝物 + 终点触发
        Box("Altar", LevelSpec.AltarPos, new Vector3(2, 1, 1));
        var treasure = Box("Treasure", LevelSpec.TreasurePos, Vector3.one * 0.4f);
        var sc = treasure.AddComponent<SphereCollider>(); sc.isTrigger = true; sc.radius = 3.75f; // 世界半径≈1.5（父缩放 0.4）
        treasure.AddComponent<GoalTrigger>();

        // 玩家（胶囊视觉 + CharacterController + 控制器/攀爬/推挤 + 相机）
        var player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "Player"; player.tag = "Player";
        player.transform.position = LevelSpec.PlayerSpawn;
        Object.DestroyImmediate(player.GetComponent<CapsuleCollider>());
        var cc = player.AddComponent<CharacterController>();
        cc.height = 1.8f; cc.radius = 0.3f; cc.center = new Vector3(0, 0.9f, 0);
        player.AddComponent<ThirdPersonController>();
        var climb = player.AddComponent<ClimbSystem>();
        climb.climbableMask = 1 << LayerMask.NameToLayer(LevelSpec.LayerClimbable);

        var camGo = new GameObject("MainCamera");
        var cam = camGo.AddComponent<Camera>(); camGo.tag = "MainCamera";
        var follow = camGo.AddComponent<CameraFollow>();
        follow.target = player.transform;
        player.GetComponent<ThirdPersonController>().cameraPivot = camGo.transform;

        new GameObject("UI").AddComponent<SimpleUI>();

        // 光照占位（暗环境 + 暖色点光）
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.08f, 0.08f, 0.12f);
        var sun = new GameObject("Sun").AddComponent<Light>();
        sun.type = LightType.Directional; sun.intensity = 0.3f; sun.transform.rotation = Quaternion.Euler(60, -30, 0);
        MakePointLight("TorchA_L", new Vector3(-3, 2.5f, -6), new Color(1f, 0.6f, 0.3f), 6f);
        MakePointLight("TorchA_R", new Vector3(3, 2.5f, -6), new Color(1f, 0.6f, 0.3f), 6f);

        System.IO.Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene, "Assets/Scenes/Demo.unity");
        Debug.Log("[GrayboxBuilder] Demo.unity 构建完成");
    }

    static float WallH2() => LevelSpec.WallH / 2f;
    static float L2() => LevelSpec.WallH;

    static GameObject Box(string name, Vector3 center, Vector3 size)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name; go.transform.position = center; go.transform.localScale = size;
        return go;
    }

    static void MakePointLight(string name, Vector3 pos, Color c, float range)
    {
        var go = new GameObject(name);
        var lt = go.AddComponent<Light>();
        lt.type = LightType.Point; lt.color = c; lt.range = range; lt.intensity = 1.5f;
        go.transform.position = pos;
    }

    static void EnsureLayer(string name)
    {
        if (LayerMask.NameToLayer(name) != -1) return;
        var so = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        var layers = so.FindProperty("layers");
        for (int i = 8; i < layers.arraySize; i++)
            if (string.IsNullOrEmpty(layers.GetArrayElementAtIndex(i).stringValue))
            { layers.GetArrayElementAtIndex(i).stringValue = name; so.ApplyModifiedProperties(); return; }
    }

    static void EnsureTag(string name)
    {
        var so = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        var tags = so.FindProperty("tags");
        for (int i = 0; i < tags.arraySize; i++) if (tags.GetArrayElementAtIndex(i).stringValue == name) return;
        tags.InsertArrayElementAtIndex(tags.arraySize);
        tags.GetArrayElementAtIndex(tags.arraySize - 1).stringValue = name;
        so.ApplyModifiedProperties();
    }
}
