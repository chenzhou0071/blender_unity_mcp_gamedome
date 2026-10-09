param(
    [Parameter(Mandatory = $true)][string]$TaskId
)
# Tripo 任务查询：读取凭据 → GET /v3/tasks/{id} → 打印任务详情（含结果下载链接）
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File tools\tripo\get_task.ps1 -TaskId <uuid>
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

$key = [System.Text.Encoding]::Unicode.GetString($bytes).TrimEnd([char]0).Trim()
if (-not $key.StartsWith("tsk_")) {
    $k2 = [System.Text.Encoding]::UTF8.GetString($bytes).TrimEnd([char]0).Trim()
    if ($k2.StartsWith("tsk_")) { $key = $k2 }
}
Write-Output ("KEY_FORMAT prefix={0} len={1}" -f $key.Substring(0, [Math]::Min(4, $key.Length)), $key.Length)

try {
    $resp = Invoke-RestMethod -Uri "https://openapi.tripo3d.com/v3/tasks/$TaskId" -Headers @{ Authorization = "Bearer $key" } -Method Get
    $resp | ConvertTo-Json -Depth 10
} catch {
    Write-Output "REQUEST_FAILED"
    if ($_.Exception.Response) {
        Write-Output ("HTTP_STATUS: {0}" -f [int]$_.Exception.Response.StatusCode)
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Output ("BODY: " + $reader.ReadToEnd())
    } else {
        Write-Output $_.Exception.Message
    }
}
