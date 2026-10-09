param([string]$TitlePart = '3D-Demo', [int]$HoldMs = 3000, [int]$Vk = 0x57)
# 一气呵成：强制聚焦 Unity 窗口 -> 立即按住按键(Vk，默认 W=0x57) -> 松开
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class FgKey {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool SetFocus(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
}
"@
$p = Get-Process Unity -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*$TitlePart*" } | Select-Object -First 1
if (-not $p) { Write-Output "unity-window-not-found"; exit 1 }
$h = $p.MainWindowHandle
[FgKey]::ShowWindow($h, 9) | Out-Null
$fg = [FgKey]::GetForegroundWindow()
$fgThread = [FgKey]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
$myThread = [FgKey]::GetCurrentThreadId()
[FgKey]::AttachThreadInput($myThread, $fgThread, $true) | Out-Null
[FgKey]::BringWindowToTop($h) | Out-Null
[FgKey]::SetFocus($h) | Out-Null
$ok = [FgKey]::SetForegroundWindow($h)
[FgKey]::AttachThreadInput($myThread, $fgThread, $false) | Out-Null
Start-Sleep -Milliseconds 120
Write-Output "focus setOk=$ok fgIsUnity=$([FgKey]::GetForegroundWindow() -eq $h)"
# 按住按键
[FgKey]::keybd_event($Vk, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds $HoldMs
[FgKey]::keybd_event($Vk, 0, 2, [UIntPtr]::Zero)
Write-Output "Vk=$Vk held $HoldMs ms"
