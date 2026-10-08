using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class ThirdPersonController : MonoBehaviour
{
    public float moveSpeed = 4f, runSpeed = 6f, turnLerp = 12f, gravity = -20f, jumpHeight = 1.2f;
    public Transform cameraPivot;

    CharacterController cc;
    float velocityY;
    ClimbSystem climb;

    void Awake() { cc = GetComponent<CharacterController>(); climb = GetComponent<ClimbSystem>(); }

    void Update()
    {
        if (climb && climb.IsClimbing) { velocityY = 0f; return; }   // 攀爬期间交出控制权
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
        if (grounded && Input.GetButtonDown("Jump")) velocityY = Mathf.Sqrt(jumpHeight * -2f * gravity);
        velocityY += gravity * Time.deltaTime;

        float speed = Input.GetKey(KeyCode.LeftShift) ? runSpeed : moveSpeed;
        Vector3 move = dir * speed; move.y = velocityY;
        cc.Move(move * Time.deltaTime);
    }

    void OnControllerColliderHit(ControllerColliderHit hit)
    {
        if (!hit.rigidbody) return;
        var pb = hit.rigidbody.GetComponent<PushBlock>();
        if (pb) pb.Push(hit.moveDirection);
    }
}
