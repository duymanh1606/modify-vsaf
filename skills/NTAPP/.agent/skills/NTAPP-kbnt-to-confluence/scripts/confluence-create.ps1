# Tao trang KBNT moi tren Confluence .35 bang REST (body 399KB - vuot gioi han MCP).
param(
    [Parameter(Mandatory=$true)][string]$StorageFile,
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][string]$ParentId,
    [string]$SpaceKey = 'TDOV',
    [string]$AuthFile
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (-not $AuthFile) {
    $dir = (Get-Location).Path
    while ($dir) {
        $cand = Join-Path $dir '.confluence-auth'
        if (Test-Path $cand) { $AuthFile = $cand; break }
        $parent = Split-Path -Parent $dir
        if ($parent -eq $dir) { break }
        $dir = $parent
    }
}
if (-not $AuthFile -or -not (Test-Path $AuthFile)) { throw ".confluence-auth NOT FOUND (searched from cwd up to root). Pass -AuthFile explicitly." }

$auth = @{}
foreach ($line in (Get-Content -Encoding UTF8 $AuthFile)) {
    $t = $line.Trim()
    if ($t -eq '' -or $t.StartsWith('#')) { continue }
    $i = $t.IndexOf('=')
    if ($i -lt 1) { continue }
    $auth[$t.Substring(0, $i).Trim()] = $t.Substring($i + 1).Trim()
}
$base = $auth['CONFLUENCE_BASE_URL']
$h = @{ Authorization = 'Bearer ' + $auth['CONFLUENCE_PAT'] }

$storage = [IO.File]::ReadAllText($StorageFile, [Text.UTF8Encoding]::new($false))
Write-Output ("storage bytes: " + ([Text.Encoding]::UTF8.GetByteCount($storage)))

$payload = @{
    type      = 'page'
    title     = $Title
    space     = @{ key = $SpaceKey }
    ancestors = @(@{ id = $ParentId })
    body      = @{ storage = @{ value = $storage; representation = 'storage' } }
}
$json  = $payload | ConvertTo-Json -Depth 10 -Compress
$bytes = [Text.Encoding]::UTF8.GetBytes($json)

$resp = Invoke-RestMethod -Method Post -Uri ($base + '/rest/api/content') -Headers $h `
    -ContentType 'application/json; charset=utf-8' -Body $bytes
Write-Output ("CREATED id=" + $resp.id + " ver=" + $resp.version.number)
Write-Output ("URL=" + $base + "/pages/viewpage.action?pageId=" + $resp.id)
