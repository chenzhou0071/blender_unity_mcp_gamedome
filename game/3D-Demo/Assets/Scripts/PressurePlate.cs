using UnityEngine;

[RequireComponent(typeof(BoxCollider))]
public class PressurePlate : MonoBehaviour
{
    public StoneDoor door;
    public float pressDepth = 0.08f;

    int occupants;
    Vector3 initialPos;

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
        if (occupants == 1 && door) door.Open();
    }

    void OnTriggerExit(Collider other)
    {
        if (!IsPresser(other)) return;
        occupants = Mathf.Max(0, occupants - 1);
        if (occupants == 0 && door) door.Close();
    }

    void Update()
    {
        Vector3 target = initialPos + (occupants > 0 ? Vector3.down * pressDepth : Vector3.zero);
        transform.position = Vector3.Lerp(transform.position, target, 10f * Time.deltaTime);
    }
}
