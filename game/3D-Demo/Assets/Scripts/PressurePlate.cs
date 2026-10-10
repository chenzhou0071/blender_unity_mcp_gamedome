using UnityEngine;

[RequireComponent(typeof(BoxCollider))]
public class PressurePlate : MonoBehaviour
{
    public StoneDoor door;
    public float pressDepth = 0.08f;

    int occupants;
    bool playerOn, wasPressed;
    float debounce;
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

        // M5-2 修复: pressed 去抖——石头/玩家在检测边缘反复进出时原逻辑逐帧翻转，
        // 导致石门开/关高频交替、隆声逐帧叠加；现要求新状态连续稳定 0.15s 才切换
        bool pressedRaw = occupants > 0 || playerOn;
        if (pressedRaw != wasPressed)
        {
            debounce += Time.deltaTime;
            if (debounce >= 0.15f)
            {
                debounce = 0f;
                wasPressed = pressedRaw;
                if (wasPressed) AudioManager.Instance?.PlateClick();    // M5-2: 压板触发"咔-哒"（0→1 首帧）
                if (door) { if (wasPressed) door.Open(); else door.Close(); }
            }
        }
        else debounce = 0f;
        bool pressed = wasPressed;
        Vector3 target = initialPos + (pressed ? Vector3.down * pressDepth : Vector3.zero);
        transform.position = Vector3.Lerp(transform.position, target, 10f * Time.deltaTime);
    }
}
