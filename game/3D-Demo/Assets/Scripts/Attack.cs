using UnityEngine;
// M6-3: 左键挥刀——触发 Slash 动画 + 判定窗扇形检测（命中 ICuttable）；
// Start 时把 SM_Knife 实例挂到 RightHand 骨骼（随动画摆动）。
public class Attack : MonoBehaviour
{
    public GameObject knifePrefab;                 // SM_Knife.fbx（Assets/Art/Static/hero_props）
    public float hitDelay = 0.4f;                  // 判定窗时刻＝A_Slash f10-f14 中点 f12（12/30≈0.4s；
                                                   // 进状态转场 0.1s 内 clip 同步推进，不叠加）
    public float range = 1.2f, radius = 0.85f, cooldown = 0.7f;
    public Vector3 knifeEuler = new Vector3(0f, 180f, 0f);   // 握持校准：绕刀轴转 180° 使刃口朝挥砍行进方向（Play 实测）
    float next; Animator anim; Transform knife;

    void Start()
    {
        anim = GetComponentInChildren<Animator>();
        var hand = anim ? anim.GetBoneTransform(HumanBodyBones.RightHand) : null;
        if (hand && knifePrefab)
        {
            knife = Instantiate(knifePrefab, hand).transform;
            knife.localPosition = Vector3.zero;
            knife.localRotation = Quaternion.Euler(knifeEuler);
            knife.localScale = Vector3.one * (1f / 1.7f);   // 抵消 Hero 根 1.7× 缩放：刀保持 0.42m 实际尺寸
        }
    }

    void Update()
    {
        if (Time.time < next || Time.timeScale == 0f) return;   // 覆盖暂停菜单期间（timeScale=0）不响应攻击
        if (!Input.GetMouseButtonDown(0)) return;
        next = Time.time + cooldown;
        if (anim) anim.SetTrigger("slash");
        Invoke(nameof(Hit), hitDelay);
    }

    void Hit()
    {
        Vector3 c = transform.position + Vector3.up * 0.9f + transform.forward * (range * 0.6f);
        foreach (var h in Physics.OverlapSphere(c, radius, ~0, QueryTriggerInteraction.Ignore))
        {
            var cut = h.GetComponentInParent<ICuttable>();
            if (cut != null) { cut.Cut(transform.forward); break; }
        }
    }
}
