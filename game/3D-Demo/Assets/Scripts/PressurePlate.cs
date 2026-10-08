using UnityEngine;

[RequireComponent(typeof(BoxCollider))]
public class PressurePlate : MonoBehaviour
{
    public StoneDoor door;
    public float pressDepth = 0.08f;

    int occupants;
    bool playerOn, wasPressed;
    Vector3 initialPos;
    Transform player;

    void Awake()
    {
        initialPos = transform.position;
        GetComponent<BoxCollider>().isTrigger = true;
    }

    bool IsPresser(Collider c) => c.CompareTag(LevelSpec.TagPushable) || c.CompareTag("Player");

    void OnTriggerEnter(Collider other)
    {
        if (!IsPresser(other)) return;
        occupants++;
    }

    void OnTriggerExit(Collider other)
    {
        if (!IsPresser(other)) return;
        occupants = Mathf.Max(0, occupants - 1);
    }

    void Update()
    {
        // 玩家为 CharacterController，不产生 Trigger 事件 → 单独用位置检测（板面半宽 0.6 + 余量）
        if (!player)
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            if (p) player = p.transform;
        }
        if (player)
        {
            Vector3 d = player.position - initialPos;
            playerOn = Mathf.Abs(d.x) < 0.7f && Mathf.Abs(d.z) < 0.7f && d.y > -0.2f && d.y < 0.6f;
        }

        bool pressed = occupants > 0 || playerOn;
        if (pressed != wasPressed)
        {
            wasPressed = pressed;
            if (door) { if (pressed) door.Open(); else door.Close(); }
        }
        Vector3 target = initialPos + (pressed ? Vector3.down * pressDepth : Vector3.zero);
        transform.position = Vector3.Lerp(transform.position, target, 10f * Time.deltaTime);
    }
}
