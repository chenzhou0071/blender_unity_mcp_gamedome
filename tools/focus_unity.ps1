param([string]$TitlePart = '3D-Demo', [int]$BurstSeconds = 6)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class FgForce {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool SetFocus(IntPtr hWnd);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
}
"@
$p = Get-Process Unity -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*$TitlePart*" } | Select-Object -First 1
if (-not $p) { Write-Output "unity-window-not-found"; exit 1 }
$h = $p.MainWindowHandle
[FgForce]::ShowWindow($h, 9) | Out-Null
$fg = [FgForce]::GetForegroundWindow()
$fgThread = [FgForce]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
$myThread = [FgForce]::GetCurrentThreadId()
[FgForce]::AttachThreadInput($myThread, $fgThread, $true) | Out-Null
[FgForce]::BringWindowToTop($h) | Out-Null
[FgForce]::SetFocus($h) | Out-Null
$ok = [FgForce]::SetForegroundWindow($h)
[FgForce]::AttachThreadInput($myThread, $fgThread, $false) | Out-Null
Start-Sleep -Milliseconds 400
$newFg = [FgForce]::GetForegroundWindow()
Write-Output "setOk=$ok focused=$($newFg -eq $h)"
if ($BurstSeconds -gt 0) { Start-Sleep -Seconds $BurstSeconds; Write-Output "burst done $BurstSeconds s" }
