using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// M5-2: 一键接线音效——场景建/找 AudioManager 对象，按文件名把 wav 赋到字段并保存场景（幂等）
public static class AudioWiring
{
    [MenuItem("Demo/接线音效")]
    public static void Wire()
    {
        var go = GameObject.Find("AudioManager");
        if (go == null)
        {
            go = new GameObject("AudioManager");
            Undo.RegisterCreatedObjectUndo(go, "Create AudioManager");
        }
        var am = go.GetComponent<AudioManager>();
        if (am == null) am = go.AddComponent<AudioManager>();

        am.ambient = Load("ambient_temple.wav");
        am.footsteps = new[]
        {
            Load("footstep_stone_1.wav"), Load("footstep_stone_2.wav"),
            Load("footstep_stone_3.wav"), Load("footstep_stone_4.wav")
        };
        am.land = Load("land.wav");
        am.blockGrind = Load("block_grind.wav");
        am.plateClick = Load("plate_click.wav");
        am.doorRumble = Load("door_rumble.wav");
        am.goalChime = Load("goal_chime.wav");

        // 火盆噼啪：3D 空间源——线性衰减（二轮试听：只有贴近才听清）
        var fireClip = Load("fire_crackle.wav");
        if (!fireClip) Debug.LogWarning("[AudioWiring] fire_crackle.wav 未找到");
        int fireCount = 0;
        foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(FindObjectsSortMode.None))
        {
            if (!l.name.StartsWith("Torch")) continue;
            var src = l.gameObject.GetComponent<AudioSource>();
            if (src == null) src = l.gameObject.AddComponent<AudioSource>();
            src.clip = fireClip;
            src.loop = true;
            src.volume = 0.6f;                                   // 近场响度
            src.spatialBlend = 1f;                               // 纯 3D
            src.rolloffMode = AudioRolloffMode.Linear;
            src.minDistance = 1.2f;                              // 1.2m 内全响
            src.maxDistance = 5.0f;                              // 5.0m 外静音（三轮试听）
            src.playOnAwake = true;
            fireCount++;
        }
        Debug.Log("[AudioWiring] 火盆空间音源: " + fireCount + " 个（近响远弱）");

        // 确保场景有 AudioListener（M2 建场景时 MainCamera 遗漏——此前无音效未暴露）
        if (UnityEngine.Object.FindObjectsByType<AudioListener>(FindObjectsSortMode.None).Length == 0)
        {
            var cam = Camera.main;
            if (cam)
            {
                cam.gameObject.AddComponent<AudioListener>();
                Debug.Log("[AudioWiring] 已给 MainCamera 补 AudioListener");
            }
            else Debug.LogWarning("[AudioWiring] 场景无主相机，AudioListener 未添加");
        }

        EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
        EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
        Debug.Log("[AudioWiring] 音效已接线（AudioManager 对象），场景已保存");
    }

    static AudioClip Load(string file) =>
        AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/Audio/" + file);
}
