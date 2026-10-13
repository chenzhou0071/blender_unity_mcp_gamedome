using UnityEngine;

// M6-1 Task4: 室内外光照过渡——玩家进入 Zone 后把太阳/雾混到目标值（SmoothStep，1.5s）。
// 两个实例由「Demo/户外氛围」菜单创建：
//   OUT_Zone_Indoor（楼梯中上段 z10-15）：从户外回室内时过渡回"室内基调"（0.3 暖橙太阳 + 浓雾 0→60）
//   OUT_Zone_Outdoor（楼梯下段几阶起 z16-40）：出门时过渡到"白天基调"（1.6 白暖太阳 + 远雾 60→240）
// 目标存静态字段：两 Zone 共用，后触发者覆盖（快速往返时从当前值继续插值，平滑）。
public class LightZone : MonoBehaviour
{
    public Light sun;
    public float sunIntensity = 1.5f;
    public Color sunColor = new Color(1f, 0.96f, 0.88f);    // ≈5800K 白暖（户外基调）
    public float fogStart = 60f, fogEnd = 240f;
    public Color fogColor = new Color(0.66f, 0.74f, 0.80f); // 增补：雾色随 Zone 过渡（防室内暗雾↔户外蓝雾突变）
    public float blendSeconds = 1.5f;

    // 静态：两 Zone 共用同一目标（后触发者覆盖）——初值=室内基调（场景初始状态）
    static float targetIntensity = 0.3f, targetFogStart = 0f, targetFogEnd = 60f;
    static Color targetSunColor = new Color(1f, 0.78f, 0.55f);
    static Color targetFogColor = new Color(0.33f, 0.32f, 0.35f);
    float t = 1f;

    void OnTriggerEnter(Collider other)
    {
        if (!other.CompareTag("Player")) return;
        targetIntensity = sunIntensity;
        targetSunColor = sunColor;
        targetFogStart = fogStart;
        targetFogEnd = fogEnd;
        targetFogColor = fogColor;
        t = 0f;
    }

    void Update()
    {
        if (t >= 1f || !sun) return;
        t += Time.deltaTime / blendSeconds;
        float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(t, 1f));
        sun.intensity = Mathf.Lerp(sun.intensity, targetIntensity, k);
        sun.color = Color.Lerp(sun.color, targetSunColor, k);
        RenderSettings.fogStartDistance = Mathf.Lerp(RenderSettings.fogStartDistance, targetFogStart, k);
        RenderSettings.fogEndDistance = Mathf.Lerp(RenderSettings.fogEndDistance, targetFogEnd, k);
        RenderSettings.fogColor = Color.Lerp(RenderSettings.fogColor, targetFogColor, k);
    }
}
