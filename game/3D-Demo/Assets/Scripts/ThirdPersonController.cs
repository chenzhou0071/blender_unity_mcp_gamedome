using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class ThirdPersonController : MonoBehaviour
{
    public float moveSpeed = 1.5f, runSpeed = 3.5f, turnLerp = 12f, gravity = -20f, jumpHeight = 1.2f;  // M4-9: 速度分层——散步 1.5（walk 播放率 0.9）/ 慢跑 3.5（run 播放率 1.0 动画原速零滑步）
    public float standOffsetY = 0.045f;                               // 站立位校准：原点距地面高（脚底贴地+5mm）
    public Transform cameraPivot;

    CharacterController cc;
    float velocityY;
    ClimbSystem climb;
    Animator anim;
    bool jumpPending; float jumpDelayT; bool jumpIsRun;   // M4-9: 起跳前摇（蹲→蹬→离地时序对齐 A_Jump）；M4-11: 起跳档位（跑跳）
    bool airLocked; Vector3 airVel;       // M4-11: 跑跳空中惯性（离地时启用按下瞬间锁定的起跳冲量，松键不空中急停）
    const float runJumpDelay = 0.1f;      // M4-11: 跑跳前摇 0.1s（对齐 A_JumpRun f3 蹬伸；走/立定跳保持 0.26s）
    bool wasGrounded; float stepDist;     // M5-2: 上帧着地状态（落地检测）/ 脚步位移累计

    void Awake() { cc = GetComponent<CharacterController>(); climb = GetComponent<ClimbSystem>(); }

    void Start() { anim = GetComponentInChildren<Animator>(); }   // M4-5: 主角模型上的 Animator

    void Update()
    {
        if (climb && climb.IsClimbing) { velocityY = 0f; airLocked = false; SyncAnimator(); return; }   // 攀爬期间交出控制权（跑跳扑墙则清除惯性锁）
        bool grounded = cc.isGrounded;
        if (!wasGrounded && grounded && velocityY < -3f) AudioManager.Instance?.Land();   // M5-2: 落地音（下落足够快才响，轻踩不触发）
        wasGrounded = grounded;
        if (grounded && velocityY < 0f) velocityY = -2f;

        float h = Input.GetAxisRaw("Horizontal"), v = Input.GetAxisRaw("Vertical");
        float yaw = cameraPivot ? cameraPivot.eulerAngles.y : 0f;
        Vector3 dir = Quaternion.Euler(0, yaw, 0) * new Vector3(h, 0, v);
        if (dir.sqrMagnitude > 1f) dir.Normalize();

        float speed = Input.GetKey(KeyCode.LeftShift) ? runSpeed : moveSpeed;   // 输入档速度（M4-9 分层：走 1.5 / 跑 3.5）
        bool airRush = airLocked && !grounded;                  // M4-11: 跑跳空中惯性相位
        if (dir.sqrMagnitude > 0.01f && !airRush)               // 锁速期间锁向（速度保持起跳方向，空中转向会与轨迹错位）
        {
            var look = Quaternion.LookRotation(dir);
            transform.rotation = Quaternion.Slerp(transform.rotation, look, turnLerp * Time.deltaTime);
        }
        if (grounded && Input.GetButtonDown("Jump") && !jumpPending)
        {
            // M4-9: 起跳前摇 0.26s —— 先播 A_Jump 下蹲蓄力（f0-f7=0.233s），
            // 到蹬伸段（f7-f10）才给物理速度，"蹲→蹬→离地"与动画同步（原先按下即离地，动画还在蹲）
            // M4-11: 跑跳（跑速档起跳）前摇 0.1s 对齐 A_JumpRun f3 蹬伸——跑步中无停顿、不打断节奏
            jumpIsRun = dir.sqrMagnitude > 0.01f && speed > 2.5f;
            airVel = dir * speed;                                 // M4-11: 起跳冲量（按下瞬间锁定，离地时启用）
            jumpPending = true; jumpDelayT = jumpIsRun ? runJumpDelay : 0.26f;
            if (anim) anim.SetTrigger("jump");   // M4-5: 触发跳跃动画（跑跳/走跳由 Animator 按 state 分流）
        }
        if (jumpPending)
        {
            jumpDelayT -= Time.deltaTime;
            if (jumpDelayT <= 0f)
            {
                jumpPending = false;
                if (grounded)
                {
                    velocityY = Mathf.Sqrt(jumpHeight * -2f * gravity);   // 蓄力中离地（走落）则放弃起跳
                    if (jumpIsRun) airLocked = true;                      // M4-11: 跑跳离地——启用起跳冲量锁（airVel）
                }
            }
        }
        velocityY += gravity * Time.deltaTime;

        Vector3 move = dir * speed;
        if (airRush) { move.x = airVel.x; move.z = airVel.z; }              // M4-11: 空中惯性（松开方向键不空中急停）
        else if (airLocked && grounded && velocityY <= 0f) airLocked = false;   // 升空/离地帧（grounded 缓存 + vy>0）不解除；下落触地才解除
        move.y = velocityY;
        cc.Move(move * Time.deltaTime);
        GroundSnap(grounded);                              // 贴地吸附（消除 skinWidth 内悬空残差）

        // M5-2: 脚步声——按实际水平位移累计触发（走 0.75m/跑 1.25m 一步，对齐动画步频）
        if (grounded)
        {
            stepDist += new Vector2(cc.velocity.x, cc.velocity.z).magnitude * Time.deltaTime;
            if (stepDist >= (speed > 2.5f ? 1.25f : 0.75f)) { AudioManager.Instance?.Footstep(); stepDist = 0f; }
        }

        SyncAnimator();
    }

    // 贴地吸附：CC 在 skinWidth 内判 grounded 时不自动沉降，出生点/高台会留悬空残差；
    // 每帧对脚下地面重投影，把原点校准回「地面 + standOffsetY」的稳定站立高度（小步上限 8cm）。
    void GroundSnap(bool grounded)
    {
        if (!grounded || velocityY > 0.01f) return;
        RaycastHit gh;
        if (Physics.Raycast(transform.position + Vector3.up * 0.1f, Vector3.down, out gh, 0.5f, ~0, QueryTriggerInteraction.Ignore)
            && gh.normal.y > 0.7f)
        {
            float dy = gh.point.y + standOffsetY - transform.position.y;
            if (Mathf.Abs(dy) > 0.003f && Mathf.Abs(dy) < 0.08f)
                transform.position += Vector3.up * dy;
        }
    }

    // M4-5: 移动状态同步给 Animator（speed/grounded/climbing）
    void SyncAnimator()
    {
        if (!anim) return;
        Vector3 hv = new Vector3(cc.velocity.x, 0f, cc.velocity.z);
        anim.SetFloat("speed", hv.magnitude);
        anim.SetBool("grounded", cc.isGrounded);
        anim.SetBool("climbing", climb && climb.IsClimbing);
        anim.SetBool("toppingOut", climb && climb.IsToppingOut);   // M4-8: 爬顶翻越段（Climb→Mantle）
    }

    void OnControllerColliderHit(ControllerColliderHit hit)
    {
        if (!hit.rigidbody) return;
        var pb = hit.rigidbody.GetComponent<PushBlock>();
        if (pb) pb.Push(hit.moveDirection);
    }
}
