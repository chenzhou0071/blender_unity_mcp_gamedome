using UnityEngine;

public static class LevelSpec
{
    public const float WallH = 6f, WallT = 0.5f, DoorWidth = 3f, DoorHeight = 4f;
    public static readonly Vector3 PlayerSpawn = new Vector3(0, 0.05f, -6);
    public static readonly Vector3 DoorPos = new Vector3(0, DoorHeight / 2f, 8);
    public static readonly Vector3 PlatePos = new Vector3(4, 0.05f, -2);
    public static readonly Vector3 BlockPos = new Vector3(-2, 0.5f, -2);
    public static readonly Vector3 LedgeCenter = new Vector3(0, 1.5f, 18);
    public static readonly Vector3 LedgeSize = new Vector3(6, 3, 4);
    public static readonly Vector3 AltarPos = new Vector3(0, 3.5f, 19);    // 攀爬石台顶面上（台顶 y=3 + 祭坛半高 0.5）
    public static readonly Vector3 TreasurePos = new Vector3(0, 4.4f, 19); // 祭坛上方悬浮
    public const string LayerClimbable = "Climbable";
    public const string TagPushable = "Pushable";
}
