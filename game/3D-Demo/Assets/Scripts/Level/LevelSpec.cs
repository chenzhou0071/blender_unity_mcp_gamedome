using UnityEngine;

// M6-1: 神庙重做后的关卡布局——金字塔 @(0,0,6)；房间 x±12 / z±10 / 地板顶 y=6 / 天花 y=14；
// 石门在房间北墙 z=10；楼梯间自 z10(y6) 降至 z19(y0)；北门洞 z22~24；前庭 z24~34。
public static class LevelSpec
{
    public const float WallH = 6f, WallT = 0.5f, DoorWidth = 3f, DoorHeight = 4f;
    public const float RoomHalfX = 12f, RoomHalfZ = 10f, RoomFloorY = 6f, RoomCeilY = 14f;
    public static readonly Vector3 PlayerSpawn = new Vector3(0, 6.05f, -4.5f);
    public static readonly Vector3 DoorPos = new Vector3(0, 8, 10);        // 石门中心：门底=地板 y6 + 高 4/2
    public static readonly Vector3 PlatePos = new Vector3(4, 6.05f, -2);
    public static readonly Vector3 BlockPos = new Vector3(-2, 6.5f, -2);
    public const string LayerClimbable = "Climbable";
    public const string TagPushable = "Pushable";
}
