using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;

// M5-3: 氛围一键配置——批量给火盆点光挂 FireFlicker、创建 Global Volume + Bloom、打开相机后处理
// 菜单: Tools/M5/Setup Atmosphere（幂等，可重复执行）
public static class PostFxSetup
{
    [MenuItem("Tools/M5/Setup Atmosphere")]
    public static void Setup()
    {
        // 1) 火盆闪烁：命名 Torch* 的点光（与 AudioWiring 的火盆识别口径一致）
        int torches = 0;
        foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(FindObjectsSortMode.None))
        {
            if (!l.name.StartsWith("Torch") || l.type != LightType.Point) continue;
            var ff = l.gameObject.GetComponent<FireFlicker>();
            if (ff == null) ff = l.gameObject.AddComponent<FireFlicker>();
            ff.baseIntensity = l.intensity;              // 以当前亮度为基准（Edit 模式下为场景原值）
            torches++;
        }
        Debug.Log("[PostFxSetup] FireFlicker: " + torches + " 个火盆");

        // 2) Global Volume + Bloom（profile 资产化；可重复执行时复用旧资产）
        var volGo = GameObject.Find("Global Volume");
        if (volGo == null) volGo = new GameObject("Global Volume");
        var vol = volGo.GetComponent<Volume>();
        if (vol == null) vol = volGo.AddComponent<Volume>();
        vol.isGlobal = true;
        const string profilePath = "Assets/Settings/M5_Atmosphere_Volume.asset";
        var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(profilePath);
        if (profile == null)
        {
            profile = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(profile, profilePath);
        }
        vol.sharedProfile = profile;

        if (!profile.TryGet<Bloom>(out var bloom))
            bloom = profile.Add<Bloom>(true);
        bloom.intensity.Override(0.8f);
        bloom.threshold.Override(0.7f);   // 实测定档：火焰几何体亮度在 LDR 下 <1，阈值 1.0 不泛光；0.7 只捕捉火焰亮部，安全

        // 3) 相机后处理开关（URP 相机默认关闭）
        var cam = Camera.main;
        if (cam != null)
        {
            var data = cam.GetComponent<UniversalAdditionalCameraData>();
            if (data == null) data = cam.gameObject.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
        }
        else Debug.LogWarning("[PostFxSetup] Camera.main 未找到，后处理开关未设置");

        EditorUtility.SetDirty(volGo);
        EditorUtility.SetDirty(vol);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
            UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();
        AssetDatabase.SaveAssets();
        Debug.Log("[PostFxSetup] Global Volume + Bloom(0.8/0.7) 与相机后处理配置完成");
    }
}
