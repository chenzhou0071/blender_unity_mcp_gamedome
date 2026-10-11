using UnityEngine;

// M5-3: 火盆点光闪烁——Perlin 噪声微调强度，让火光"活"起来（挂载由 Editor/PostFxSetup 批量完成）
[RequireComponent(typeof(Light))]
public class FireFlicker : MonoBehaviour
{
    public float baseIntensity = 2.2f, amp = 0.5f, speed = 8f;
    Light lt; float seed;

    void Awake() { lt = GetComponent<Light>(); seed = Random.value * 100f; }

    void Update()
    {
        lt.intensity = baseIntensity + (Mathf.PerlinNoise(seed, Time.time * speed) - 0.5f) * 2f * amp;
    }
}
