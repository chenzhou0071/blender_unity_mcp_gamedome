using UnityEngine;

// M5-3.1: 音频听者跟随——位置跟随人物（3D 音效的距离衰减按人物算，而非相机），
// 朝向跟随相机（左右声场与画面保持一致）；由 AudioWiring 创建并接线
public class ListenerFollower : MonoBehaviour
{
    public Transform player, cam;
    public float height = 1.2f;   // 听者高度（胸口），位置 = 人物原点 + 该高度

    void LateUpdate()
    {
        if (player) transform.position = player.position + Vector3.up * height;
        if (cam) transform.rotation = cam.rotation;
    }
}
