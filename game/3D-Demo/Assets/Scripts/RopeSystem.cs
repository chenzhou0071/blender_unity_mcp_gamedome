using UnityEngine;

// M6-5 Task 16: 爬绳（斜绳横跨深渊版·趴绳蠕动）——靠近绳南端+按 W+面向绳 → 抓绳上绳。
// 姿态：身体趴在绳面上沿轴蠕动（模型前倾贴合绳轴，A_Climb 手脚交替映射为爬行），W/S 沿轴爬行；
// 到北端自动起身顶翻越上崖顶；空格=松手坠落；S 回到南端落地。
// 结构仿 ClimbSystem；挂在绳对象上（对象原点=绳南底端；本组件不在玩家上，运行时查 Player）。
public class RopeSystem : MonoBehaviour
{
    public float ropeLength = 22.7f;                       // 南端原点沿 +up（斜向）全长
    public float grabRadius = 0.85f, climbSpeed = 1.5f, topOutSpeed = 2.0f;
    public float bodyCenterBack = 0.75f, bodyDrop = 0.82f; // 贴绳偏移解算：模型根(胯)在原点上方 0.81；令胯沿绳垂直方位高于绳轴 0.15、轴向对齐 → 原点=绳点南 0.75/下 0.82
    public float bodyPitch = 79f;                          // 模型前倾（90-绳倾角 11.2≈79：身体轴对齐绳轴趴下）
    public float wobble = 0.03f;                           // 蠕动起伏（3cm 正弦，脚爬节奏感）
    public bool IsRoping { get; private set; }
    public static RopeSystem Active;                       // TPC 分支用（组件在绳上而非玩家）

    CharacterController cc;
    Transform playerT, body;                               // body=模型根（Animator 所在子物体：只转它趴下，不动 CC 胶囊）
    Quaternion bodyBase;                                   // 模型原始局部朝向（恢复直立用）
    float ropeT;                                           // 攀爬进度（沿轴米数）
    bool topping; float topT; Vector3 topFrom, topTo;

    Vector3 Axis => transform.up;                          // 斜绳轴（南→北向上）

    void Update()
    {
        if (!playerT)
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            if (!p) return;
            playerT = p.transform; cc = p.GetComponent<CharacterController>();
            var an = p.GetComponentInChildren<Animator>();
            if (an) { body = an.transform; bodyBase = body.localRotation; }
        }
        if (IsRoping) { TickRope(); return; }

        // 抓绳条件：离绳轴最近点 < grabRadius；处于绳底段（t<3，只能从南端上绳）；按 W；面向绳
        Vector3 rel = playerT.position - transform.position;
        float t = Mathf.Clamp(Vector3.Dot(rel, Axis), 0f, ropeLength);
        Vector3 near = transform.position + Axis * t;
        if ((playerT.position - near).magnitude > grabRadius || t > 3f) return;
        if (Input.GetAxisRaw("Vertical") <= 0.1f) return;
        Vector3 face = near - playerT.position; face.y = 0f;
        if (face.sqrMagnitude < 0.001f) return;
        face.Normalize();
        if (Vector3.Dot(playerT.forward, face) < 0.4f) return;
        IsRoping = true; Active = this; ropeT = t;
        SnapToRope();
    }

    // 趴在绳上：原点 = 轴点沿轴后（南）0.9m/下 0.06m（躯干中心贴绳轴）；模型渐前倾趴下；微蠕动起伏
    void SnapToRope()
    {
        Vector3 flat = Axis; flat.y = 0f; flat.Normalize();       // 水平北向（轴水平化）
        Vector3 target = RopePoint(ropeT) - flat * bodyCenterBack - Vector3.up * bodyDrop;
        target.y += Mathf.Sin(Time.time * 4.5f) * wobble;
        cc.Move(target - playerT.position);
        playerT.rotation = Quaternion.LookRotation(flat, Vector3.up);
        if (body)
            body.localRotation = Quaternion.Slerp(body.localRotation,
                Quaternion.Euler(bodyPitch, 0f, 0f), 12f * Time.deltaTime);
    }

    void StandUp() { if (body) body.localRotation = bodyBase; }   // 松手/落地：模型立即恢复直立

    Vector3 RopePoint(float t) => transform.position + Axis * t;

    void TickRope()
    {
        if (topping)
        {
            topT += Time.deltaTime * topOutSpeed;
            float k = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(topT));
            cc.Move(Vector3.Lerp(topFrom, topTo, k) - playerT.position);
            if (body)   // 翻越段：身体从趴姿滑动回直立（与位移同相：撑台起身）
                body.localRotation = Quaternion.Slerp(Quaternion.Euler(bodyPitch, 0f, 0f), bodyBase, k);
            if (topT >= 1f) { topping = false; IsRoping = false; Active = null; StandUp(); }
            return;
        }

        if (Input.GetButtonDown("Jump")) { IsRoping = false; Active = null; StandUp(); return; }   // 空格松手坠落
        float v = Input.GetAxisRaw("Vertical");

        // 北端到顶：进度达全长 → 翻越上崖顶（崖顶地面 y=3，落点 z≈216.3）
        if (v > 0.1f && ropeT >= ropeLength - 0.4f)
        {
            topping = true; topT = 0f;
            topFrom = playerT.position;
            topTo = new Vector3(transform.position.x, 3.05f, 216.3f);
            return;
        }
        // 南端到底：S 持续 → 落地松手（站回南岸崖边）
        if (v < -0.1f && ropeT <= 0.15f) { IsRoping = false; Active = null; StandUp(); return; }

        ropeT = Mathf.Clamp(ropeT + v * climbSpeed * Time.deltaTime, 0f, ropeLength);
        SnapToRope();
    }
}
