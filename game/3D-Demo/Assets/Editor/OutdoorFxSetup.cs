using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;

// M6-1 Task4: 户外氛围一键配置（幂等）——白天基调（2026-10-12 设计变更）：
//   · 天空：M_DaySky（Skybox/Procedural 白天蓝天，替代黎明版 M_MorningSky）
//   · 太阳：Euler (67.5°,57°,61.5°)（2026-10-13 用户定稿光位）；强度/色保存为室内基调（运行时由 LightZone 过渡到户外 1.6 白暖）
//   · 雾：Linear 室内浓雾 0→60 暗紫灰（运行时过渡到户外 60→240 天光蓝灰）
//   · Volume：追加 ColorAdjustments（饱和度 +8 / 曝光 +0.2）
//   · 过渡 Zone：OUT_Zone_Indoor z10-15 / OUT_Zone_Outdoor z16-40（触发器 + LightZone，1.5s）
// 菜单: Demo/户外氛围 —— 注意链路：「构建户外场景」会清 OUT_* 前缀、「重建神庙」会清 Torch_*，重跑后需重跑本菜单。
public static class OutdoorFxSetup
{
    // 室内基调
    static readonly Color IndoorSunColor  = new Color(1f, 0.78f, 0.55f);
    static readonly Color IndoorFogColor  = new Color(0.33f, 0.32f, 0.35f);
    // 户外基调（白天）
    static readonly Color OutdoorSunColor = new Color(1f, 0.96f, 0.88f);    // ≈5800K 白暖
    static readonly Color OutdoorFogColor = new Color(0.66f, 0.74f, 0.80f); // 天光蓝灰

