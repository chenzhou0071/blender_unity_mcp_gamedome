using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class PushBlock : MonoBehaviour
{
    public float maxPushSpeed = 1.2f;

    Rigidbody rb;
    void Awake() { rb = GetComponent<Rigidbody>(); }

    // 由玩家控制器 OnControllerColliderHit 调用；把推力约束到 X/Z 主导轴，避免斜推乱飘
    public void Push(Vector3 pushDirWorld)
    {
        Vector3 p = pushDirWorld; p.y = 0f;
        if (p.sqrMagnitude < 1e-4f) return;
        if (Mathf.Abs(p.x) < Mathf.Abs(p.z)) p = new Vector3(0, 0, Mathf.Sign(p.z));
        else p = new Vector3(Mathf.Sign(p.x), 0, 0);
        Vector3 v = rb.linearVelocity;                      // Unity 6 API
        rb.linearVelocity = new Vector3(p.x * maxPushSpeed, v.y, p.z * maxPushSpeed);
    }
}
