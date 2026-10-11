# M5 里程碑报告（打磨与交付）

> 生成时间：2026-10-11 ｜ 当前覆盖任务：M5-5（性能与 Console 清零）
> 环境：Unity 6 + URP，编辑器 Play 实测（游戏内 runInBackground）

## M5-5 性能与 Console 清零

### 1. Console 清零结果

| 检查项 | 结果 |
|---|---|
| 脚本全量重编译 | 0 Error / 0 Warning |
| Play 启动瞬间 | 0 Error / 0 Warning |
| Play 运行中（火盆区摆位 + 光照/火焰闪烁全开） | 0 Error / 0 Warning |
| 残留提示 | 仅 2 条 MCP-FOR-UNITY 工具自身连接提示（非项目内容，不计入） |

说明：此前跟踪的 URP 阴影相关警告在当前配置下已不复现（火焰光团 `shadowCastingMode=Off` 等改动后消除）。项目产出的 Console 现状为零 Error / 零 Warning。

### 2. 性能抽查

测试场景：B 房间火盆区（本项目视觉负荷最重处——4 火盆 + 火光闪烁 + Bloom + ACES 色调映射同时开启）。

| 指标 | 数值 | 结论 |
|---|---|---|
| 帧率（标记静态前） | ≈176 fps（2144 帧 / 12.1s） | 远高于 60 目标 |
| 帧率（标记静态后） | ≈174 fps（2754 帧 / 15.8s） | 与标记前持平（低模场景，瓶颈不在 draw call） |
| 内存 | 稳定 ≈493 MB | 12s 增量 ≈1.4 MB，`GC.Collect()` 后回落 4.7 MB——属常规帧分配垃圾，无泄漏迹象 |

### 3. 静态批处理标记

- 对 **250 个静止环境网格**标记 `BatchingStatic` 并保存场景：
  - VIZ_ 程序化资产 236 个（墙/柱/地板/藤蔓/火盆底座等）
  - 灰盒对象：FloorA/FloorB/GroundOutside、WallA_*/WallB_*/WallAB_*、ClimbableLedge、Altar
- 排除会动/透明对象：StoneDoor、PushBlock、PressurePlate、Treasure、Flame_*（火焰光团）。
- 说明：低模场景 draw call 压力本就很小，标记属"交付规范预留"——后续继续加资产时静态批处理自动生效。

### 4. 测试方法（可复现）

- **帧率** = Δ`Time.frameCount` / Δ`Time.realtimeSinceStartup`（取两个 MCP 执行点的差值，采样窗口 12~16s）；
- **内存** = `Profiler.GetTotalAllocatedMemoryLong()`，对照 `GC.Collect()` 前后差值判断泄漏；
- **Console** = MCP `read_console`（types=error,warning），清空后重走"全量编译 → Play 启动 → 运行"全流程抓取。

（M5-7 终验记录后续追加。）
