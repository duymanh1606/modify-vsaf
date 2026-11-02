# =============================================================================
# confluence-get.ps1  —  REST read a Confluence page (Basic auth), fallback for
# NTAPP-srs-to-confluence when the .32 MCP server token is dead.
# =============================================================================
# Purpose: the .32 MCP server token expires (403). When the agent still needs to
# READ .32 (templates / index that live only on .32), it runs this script, which
# authenticates with user/password (Basic) read from the gitignored .confluence-auth.
# Reads default the .32 host block (CONFLUENCE_32_*). GET only — never writes.
#
# Usage (agent):
#   powershell -ExecutionPolicy Bypass -File confluence-get.ps1 -PageId <id> [-AuthFile <path>]
#
# .confluence-auth (.32 block):
#   CONFLUENCE_32_BASE_URL=http://10.254.136.32:8090
#   CONFLUENCE_32_USER=your_username
#   CONFLUENCE_32_PASS=<password>
#
# Output (STDOUT):
#   === VERSION: <n> ===
#   <body.storage XHTML>
# Exit: 0 ok · 3 missing/placeholder cred · 4 http error
# =============================================================================
param(
    [Parameter(Mandatory=$true)][string]$PageId,
    [string]$AuthFile
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

function Find-AuthFile() {
    if ($AuthFile) { if (Test-Path $AuthFile) { return (Resolve-Path $AuthFile) } else { throw "AuthFile not found: $AuthFile" } }
    $dir = (Get-Location).Path
    while ($dir) {
        $cand = Join-Path $dir '.confluence-auth'
        if (Test-Path $cand) { return $cand }
        $parent = Split-Path -Parent $dir
        if ($parent -eq $dir) { break }
        $dir = $parent
    }
    throw ".confluence-auth NOT FOUND (searched from $((Get-Location).Path) up to root)."
}
$authPath = Find-AuthFile
$auth = @{}
foreach ($line in (Get-Content -Encoding UTF8 $authPath)) {
    $t = $line.Trim()
    if ($t -eq '' -or $t.StartsWith('#')) { continue }
    $ix = $t.IndexOf('=')
    if ($ix -lt 1) { continue }
    $auth[$t.Substring(0,$ix).Trim()] = $t.Substring($ix+1).Trim()
}
$BaseUrl = $auth['CONFLUENCE_32_BASE_URL']
$User    = $auth['CONFLUENCE_32_USER']
$Pass    = $auth['CONFLUENCE_32_PASS']
if (-not $BaseUrl -or -not $User -or -not $Pass -or $User -eq 'your_username' -or $Pass -eq 'REPLACE_WITH_32_PASSWORD') {
    Write-Host "CONFLUENCE_32_* not set in $authPath (need BASE_URL + USER + PASS)." -ForegroundColor Yellow
    exit 3
}
$pair  = [Text.Encoding]::UTF8.GetBytes($User + ':' + $Pass)
$basic = [Convert]::ToBase64String($pair)
$Headers = @{ Authorization = 'Basic ' + $basic; 'X-Atlassian-Token' = 'no-check' }

$url = $BaseUrl.TrimEnd('/') + '/rest/api/content/' + $PageId + '?expand=body.storage,version,space'
try {
    $r = Invoke-RestMethod -Method Get -Uri $url -Headers $Headers
} catch {
    Write-Host ("GET FAILED for page {0}: {1}" -f $PageId, $_.Exception.Message) -ForegroundColor Red
    $resp = $_.Exception.Response
    if ($resp) { $sr = New-Object IO.StreamReader($resp.GetResponseStream()); Write-Host $sr.ReadToEnd() -ForegroundColor Yellow; $sr.Close() }
    exit 4
}
Write-Output ("=== VERSION: {0} ===" -f $r.version.number)
Write-Output $r.body.storage.value
