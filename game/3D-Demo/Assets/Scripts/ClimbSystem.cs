using UnityEngine;

public class ClimbSystem : MonoBehaviour
{
    public LayerMask climbableMask;
    public float checkDist = 0.65f, climbSpeed = 1.5f, topOutDuration = 1.0f;   // M4-10: 0.85→1.0 对齐重做的 A_Mantle（30f/1.0s 弯腰撑台提膝版）

    public bool IsClimbing { get; private set; }
    public bool IsToppingOut => toppingOut;   // M4-8: Animator 接线（Climb→Mantle 切换条件）

    CharacterController cc;
    bool toppingOut; float topOutT;
    bool slipping; float slipV;               // 空中抓墙的滑坠相位（抓住瞬间先下滑再上爬）
    Vector3 topStart, topEnd;

    void Awake() { cc = GetComponent<CharacterController>(); }

    void Update()
    {
        if (IsClimbing) { TickClimb(); return; }
        // 空中也可接攀爬：跳跃扑墙/贴墙下落时按住前进键直接抓住上壁。
        // （原先要求 cc.isGrounded——跳向高台在壁上悬挂时无法直接开始爬，
        //   必须落地站稳后才行；验收反馈要求衔接跳跃）
        float v = Input.GetAxisRaw("Vertical"), h = Input.GetAxisRaw("Horizontal");
        if (v <= 0.1f || Mathf.Abs(h) > 0.5f) return;                    // 须朝向墙前进
        Vector3 origin = transform.position + Vector3.up * 1.1f;
        if (Physics.Raycast(origin, transform.forward, out var hit, checkDist, climbableMask))
            BeginClimb(hit.normal, hit.point);
    }

    void BeginClimb(Vector3 wallNormal, Vector3 wallPoint)
    {
        IsClimbing = true;
        transform.rotation = Quaternion.LookRotation(-wallNormal, Vector3.up);
        // 水平吸附到贴墙位置（胶囊半径 0.3 + 2cm 余量），保证攀爬过程射线检测稳定命中
        Vector3 snapped = wallPoint + wallNormal * 0.32f;
        cc.Move(new Vector3(snapped.x - transform.position.x, 0f, snapped.z - transform.position.z));
        // 空中抓墙（跳扑/下落）：先往下滑一小段（约 0.27m），滑停后再开始爬——抓墙的顿挫手感
        slipping = !cc.isGrounded;
        slipV = -2.2f;
    }

    void TickClimb()
    {
        if (toppingOut)
        {
            topOutT += Time.deltaTime / topOutDuration;
            float t = Mathf.Clamp01(topOutT);
            float rise = topEnd.y - topStart.y;
            Vector3 fwd = topEnd - topStart; fwd.y = 0f;
            Vector3 p;
            if (t < 0.62f)                                               // 前 62%：贴墙升至台顶（对齐动画引体→弯腰撑台→提膝段，身体随撑台上升）
            {
                float k = Mathf.SmoothStep(0f, 1f, t / 0.62f);
                p = topStart + Vector3.up * (rise * k);
            }
            else                                                         // 后 38%：移入台面内侧（对齐动画跪撑→蹬起→站直段）
            {
                float k = Mathf.SmoothStep(0f, 1f, (t - 0.62f) / 0.38f);
                p = topStart + Vector3.up * rise + fwd * k;
            }
            cc.Move(p - transform.position);
            if (t >= 1f) { toppingOut = false; IsClimbing = false; }
            return;
        }

        float v = Input.GetAxisRaw("Vertical");
        if (v < -0.1f) { IsClimbing = false; return; }                   // 按 S 松手

        if (slipping)                                                    // 滑坠相位：减速下滑，滑停转正常攀爬
        {
            slipV += 9f * Time.deltaTime;
            if (slipV >= 0f) { slipping = false; slipV = 0f; }
            else { cc.Move(Vector3.up * slipV * Time.deltaTime); return; }
        }

        // —— 翻越检测（M4-9 提前触发）——
        // 贴墙爬升中每帧主动探测上方台面（脚上方 3.0m、前方 0.4m 处向下射线）：
        // 距台面不足 2.2m 即进入翻越相位——2.2m = 手举起恰好触及台沿（脚+2.2），
        // 与 A_Mantle f0"悬挂抓沿"的姿态在物理上对齐；原逻辑须等头部越过台顶（距台面 1.7m）
        // 才触发，玩家观感"人都上去了才翻"。探测起点取脚+3.0（高于台面才能向下命中）。
        // 头顶处墙消失 = 头部已越过台顶：保留为保底路径（防探测被场景几何干扰时卡死）。
        Vector3 probe = transform.position + Vector3.up * 3.0f + transform.forward * 0.4f;
        bool hasTop = Physics.Raycast(probe, Vector3.down, out var g, 3.5f);
        float topRise = hasTop ? g.point.y - transform.position.y : 0f;
        bool wallAhead = Physics.Raycast(transform.position + Vector3.up * 1.7f,
            transform.forward, out _, checkDist, climbableMask);
        if (hasTop && topRise > 0.1f && topRise < 2.2f)
        {
            toppingOut = true; topOutT = 0f;
            topStart = transform.position;
            // +0.045 = 站立位校准高（与 ThirdPersonController.standOffsetY 一致，落台即贴地）
            topEnd = new Vector3(g.point.x, g.point.y + 0.045f, g.point.z) + transform.forward * 0.3f;
            return;
        }
        if (!wallAhead) { IsClimbing = false; return; }                  // 无台面且头顶无墙：松手
        cc.Move((Vector3.up * climbSpeed + transform.forward * 0.1f) * Time.deltaTime);
    }
}
