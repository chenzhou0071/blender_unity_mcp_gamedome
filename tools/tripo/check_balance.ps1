# Tripo API 零消耗验证：读取 Windows 凭据管理器中的 key → 查询账号余额
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File tools\tripo\check_balance.ps1
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$sig = @"
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
public struct CREDENTIAL {
    public uint Flags;
    public uint Type;
    public string TargetName;
    public string Comment;
    public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
    public uint CredentialBlobSize;
    public IntPtr CredentialBlob;
    public uint Persist;
    public uint AttributeCount;
    public IntPtr Attributes;
    public string TargetAlias;
    public string UserName;
}

public static class CredMan {
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool CredRead(string target, uint type, uint reservedFlag, out IntPtr credentialPtr);
    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern void CredFree(IntPtr cred);
}
"@
Add-Type -TypeDefinition $sig

$ptr = [IntPtr]::Zero
$ok = [CredMan]::CredRead("MCPForUnity.AssetGen:tripo", 1, 0, [ref]$ptr)
if (-not $ok) { Write-Output "CRED_READ_FAIL"; exit 1 }

$cred = [System.Runtime.InteropServices.Marshal]::PtrToStructure($ptr, [type][CREDENTIAL])
$bytes = New-Object byte[] $cred.CredentialBlobSize
[System.Runtime.InteropServices.Marshal]::Copy($cred.CredentialBlob, $bytes, 0, $cred.CredentialBlobSize)
[CredMan]::CredFree($ptr)

# 解码（凭据 blob 通常为 UTF-16LE；兼容 UTF-8）
$key = [System.Text.Encoding]::Unicode.GetString($bytes).TrimEnd([char]0).Trim()
if (-not $key.StartsWith("tsk_")) {
    $k2 = [System.Text.Encoding]::UTF8.GetString($bytes).TrimEnd([char]0).Trim()
    if ($k2.StartsWith("tsk_")) { $key = $k2 }
}
Write-Output ("KEY_FORMAT prefix={0} len={1}" -f $key.Substring(0, [Math]::Min(4, $key.Length)), $key.Length)

$resp = Invoke-RestMethod -Uri "https://openapi.tripo3d.com/v3/account/balance" -Headers @{ Authorization = "Bearer $key" } -Method Get
$resp | ConvertTo-Json -Depth 6
