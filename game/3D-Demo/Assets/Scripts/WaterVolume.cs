using UnityEngine;

// M6-4: 游泳水域——矩形范围判定（x/z 平面），供 ThirdPersonController 查询。
// CC 不产生 Trigger 事件（沿用 GoalTrigger 经验），游泳与否走位置判定；
// “水深是否足够游泳（水线到肩）”由控制器结合 swimDepth 自行判断（反馈：入水过早就切游泳）。
public class WaterVolume : MonoBehaviour
{
    public static WaterVolume Instance;
    public float waterLevel = -2.6f;
    public Vector2 xzMin = new Vector2(-50f, 139f), xzMax = new Vector2(50f, 161f);   // 横向与水面同宽（100m 横贯河谷）；z 端点贴水线（河床加深后水线 138-161）

    void Awake() { Instance = this; }

    public bool InZone(Vector3 p)
    {
        return p.x > xzMin.x && p.x < xzMax.x && p.z > xzMin.y && p.z < xzMax.y;
    }
}
