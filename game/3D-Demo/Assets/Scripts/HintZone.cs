using UnityEngine;

// M6: 通用提示区——玩家进入半径内一次性更新目标文案（CC 不产生 Trigger 事件，用距离检测）。
public class HintZone : MonoBehaviour
{
    public string text;
    public float radius = 5f;
    Transform player;
    bool fired;

    void Update()
    {
        if (fired) return;
        if (!player) { var p = GameObject.FindGameObjectWithTag("Player"); if (p) player = p.transform; }
        if (player && Vector3.Distance(player.position, transform.position) < radius)
        {
            fired = true;
            if (SimpleUI.Instance) SimpleUI.Instance.SetObjective(text);
        }
    }
}
