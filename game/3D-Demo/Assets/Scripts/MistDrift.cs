using UnityEngine;

// M6-5: 深渊雾层漂移——慢速上下浮动 + alpha 呼吸（相位随实例错开）。
// 仿 FireFlicker 的极简结构：共享材质取底色，运行时用 MaterialPropertyBlock 覆写 alpha
// （不改共享材质资产；雾板会动 → 构建器不标静态、关阴影）。
public class MistDrift : MonoBehaviour
{
    public float bobAmp = 0.4f, bobSpeed = 0.15f, alphaBase = 0.5f, alphaAmp = 0.12f;
    Vector3 basePos; Color baseCol; float phase;
    Renderer r; MaterialPropertyBlock mpb;

    void Start()
    {
        basePos = transform.position;
        phase = Random.value * 6.28f;
        r = GetComponent<Renderer>();
        mpb = new MaterialPropertyBlock();
        baseCol = r.sharedMaterial.GetColor("_BaseColor");      // 共享材质取底色
    }

    void Update()
    {
        transform.position = basePos + Vector3.up * (Mathf.Sin(Time.time * bobSpeed + phase) * bobAmp);
        var c = baseCol;
        c.a = Mathf.Clamp01(alphaBase + Mathf.Sin(Time.time * bobSpeed * 0.7f + phase) * alphaAmp);
        r.GetPropertyBlock(mpb);
        mpb.SetColor("_BaseColor", c);
        r.SetPropertyBlock(mpb);
    }
}
