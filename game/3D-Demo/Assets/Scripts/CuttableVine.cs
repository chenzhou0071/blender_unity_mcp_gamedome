using System.Collections;
using UnityEngine;
// M6-3: 藤帘斩断——绕顶部铰链向远侧塌落 80°+微沉（0.9s）后隐藏；移除碰撞、更新目标文案。
public class CuttableVine : MonoBehaviour, ICuttable
{
    Transform player; bool done, hinted;

    void Update()
    {
        if (done) return;
        if (!player) { var p = GameObject.FindGameObjectWithTag("Player"); if (p) player = p.transform; }
        if (!player) return;
        if (!hinted && Vector3.Distance(player.position, transform.position) < 6f)
        {
            hinted = true;
            SimpleUI.Instance?.SetObjective("藤蔓挡住了去路——挥刀砍断（鼠标左键）");
        }
    }

    public void Cut(Vector3 dir)
    {
        if (done) return;
        done = true;
        AudioManager.Instance?.Chop();
        var col = GetComponent<Collider>(); if (col) col.enabled = false;
        SimpleUI.Instance?.SetObjective("继续向北——游过河谷");
        StartCoroutine(Fall(dir));
    }

    IEnumerator Fall(Vector3 dir)
    {
        float t = 0f;
        Quaternion r0 = transform.rotation; Vector3 p0 = transform.position;
        Vector3 axis = Vector3.Cross(dir, Vector3.up).normalized;   // 倒向挥刀方向（远离玩家）；注意 Cross(up,dir) 会反向（倒向玩家）
        while (t < 1f)
        {
            t += Time.deltaTime / 0.9f;
            float k = Mathf.SmoothStep(0f, 1f, Mathf.Min(t, 1f));
            transform.rotation = Quaternion.AngleAxis(80f * k, axis) * r0;
            transform.position = p0 + Vector3.down * (0.9f * k);
            yield return null;
        }
        gameObject.SetActive(false);
    }
}
