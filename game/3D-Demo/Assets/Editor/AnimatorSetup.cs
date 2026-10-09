using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// M4-5: 生成 ExplorerAnimator 控制器，并把主角模型接线到场景 Player
public static class AnimatorSetup
{
    const string CtrlPath = "Assets/Animations/ExplorerAnimator.controller";
    const string FbxPath = "Assets/Art/Characters/SK_Explorer.fbx";

    [MenuItem("Demo/生成玩家 Animator")]
    public static void Setup()
    {
        if (!AssetDatabase.IsValidFolder("Assets/Animations"))
            AssetDatabase.CreateFolder("Assets", "Animations");
        if (AssetDatabase.LoadAssetAtPath<AnimatorController>(CtrlPath) != null)
            AssetDatabase.DeleteAsset(CtrlPath);                     // 幂等：重建

        var ctrl = AnimatorController.CreateAnimatorControllerAtPath(CtrlPath);
        ctrl.AddParameter("speed", AnimatorControllerParameterType.Float);
        ctrl.AddParameter("grounded", AnimatorControllerParameterType.Bool);
        ctrl.AddParameter("climbing", AnimatorControllerParameterType.Bool);
        ctrl.AddParameter("jump", AnimatorControllerParameterType.Trigger);

        var sm = ctrl.layers[0].stateMachine;
        var clips = LoadClips();
        var idle = sm.AddState("Idle"); idle.motion = clips["A_Idle"];
        var walk = sm.AddState("Walk"); walk.motion = clips["A_Walk"];
        var run = sm.AddState("Run"); run.motion = clips["A_Run"];
        var jump = sm.AddState("Jump"); jump.motion = clips["A_Jump"];
        var climb = sm.AddState("Climb"); climb.motion = clips["A_Climb"];
        sm.defaultState = idle;

        T(idle, walk, "speed", AnimatorConditionMode.Greater, 0.1f);
        T(walk, idle, "speed", AnimatorConditionMode.Less, 0.1f);
        T(walk, run, "speed", AnimatorConditionMode.Greater, 4.5f);
        T(run, walk, "speed", AnimatorConditionMode.Less, 4.5f);
        T(idle, jump, "jump", AnimatorConditionMode.If, 0f);
        T(walk, jump, "jump", AnimatorConditionMode.If, 0f);
        T(run, jump, "jump", AnimatorConditionMode.If, 0f);          // 补：跑步起跳
        T(climb, idle, "climbing", AnimatorConditionMode.IfNot, 0f);
        T(idle, climb, "climbing", AnimatorConditionMode.If, 0f);
        T(walk, climb, "climbing", AnimatorConditionMode.If, 0f);
        T(run, climb, "climbing", AnimatorConditionMode.If, 0f);     // 补：跑步贴墙接管
        var back = jump.AddTransition(idle);                         // 跳跃播完自动回
        back.hasExitTime = true; back.exitTime = 0.85f; back.duration = 0.1f;
        AssetDatabase.SaveAssets();
        Debug.Log("[AnimatorSetup] ExplorerAnimator.controller 生成完成");
    }

    static void T(AnimatorState a, AnimatorState b, string p, AnimatorConditionMode m, float v)
    {
        var t = a.AddTransition(b); t.hasExitTime = false; t.duration = 0.1f;
        t.AddCondition(m, v, p);
    }

    static Dictionary<string, AnimationClip> LoadClips()
    {   // 从 SK_Explorer.fbx 按 M4-4 登记的 clip 名加载
        var map = new Dictionary<string, AnimationClip>();
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath(FbxPath))
            if (o is AnimationClip c && !c.name.StartsWith("__preview")) map[c.name] = c;
        return map;
    }

    // —— 场景接线：实例化主角模型、隐藏灰盒、挂 Animator ——
    [MenuItem("Demo/接线主角到玩家")]
    public static void Attach()
    {
        Setup();                                                     // 幂等确保控制器存在
        var ctrl = AssetDatabase.LoadAssetAtPath<AnimatorController>(CtrlPath);
        var player = GameObject.Find("Player");
        if (player == null) { Debug.LogError("[AnimatorSetup] 当前场景没有 Player"); return; }

        var old = player.transform.Find("Hero");
        if (old != null) Object.DestroyImmediate(old.gameObject);    // 幂等：清旧实例

        var vis = player.transform.Find("Visual");
        if (vis != null) vis.gameObject.SetActive(false);            // 隐藏灰盒小人（碰撞在 Player 上不受影响）

        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath);
        var hero = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        hero.name = "Hero";
        hero.transform.SetParent(player.transform, false);
        hero.transform.localPosition = new Vector3(0f, 0.81f, 0f);   // 脚底对齐 Player 原点（按 Idle 站姿实测校准）
        hero.transform.localRotation = Quaternion.identity;          // 模型导入即面朝 +Z，无需旋转（实测正面校准）
        hero.transform.localScale = Vector3.one * 1.7f;              // 身高对齐 1.8m 胶囊

        var anim = hero.GetComponent<Animator>();
        if (anim == null) anim = hero.AddComponent<Animator>();
        if (anim.avatar == null)
        {
            foreach (var o in AssetDatabase.LoadAllAssetsAtPath(FbxPath))
                if (o is Avatar av) { anim.avatar = av; break; }
        }
        anim.runtimeAnimatorController = ctrl;
        anim.applyRootMotion = false;                                // 位移由 CharacterController 驱动

        EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
        EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
        Debug.Log("[AnimatorSetup] 主角已接线到 Player（Hero 子对象），场景已保存");
    }
}
