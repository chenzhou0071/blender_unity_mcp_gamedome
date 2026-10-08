using UnityEngine;

public class StoneDoor : MonoBehaviour
{
    public float raiseHeight = 4.3f, duration = 2f;

    Vector3 closedPos; bool open; float t;

    void Awake() { closedPos = transform.position; }

    public void Open()
    {
        if (!open && SimpleUI.Instance) SimpleUI.Instance.SetObjective("石门已开——攀上高台，取得圣物！");
        open = true;
    }
    public void Close() { open = false; }

    void Update()
    {
        t = Mathf.MoveTowards(t, open ? 1f : 0f, Time.deltaTime / duration);
        transform.position = closedPos + Vector3.up * (raiseHeight * Mathf.SmoothStep(0f, 1f, t));
    }
}
