using UnityEngine;
using UnityEditor;

// M4-4: 主角 FBX 导入配置 —— Humanoid rig（材质走 Unity 默认导入以保留内嵌贴图）
// M4-5: 动画裁剪 —— Idle/Walk/Run/Climb 循环，Jump 单次
public class HeroImporter : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        if (!assetPath.Contains("SK_Explorer")) return;
        var imp = (ModelImporter)assetImporter;
        imp.animationType = ModelImporterAnimationType.Human; // Unity 6.3 成员名为 Human（旧版为 Humanoid）
    }

    void OnPreprocessAnimation()
    {
        if (!assetPath.Contains("SK_Explorer")) return;
        var imp = (ModelImporter)assetImporter;
        var clips = imp.defaultClipAnimations;
        foreach (var c in clips)
        {
            c.loopTime = !c.name.Contains("Jump");       // Idle/Walk/Run/Climb 循环，Jump 单次
            Debug.Log($"[HeroImporter] clip {c.name} loop={c.loopTime}");
        }
        imp.clipAnimations = clips;
    }
}

// 菜单工具：打印主角 FBX 内的全部动画片段（M4-5 控制器按此 clip 名加载）
public static class HeroClipPrinter
{
    [MenuItem("Demo/打印主角动画片段")]
    public static void PrintClips()
    {
        const string path = "Assets/Art/Characters/SK_Explorer.fbx";
        var all = AssetDatabase.LoadAllAssetsAtPath(path);
        int n = 0;
        foreach (var o in all)
        {
            if (o is AnimationClip c && !c.name.StartsWith("__preview"))
            {
                Debug.Log($"[HeroClip] {c.name}  length={c.length:F3}s  fps={c.frameRate}");
                n++;
            }
        }
        Debug.Log($"[HeroClip] total {n} clips; loaded objects={all.Length}");
    }
}
