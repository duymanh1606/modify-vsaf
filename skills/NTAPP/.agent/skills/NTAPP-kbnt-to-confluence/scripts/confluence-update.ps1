# Cap nhat trang KBNT bang REST PUT (body > 150KB nen khong di MCP duoc).
# Khoa lac quan: doc version truoc, chi PUT khi khop -ExpectVersion.
param(
    [Parameter(Mandatory=$true)][string]$StorageFile,
    [Parameter(Mandatory=$true)][string]$PageId,
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][int]$ExpectVersion,
    [string]$VersionComment = 'KBNT sync',
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

$cur = Invoke-RestMethod -Method Get -Uri ($base + '/rest/api/content/' + $PageId + '?expand=version,space') -Headers $h
if ([int]$cur.version.number -ne $ExpectVersion) {
    throw ("KHOA LAC QUAN: version tren trang = " + $cur.version.number + " nhung ky vong " + $ExpectVersion + ". HUY GHI - doc lai trang roi merge.")
}
Write-Output ("version hien tai khop: " + $cur.version.number + "  space=" + $cur.space.key)

$storage = [IO.File]::ReadAllText($StorageFile, [Text.UTF8Encoding]::new($false))
Write-Output ("storage bytes: " + [Text.Encoding]::UTF8.GetByteCount($storage))

$payload = @{
    id      = $PageId
    type    = 'page'
    title   = $Title
    space   = @{ key = $cur.space.key }
    version = @{ number = ($ExpectVersion + 1); message = $VersionComment; minorEdit = $false }
    body    = @{ storage = @{ value = $storage; representation = 'storage' } }
}
$bytes = [Text.Encoding]::UTF8.GetBytes(($payload | ConvertTo-Json -Depth 10 -Compress))

$resp = Invoke-RestMethod -Method Put -Uri ($base + '/rest/api/content/' + $PageId) -Headers $h `
    -ContentType 'application/json; charset=utf-8' -Body $bytes
Write-Output ("UPDATED id=" + $resp.id + " ver=" + $resp.version.number)
Write-Output ("URL=" + $base + "/pages/viewpage.action?pageId=" + $resp.id)