    [MenuItem("Demo/户外氛围")]
    public static void Setup()
    {
        if (EditorApplication.isPlaying)
        {
            Debug.LogWarning("[OutdoorFxSetup] 请先退出 Play 模式再执行（Play 中改动退出后会还原）");
            return;
        }

        // 1) 太阳：Euler (67.5°,57°,61.5°)（2026-10-13 用户定稿；注：Unity 平行光 Euler.X 即太阳仰角）；
        //    强度/色=室内基调（运行时 Zone 过渡到户外）
        var sunGo = GameObject.Find("Sun");
        Light sunLight = null;
        if (sunGo != null)
        {
            sunGo.transform.rotation = Quaternion.Euler(67.5f, 57f, 61.5f);
            sunLight = sunGo.GetComponent<Light>();
            sunLight.intensity = 0.3f;
            sunLight.color = IndoorSunColor;
            Debug.Log("[OutdoorFxSetup] Sun：角度(67.5,57,61.5) 强度 0.3 暖橙（室内基调）");
        }
        else Debug.LogWarning("[OutdoorFxSetup] Sun 未找到");

        // 2) 天空盒：M_DaySky（Skybox/Procedural；幂等创建/更新）
        //    说明：计划原定 Volume 天空组件（PhysicallyBasedSky/GradientSky），实测 Unity 6.3 URP 无此类，
        //    改用内置程序化天空盒：太阳盘方向自动跟随最亮平行光（即 Sun 的角度）
        const string skyPath = "Assets/Settings/M_DaySky.mat";
        var sky = AssetDatabase.LoadAssetAtPath<Material>(skyPath);
        if (sky == null)
        {
            sky = new Material(Shader.Find("Skybox/Procedural"));
            AssetDatabase.CreateAsset(sky, skyPath);
        }
        sky.SetFloat("_SunDisk", 2f);                 // 高品质太阳盘
        sky.SetFloat("_SunSize", 0.04f);              // 标准小太阳（黎明版是 2.0 大阳盘）
        sky.SetFloat("_SunSizeConvergence", 2f);
        sky.SetFloat("_AtmosphereThickness", 0.65f);  // 清透晴天
        sky.SetColor("_SkyTint", new Color(0.42f, 0.50f, 0.62f, 1f));    // 天顶蓝
        sky.SetColor("_GroundColor", new Color(0.52f, 0.51f, 0.50f, 1f)); // 天际线下中性亮灰
        sky.SetFloat("_Exposure", 1.1f);
        EditorUtility.SetDirty(sky);
        AssetDatabase.SaveAssetIfDirty(sky);
        RenderSettings.skybox = sky;
        Debug.Log("[OutdoorFxSetup] 天空盒：M_DaySky（白天蓝天）");

        // 3) 雾：Linear 室内浓雾（运行时 Zone 过渡）
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogStartDistance = 0f;
        RenderSettings.fogEndDistance = 60f;
        RenderSettings.fogColor = IndoorFogColor;

        // 4) Volume：追加 ColorAdjustments（饱和度 +8 / 曝光 +0.2）
        var volGo = GameObject.Find("Global Volume");
        if (volGo == null) volGo = new GameObject("Global Volume");
        var vol = volGo.GetComponent<Volume>();
        if (vol == null) vol = volGo.AddComponent<Volume>();
        vol.isGlobal = true;
        const string profilePath = "Assets/Settings/M5_Atmosphere_Volume.asset";
        var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(profilePath);
        if (profile != null)
        {
            if (!profile.TryGet<ColorAdjustments>(out var ca))
            {
                ca = profile.Add<ColorAdjustments>(true);
                AssetDatabase.AddObjectToAsset(ca, profile);   // 关键：必须挂进资产，否则重启 Unity 后丢失（M5-3 的坑）
            }
            ca.saturation.Override(8f);
            ca.postExposure.Override(0.2f);
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssetIfDirty(profile);
            Debug.Log("[OutdoorFxSetup] ColorAdjustments：饱和度 +8 / 曝光 +0.2");
        }
        else Debug.LogWarning("[OutdoorFxSetup] VolumeProfile 未找到: " + profilePath);

        // 5) 室内外过渡 Zone（BoxCollider isTrigger + LightZone；纯触发器无渲染网格）
        //    切点（迭代：用户反馈"楼梯后几阶就该切换，那时已能看清外面"）：
        //    Indoor z10-15（楼梯中上段，回程触发回室内）/ Outdoor z16-40（楼梯下段几阶起，出门过渡）；
        //    两 Zone 不重叠——重叠区内玩家不会再次收到 Enter，会导致回程漏切换
        MakeZone("OUT_Zone_Indoor", new Vector3(0f, 4f, 12.5f), new Vector3(8f, 12f, 5f), sunLight,
                 0.3f, IndoorSunColor, 0f, 60f, IndoorFogColor);
        MakeZone("OUT_Zone_Outdoor", new Vector3(0f, 4f, 28f), new Vector3(30f, 12f, 24f), sunLight,
                 1.6f, OutdoorSunColor, 60f, 240f, OutdoorFogColor);
        Debug.Log("[OutdoorFxSetup] 过渡 Zone：Indoor(z10-15) / Outdoor(z16-40) 已配置");

        // 保存
        EditorUtility.SetDirty(volGo);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
            UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();
        AssetDatabase.SaveAssets();
        Debug.Log("[OutdoorFxSetup] 户外氛围配置完成（天空/太阳/雾/曝光 + 2 个过渡 Zone）");
    }

    static void MakeZone(string name, Vector3 center, Vector3 size, Light sun,
                         float intensity, Color sunCol, float fogS, float fogE, Color fogCol)
    {
        var go = GameObject.Find(name);
        if (go == null) go = new GameObject(name);
        go.transform.position = center;
        var bc = go.GetComponent<BoxCollider>();
        if (bc == null) bc = go.AddComponent<BoxCollider>();
        bc.isTrigger = true;
        bc.size = size;
        var lz = go.GetComponent<LightZone>();
        if (lz == null) lz = go.AddComponent<LightZone>();
        lz.sun = sun;
        lz.sunIntensity = intensity;
        lz.sunColor = sunCol;
        lz.fogStart = fogS;
        lz.fogEnd = fogE;
        lz.fogColor = fogCol;
        lz.blendSeconds = 1.5f;
    }
}
