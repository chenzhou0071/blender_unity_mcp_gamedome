using UnityEngine;

public class ClimbSystem : MonoBehaviour
{
    public LayerMask climbableMask;
    public float checkDist = 0.65f, climbSpeed = 1.5f, topOutDuration = 0.45f;

    public bool IsClimbing { get; private set; }

    CharacterController cc;
    bool toppingOut; float topOutT;
    Vector3 topStart, topEnd;

    void Awake() { cc = GetComponent<CharacterController>(); }

    void Update()
    {
        if (IsClimbing) { TickClimb(); return; }
        if (!cc.isGrounded) return;
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
            if (t < 0.55f)                                               // 前半段：贴墙升至台顶上方
            {
                float k = Mathf.SmoothStep(0f, 1f, t / 0.55f);
                p = topStart + Vector3.up * (rise * k);
            }
            else                                                         // 后半段：移入台面内侧
            {
                float k = Mathf.SmoothStep(0f, 1f, (t - 0.55f) / 0.45f);
                p = topStart + Vector3.up * rise + fwd * k;
            }
            cc.Move(p - transform.position);
            if (t >= 1f) { toppingOut = false; IsClimbing = false; }
            return;
        }

        float v = Input.GetAxisRaw("Vertical");
        if (v < -0.1f) { IsClimbing = false; return; }                   // 按 S 松手

        // 到顶检测：贴近头顶高度处墙消失 = 头部已越过台顶
        bool wallAhead = Physics.Raycast(transform.position + Vector3.up * 1.7f,
            transform.forward, out _, checkDist, climbableMask);
        if (!wallAhead)
        {
            // 探测上方可站台面（脚上方 2.2m、前方 0.4m 处向下射线）；有则翻上去，无则松手
            Vector3 probe = transform.position + Vector3.up * 2.2f + transform.forward * 0.4f;
            if (Physics.Raycast(probe, Vector3.down, out var g, 3f))
            {
                float rise = g.point.y - transform.position.y;
                if (rise > 0.1f && rise < 2.2f)
                {
                    toppingOut = true; topOutT = 0f;
                    topStart = transform.position;
                    topEnd = new Vector3(g.point.x, g.point.y + 0.02f, g.point.z) + transform.forward * 0.3f;
                    return;
                }
            }
            IsClimbing = false;
            return;
        }
        cc.Move((Vector3.up * climbSpeed + transform.forward * 0.1f) * Time.deltaTime);
    }
}
