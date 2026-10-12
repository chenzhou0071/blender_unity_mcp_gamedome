param(
  [string]$Ping = '',          # 非空: 发送 ping（值为 '1'）
  [string]$Menu = '',          # 执行菜单: -Menu "Demo/构建户外场景"
  [string]$Code = '',          # 执行 C# 代码（MCPDynamicCode.Execute 体）: -Code $code（单行）
  [string]$CodeFile = '',      # 从文件读取 C# 代码（多行代码用这个，避免命令行拆行）
  [int]$Port = 6400,
  [int]$TimeoutSec = 300
)
# Unity MCP stdio bridge 直连客户端（帧: 8字节大端长度 + UTF-8 JSON）。
# 用法示例:
#   .\unity_bridge.ps1 -Ping 1
#   .\unity_bridge.ps1 -Menu "Demo/构建户外场景"
#   .\unity_bridge.ps1 -CodeFile tools\_m6_check1.cs
# 命令信封与 MCPForUnity 一致: {"type":"<tool>","params":{...}}

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if ($CodeFile) { $Code = [System.IO.File]::ReadAllText($CodeFile, [System.Text.Encoding]::UTF8) }

function Send-Unity([string]$payloadJson) {
  $client = New-Object System.Net.Sockets.TcpClient
  $client.Connect('127.0.0.1', $Port)
  try {
    $stream = $client.GetStream()
    $stream.ReadTimeout = $TimeoutSec * 1000
    # 连接握手：Unity 先发 30 字节 ASCII "WELCOME UNITY-MCP 1 FRAMING=1\n"
    $hs = [byte[]]::new(30)
    $read = 0
    while ($read -lt 30) { $n = $stream.Read($hs, $read, 30 - $read); if ($n -le 0) { throw 'closed during handshake' }; $read += $n }
    $hsText = [System.Text.Encoding]::ASCII.GetString($hs)
    if (-not $hsText.StartsWith('WELCOME')) { throw "bad handshake: $hsText" }
    $payload = [System.Text.Encoding]::UTF8.GetBytes($payloadJson)
    $header = [byte[]]::new(8)
    [UInt64]$len = $payload.Length
    for ($i = 0; $i -lt 8; $i++) { $header[7 - $i] = [byte](($len -shr (8 * $i)) -band 0xFF) }
    $stream.Write($header, 0, 8)
    $stream.Write($payload, 0, $payload.Length)
    $stream.Flush()
    $hdr = [byte[]]::new(8)
    $read = 0
    while ($read -lt 8) { $n = $stream.Read($hdr, $read, 8 - $read); if ($n -le 0) { throw 'connection closed' }; $read += $n }
    [UInt64]$rlen = 0
    for ($i = 0; $i -lt 8; $i++) { $rlen = ($rlen -shl 8) -bor [UInt64]$hdr[$i] }
    $buf = [byte[]]::new([int]$rlen)
    $read = 0
    while ($read -lt $rlen) { $n = $stream.Read($buf, $read, [int]$rlen - $read); if ($n -le 0) { throw 'connection closed mid-frame' }; $read += $n }
    return [System.Text.Encoding]::UTF8.GetString($buf)
  } finally { $client.Close() }
}

if ($Ping) { Write-Output (Send-Unity 'ping'); exit 0 }
if ($Menu) {
  $params = @{ menu_path = $Menu } | ConvertTo-Json -Compress
  $envelope = '{"type":"execute_menu_item","params":' + $params + '}'
  Write-Output (Send-Unity $envelope); exit 0
}
if ($Code) {
  $params = @{ action = 'execute'; code = $Code } | ConvertTo-Json -Compress
  $envelope = '{"type":"execute_code","params":' + $params + '}'
  Write-Output (Send-Unity $envelope); exit 0
}
Write-Output 'no action: pass -Ping/-Menu/-Code'; exit 1