using UnityEngine;

// M5-2/六轮: 音效总线——脚步/落地/机关/完成走 OneShot；推石走可开关的摩擦 loop
// 火盆噼啪为 3D 空间源（由 AudioWiring 配置在 Torch 对象上，近响远弱）
// 注：起跳音效经用户试听移除（M5-1）；环境背景声经六轮试听移除（ambient 字段保留便于回退）
public class AudioManager : MonoBehaviour
{
    public static AudioManager Instance;
    public AudioClip[] footsteps;
    public AudioClip land, plateClick, doorRumble, goalChime, blockGrind, ambient;

    AudioSource oneShot, grind;
    float lastDoor;

    void Awake()
    {
        Instance = this;
        AudioListener.volume = 0.5f;           // 四轮试听：全局音量 50%
        oneShot = gameObject.AddComponent<AudioSource>(); oneShot.playOnAwake = false;
        grind = gameObject.AddComponent<AudioSource>();
        grind.playOnAwake = false;             // 修复: 防进游戏瞬间漏一声摩擦
        grind.loop = true; grind.volume = 0.5f; grind.clip = blockGrind;
    }

    void PlayLoop(AudioClip c, float v)
    { if (!c) return; var s = gameObject.AddComponent<AudioSource>(); s.clip = c; s.loop = true; s.volume = v; s.Play(); }

    public void OneShot(AudioClip c, float v = 1f) { if (c) oneShot.PlayOneShot(c, v); }
    public void Footstep() { if (footsteps != null && footsteps.Length > 0) oneShot.PlayOneShot(footsteps[Random.Range(0, footsteps.Length)], 0.25f); }   // 四轮试听：脚步再微降
    public void Land() => OneShot(land, 0.4f);   // 落地实录版：文件对齐 -20dB + 音量再降至 0.4（用户要求小声）
    public void PlateClick() => OneShot(plateClick);
    public void Door()
    {
        if (Time.time - lastDoor < 0.5f) return;   // 修复: 石门隆声节流（防压板抖动逐帧叠声）
        lastDoor = Time.time;
        OneShot(doorRumble);
    }
    public void Goal() => OneShot(goalChime);
    public void Grind(bool on)
    {
        if (!grind.clip) return;
        if (on && !grind.isPlaying) grind.Play();
        else if (!on && grind.isPlaying) grind.Stop();
    }
}
