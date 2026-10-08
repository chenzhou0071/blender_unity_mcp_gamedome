using UnityEngine;

public class CameraFollow : MonoBehaviour
{
    public Transform target;
    public float distance = 5f, height = 1.6f, mouseSens = 3f, minPitch = -20f, maxPitch = 60f;
    public float posLerp = 10f, collisionRadius = 0.25f;

    float yaw, pitch = 15f;

    void Start()
    {
        if (target) yaw = target.eulerAngles.y;
        Cursor.lockState = CursorLockMode.Locked;   // 编辑器内点击画面进入锁定，Esc 解锁
    }

    void LateUpdate()
    {
        if (!target) return;
        yaw += Input.GetAxis("Mouse X") * mouseSens;
        pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * mouseSens, minPitch, maxPitch);

        Vector3 pivot = target.position + Vector3.up * height;
        Quaternion rot = Quaternion.Euler(pitch, yaw, 0);
        Vector3 desired = pivot - rot * Vector3.forward * distance;

        Vector3 dir = (desired - pivot).normalized;
        if (Physics.SphereCast(pivot, collisionRadius, dir, out var hit, distance, ~0, QueryTriggerInteraction.Ignore))
            desired = pivot + dir * Mathf.Max(0.3f, hit.distance - 0.1f);

        transform.position = Vector3.Lerp(transform.position, desired, posLerp * Time.deltaTime);
        transform.rotation = Quaternion.LookRotation(pivot - transform.position);
    }
}
