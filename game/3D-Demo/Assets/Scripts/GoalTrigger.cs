using UnityEngine;

public class GoalTrigger : MonoBehaviour
{
    bool done;

    void OnTriggerEnter(Collider other)
    {
        if (done || !other.CompareTag("Player")) return;
        done = true;
        if (SimpleUI.Instance) SimpleUI.Instance.ShowComplete();
    }
}
