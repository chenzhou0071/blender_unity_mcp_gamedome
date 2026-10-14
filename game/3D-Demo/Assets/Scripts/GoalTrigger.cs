using UnityEngine;

public class GoalTrigger : MonoBehaviour
{
    public float radius = 1.5f;             // 世界半径（与构建器 SphereCollider 一致）
    public string message = "探索完成！\n你取得了圣物";   // M6-6: 终点文案（默认=原宝物文案，向后兼容；崖顶遗迹用另一组）

    bool done;
    Transform player;

    void Update()
    {
        if (done) return;
        if (!player)
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            if (!p) return;
            player = p.transform;
        }
        // 玩家为 CharacterController，不产生 Trigger 事件 → 用躯干点到宝物球心的距离检测
        Vector3 torso = player.position + Vector3.up * 0.9f;
        if (Vector3.Distance(torso, transform.position) <= radius)
        {
            done = true;
            AudioManager.Instance?.Goal();                       // M5-2: 取得圣物钟声
            if (SimpleUI.Instance) SimpleUI.Instance.ShowComplete(message);
        }
    }
}
