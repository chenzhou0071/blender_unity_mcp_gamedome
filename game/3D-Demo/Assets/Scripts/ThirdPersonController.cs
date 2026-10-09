using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class ThirdPersonController : MonoBehaviour
{
    public float moveSpeed = 2.5f, runSpeed = 4f, turnLerp = 12f, gravity = -20f, jumpHeight = 1.2f;   // M4-7: 实机四次校准（4/8→2/4→3/6→2.5/4）；Controller 播放率 1.79/1.29 匹配零滑步
    public float standOffsetY = 0.045f;                               // 站立位校准：原点距地面高（脚底贴地+5mm）
    public Transform cameraPivot;

    CharacterController cc;
    float velocityY;
    ClimbSystem climb;
    Animator anim;

    void Awake() { cc = GetComponent<CharacterController>(); climb = GetComponent<ClimbSystem>(); }

    void Start() { anim = GetComponentInChildren<Animator>(); }   // M4-5: 主角模型上的 Animator

    void Update()
    {
        if (climb && climb.IsClimbing) { velocityY = 0f; SyncAnimator(); return; }   // 攀爬期间交出控制权
        bool grounded = cc.isGrounded;
        if (grounded && velocityY < 0f) velocityY = -2f;

        float h = Input.GetAxisRaw("Horizontal"), v = Input.GetAxisRaw("Vertical");
        float yaw = cameraPivot ? cameraPivot.eulerAngles.y : 0f;
        Vector3 dir = Quaternion.Euler(0, yaw, 0) * new Vector3(h, 0, v);
        if (dir.sqrMagnitude > 1f) dir.Normalize();

        if (dir.sqrMagnitude > 0.01f)
        {
            var look = Quaternion.LookRotation(dir);
            transform.rotation = Quaternion.Slerp(transform.rotation, look, turnLerp * Time.deltaTime);
        }
        if (grounded && Input.GetButtonDown("Jump"))
        {
            velocityY = Mathf.Sqrt(jumpHeight * -2f * gravity);
            if (anim) anim.SetTrigger("jump");   // M4-5: 触发跳跃动画
        }
        velocityY += gravity * Time.deltaTime;

        float speed = Input.GetKey(KeyCode.LeftShift) ? runSpeed : moveSpeed;
        Vector3 move = dir * speed; move.y = velocityY;
        cc.Move(move * Time.deltaTime);
        GroundSnap(grounded);                              // 贴地吸附（消除 skinWidth 内悬空残差）

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
    }

    void OnControllerColliderHit(ControllerColliderHit hit)
    {
        if (!hit.rigidbody) return;
        var pb = hit.rigidbody.GetComponent<PushBlock>();
        if (pb) pb.Push(hit.moveDirection);
    }
}
