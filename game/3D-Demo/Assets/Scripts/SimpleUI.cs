using UnityEngine;
using UnityEngine.UI;

public class SimpleUI : MonoBehaviour
{
    public static SimpleUI Instance;

    Text objective, complete;
    Font font;

    void Awake()
    {
        Instance = this;
        font = Font.CreateDynamicFontFromOSFont("Microsoft YaHei", 24);
        if (!font) font = Font.CreateDynamicFontFromOSFont(new[] { "SimHei", "Arial" }, 24);

        var canvasGo = new GameObject("HUD", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        var canvas = canvasGo.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;

        objective = MakeText(canvasGo.transform, new Vector2(24, -24), TextAnchor.UpperLeft, "找到并开启石门", 24);
        complete = MakeText(canvasGo.transform, Vector2.zero, TextAnchor.MiddleCenter, "探索完成！\n你取得了圣物", 48);
        var rt = complete.rectTransform;
        rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
        rt.pivot = new Vector2(0.5f, 0.5f);
        rt.anchoredPosition = Vector2.zero;
        rt.sizeDelta = new Vector2(900, 300);
        complete.gameObject.SetActive(false);
    }

    Text MakeText(Transform parent, Vector2 anchoredPos, TextAnchor anchor, string text, int size)
    {
        var go = new GameObject("Text", typeof(Text));
        go.transform.SetParent(parent, false);
        var t = go.GetComponent<Text>();
        t.font = font; t.fontSize = size; t.text = text; t.alignment = anchor; t.color = Color.white;
        var rt = t.rectTransform;
        rt.anchorMin = rt.anchorMax = new Vector2(0, 1); rt.pivot = new Vector2(0, 1);
        rt.anchoredPosition = anchoredPos; rt.sizeDelta = new Vector2(900, 300);
        return t;
    }

    public void SetObjective(string s) { if (objective) objective.text = s; }
    public void ShowComplete() { if (complete) complete.gameObject.SetActive(true); SetObjective(""); }
}
