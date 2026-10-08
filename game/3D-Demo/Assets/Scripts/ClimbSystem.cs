using UnityEngine;

public class ClimbSystem : MonoBehaviour
{
    public LayerMask climbableMask;
    public float checkDist = 0.65f, climbSpeed = 1.5f, topOutDuration = 0.4f, topOutForward = 0.7f;

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
            BeginClimb(hit.normal);
    }

    void BeginClimb(Vector3 wallNormal)
    {
        IsClimbing = true;
        transform.rotation = Quaternion.LookRotation(-wallNormal, Vector3.up);
    }

    void TickClimb()
    {
        if (toppingOut)
        {
            topOutT += Time.deltaTime / topOutDuration;
            cc.Move(Vector3.Lerp(topStart, topEnd, Mathf.Clamp01(topOutT)) - transform.position);
            if (topOutT >= 1f) { toppingOut = false; IsClimbing = false; }
            return;
        }
        float v = Input.GetAxisRaw("Vertical");
        if (v < -0.1f) { IsClimbing = false; return; }                   // 按 S 松手
        bool wallAhead = Physics.Raycast(transform.position + Vector3.up * 2.0f,
            transform.forward, out _, checkDist, climbableMask);
        if (!wallAhead)                                                   // 到顶 → 翻上去
        {
            toppingOut = true; topOutT = 0f;
            topStart = transform.position;
            topEnd = transform.position + Vector3.up * 0.9f + transform.forward * topOutForward;
            return;
        }
        cc.Move(Vector3.up * (climbSpeed * Time.deltaTime) - transform.forward * 0.5f * Time.deltaTime);
    }
}
