using UnityEngine;

// 低空雾团漂移：绕初始锚点缓慢环绕 + 上下起伏 + 透明度呼吸（MaterialPropertyBlock，不破坏共享材质）。
// 由 KitPlacer 生成雾片时挂载并 Init；编辑器场景中静止于基准位置，Play 后开始流动。
public class FogDrift : MonoBehaviour
{
    Vector3 anchor;
    float radius, speed, phase, breath;
    Renderer rend;
    MaterialPropertyBlock mpb;
    Color baseColor;

    public void Init(float radius, float speed, float phase, float breath)
    {
        this.radius = radius; this.speed = speed; this.phase = phase; this.breath = breath;
    }

    void Start()
    {
        anchor = transform.position;
        rend = GetComponent<Renderer>();
        mpb = new MaterialPropertyBlock();
        var mat = rend ? rend.sharedMaterial : null;
        baseColor = (mat != null && mat.HasProperty("_BaseColor"))
            ? mat.GetColor("_BaseColor") : new Color(1f, 1f, 1f, 0.22f);
    }

    void Update()
    {
        float t = Time.time * speed + phase;
        transform.position = anchor + new Vector3(
            Mathf.Sin(t) * radius,
            Mathf.Sin(t * 0.7f + 1.3f) * 0.15f,
            Mathf.Cos(t * 0.8f + 0.6f) * radius);
        if (rend)
        {
            rend.GetPropertyBlock(mpb);
            var c = baseColor;
            c.a = Mathf.Clamp01(baseColor.a + Mathf.Sin(t * 1.7f + 2.1f) * breath);
            mpb.SetColor("_BaseColor", c);
            rend.SetPropertyBlock(mpb);
        }
    }
}
