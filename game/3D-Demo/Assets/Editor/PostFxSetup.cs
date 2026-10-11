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
        {
            bloom = profile.Add<Bloom>(true);
            AssetDatabase.AddObjectToAsset(bloom, profile);   // 关键：组件必须挂进资产，否则重启 Unity 后丢失（M5-3 的 bug）
        }
        bloom.intensity.Override(1.0f);   // M5-3.2: 火焰光团 ×4.5 下 1.0 实测定档（1.6 会全屏橙雾）
        bloom.threshold.Override(0.7f);   // 实测定档：捕捉火焰亮部，其余暗调不受影响

        // 色调映射：HDR 火焰过曝滚成奶油橙白（没有它高光会死白难看）
        if (!profile.TryGet<Tonemapping>(out var tmap))
        {
            tmap = profile.Add<Tonemapping>(true);
            AssetDatabase.AddObjectToAsset(tmap, profile);
        }
        tmap.mode.Override(TonemappingMode.ACES);

        // 3) 相机后处理开关（URP 相机默认关闭）
        var cam = Camera.main;
        if (cam != null)
        {
            var data = cam.GetComponent<UniversalAdditionalCameraData>();
            if (data == null) data = cam.gameObject.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
        }
        else Debug.LogWarning("[PostFxSetup] Camera.main 未找到，后处理开关未设置");

        // 4) 火焰光团：盆口上方 HDR 自发光椭球——过曝成亮团、不投影；盆体轮廓在光晕下隐约可见
        // 注：用 Unlit + HDR 底色直出（Lit 的 _EMISSION keyword 在 Unity 6 资产导入时会丢，弃用）
        const string flameMatPath = "Assets/Settings/M_Flame.mat";
        var flameMat = AssetDatabase.LoadAssetAtPath<Material>(flameMatPath);
        if (flameMat == null)
        {
            flameMat = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
            AssetDatabase.CreateAsset(flameMat, flameMatPath);
        }
        flameMat.shader = Shader.Find("Universal Render Pipeline/Unlit");   // 兼容旧 Lit 资产迁移
        flameMat.SetColor("_BaseColor", new Color(4.5f, 1.9f, 0.35f, 0.5f));  // HDR ×4.5 半透明橙（alpha 0.5；实测定档）
        // 半透明直出：Unlit 透明混合（Blend 由属性直控，无 keyword 依赖）；关 ZWrite、进透明队列
        flameMat.SetFloat("_Surface", 1f);
        flameMat.SetFloat("_Blend", 0f);
        flameMat.SetFloat("_SrcBlend", 5f);    // SrcAlpha
        flameMat.SetFloat("_DstBlend", 10f);   // OneMinusSrcAlpha
        flameMat.SetFloat("_ZWrite", 0f);
        flameMat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        flameMat.renderQueue = 3000;
        // 径向渐变遮罩：中心实、向外渐透——火焰边缘半透明（生成一次后复用）
        const string flameTexPath = "Assets/Settings/T_FlameFalloff.png";
        var flameTex = AssetDatabase.LoadAssetAtPath<Texture2D>(flameTexPath);
        if (flameTex == null)
        {
            int size = 128;
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false);
            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    float dx = (x + 0.5f - size / 2f) / (size / 2f);
                    float dy = (y + 0.5f - size / 2f) / (size / 2f);
                    float a = Mathf.Clamp01(1f - Mathf.Sqrt(dx * dx + dy * dy));
                    tex.SetPixel(x, y, new Color(1f, 1f, 1f, a * a));
                }
            }
            tex.Apply();
            System.IO.File.WriteAllBytes(Application.dataPath + "/Settings/T_FlameFalloff.png", tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(flameTexPath, ImportAssetOptions.ForceUpdate);
            var imp = (TextureImporter)AssetImporter.GetAtPath(flameTexPath);
            imp.alphaIsTransparency = true;
            imp.wrapMode = TextureWrapMode.Clamp;
            imp.SaveAndReimport();
            flameTex = AssetDatabase.LoadAssetAtPath<Texture2D>(flameTexPath);
        }
        flameMat.SetTexture("_BaseMap", flameTex);
        EditorUtility.SetDirty(flameMat);
        AssetDatabase.SaveAssetIfDirty(flameMat);

        int flames = 0;
        foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(FindObjectsSortMode.None))
        {
            if (!l.name.StartsWith("Torch") || l.type != LightType.Point) continue;
            var flame = l.transform.Find("Flame_" + l.name);
            if (flame == null)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
                go.name = "Flame_" + l.name;
                go.transform.SetParent(l.transform, false);
                flame = go.transform;
            }
            flame.localPosition = new Vector3(0f, -0.08f, 0f);   // 光团微沉入碗口（实测定档·三轮）
            flame.localScale = new Vector3(0.2f, 0.3f, 0.2f);    // 细长椭圆火苗（三轮定档：两轮收敛后的小尺寸）
            var fr = flame.GetComponent<MeshRenderer>();
            fr.sharedMaterial = flameMat;
            fr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            fr.receiveShadows = false;
            flames++;
        }
        Debug.Log("[PostFxSetup] 火焰光团: " + flames + " 个（HDR ×10 自发光）");

        EditorUtility.SetDirty(volGo);
        EditorUtility.SetDirty(vol);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
            UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();
        AssetDatabase.SaveAssets();
        Debug.Log("[PostFxSetup] Global Volume + Bloom(1.6/0.7) + ACES + 火焰光团 配置完成");
    }
}
