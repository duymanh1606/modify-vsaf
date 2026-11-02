# =============================================================================
# confluence-publish.ps1  —  generic Confluence publish for NTAPP-*-to-confluence
# =============================================================================
# Purpose: upload attachments + PUT a page body to a Confluence *Server* instance,
# reading the auth token from a gitignored .confluence-auth file. The AGENT runs
# this via its shell tool during the skill — the user never types a command.
#
# Why this exists: MCP confluence_upload_attachment / _upload_attachments FAIL on
# this Confluence Server (returns success:false / "Failed to upload attachment"),
# even for small pages. Body-only writes via MCP update_page work; ATTACHMENTS do
# not. This script does attachment upload (multipart REST) + the body PUT together
# so the page never sits with a broken macro pointing at a missing attachment.
#
# Auth: reads .confluence-auth (dotenv: CONFLUENCE_BASE_URL, CONFLUENCE_PAT).
# Search order for the auth file: -AuthFile param → walk up from -Manifest dir →
# repo root. Never commit .confluence-auth (it is gitignored).
#
# Usage (agent):
#   powershell -ExecutionPolicy Bypass -File confluence-publish.ps1 -Manifest <manifest.json> [-AuthFile <path>]
#
# manifest.json shape:
# {
#   "pageId": "200737502",
#   "baseUrl": "http://10.254.136.35:8090",         // optional; else from auth file
#   "title": "05.04. KBNV ... (BE-RP-17)",            // inline (preferred). Or "titleFile": "title.txt"
#   "storageFile": "BE-RP-17_srs_confluence.storage.xhtml",  // fixed name (no _vN suffix), rel to manifest dir
#   "versionMessage": "SRS sync ... v3",
#   "attachments": [
#     { "path": "BE-RP-17-activity-flow", "name": "BE-RP-17-activity-flow",
#       "contentType": "application/vnd.jgraph.mxfile", "label": "drawio" },
#     { "path": "BE-RP-17-activity-flow.png", "name": "BE-RP-17-activity-flow.png",
#       "contentType": "image/png", "comment": "BE-RP-17-activity-flow exported to image" }
#   ]
# }
# Paths in the manifest are resolved relative to the manifest file's own directory.
# =============================================================================
param(
    [Parameter(Mandatory=$true)][string]$Manifest,
    [string]$AuthFile
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

if (-not (Test-Path $Manifest)) { throw "Manifest not found: $Manifest" }
$ManifestDir = Split-Path -Parent (Resolve-Path $Manifest)
$M = Get-Content -Raw -Encoding UTF8 $Manifest | ConvertFrom-Json

function Resolve-Rel([string]$p) {
    if ([IO.Path]::IsPathRooted($p)) { return $p }
    return (Join-Path $ManifestDir $p)
}

# --- locate + parse auth file ---
function Find-AuthFile() {
    if ($AuthFile) { if (Test-Path $AuthFile) { return (Resolve-Path $AuthFile) } else { throw "AuthFile not found: $AuthFile" } }
    $dir = $ManifestDir
    while ($dir) {
        $cand = Join-Path $dir '.confluence-auth'
        if (Test-Path $cand) { return $cand }
        $parent = Split-Path -Parent $dir
        if ($parent -eq $dir) { break }
        $dir = $parent
    }
    throw ".confluence-auth NOT FOUND (searched from $ManifestDir up to repo root). Fix: copy .confluence-auth.example -> .confluence-auth and set CONFLUENCE_PAT."
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
$Token   = $auth['CONFLUENCE_PAT']
$BaseUrl = if ($M.baseUrl) { $M.baseUrl } else { $auth['CONFLUENCE_BASE_URL'] }
if (-not $Token -or $Token -eq 'REPLACE_WITH_YOUR_CONFLUENCE_PAT') { throw "CONFLUENCE_PAT not set yet in $authPath (paste your Confluence Personal Access Token there)." }
if (-not $BaseUrl) { throw "CONFLUENCE_BASE_URL missing (set in manifest.baseUrl or auth file)." }
$Headers = @{ Authorization = "Bearer $Token" }
$PageId  = [string]$M.pageId
Write-Host ("Auth: {0}  ·  Base: {1}  ·  Page: {2}" -f (Split-Path -Leaf $authPath), $BaseUrl, $PageId)

function Show-HttpError($err) {
    $r = $err.Exception.Response
    if ($r) { $sr = New-Object IO.StreamReader($r.GetResponseStream()); $b = $sr.ReadToEnd(); $sr.Close(); Write-Host $b -ForegroundColor Yellow }
    else { Write-Host $err.Exception.Message -ForegroundColor Yellow }
}

function Upload-Attachment($Path, $FileName, $ContentType, $Label, $Comment) {
    if (-not (Test-Path $Path)) { throw "Attachment not found: $Path" }
    $enc = [Uri]::EscapeDataString($FileName)
    $listUrl = $BaseUrl + '/rest/api/content/' + $PageId + '/child/attachment?filename=' + $enc
    $existing = $null
    try { $r = Invoke-RestMethod -Method Get -Uri $listUrl -Headers $Headers; if ($r.results.Count -gt 0) { $existing = $r.results[0] } } catch {}

    $boundary = 'NTAPP' + [Guid]::NewGuid().ToString('N')
    $LF = "`r`n"
    $pre  = '--' + $boundary + $LF
    $pre += 'Content-Disposition: form-data; name="file"; filename="' + $FileName + '"' + $LF
    $pre += 'Content-Type: ' + $ContentType + $LF + $LF
    $post = $LF + '--' + $boundary + $LF
    $post += 'Content-Disposition: form-data; name="minorEdit"' + $LF + $LF + 'true' + $LF
    if ($Comment) { $post += '--' + $boundary + $LF + 'Content-Disposition: form-data; name="comment"' + $LF + $LF + $Comment + $LF }
    $post += '--' + $boundary + '--' + $LF

    $preB  = [Text.Encoding]::UTF8.GetBytes($pre)
    $fileB = [IO.File]::ReadAllBytes($Path)
    $postB = [Text.Encoding]::UTF8.GetBytes($post)
    $body  = New-Object byte[] ($preB.Length + $fileB.Length + $postB.Length)
    [Array]::Copy($preB, 0, $body, 0, $preB.Length)
    [Array]::Copy($fileB, 0, $body, $preB.Length, $fileB.Length)
    [Array]::Copy($postB, 0, $body, $preB.Length + $fileB.Length, $postB.Length)

    $h2 = @{}; $Headers.GetEnumerator() | ForEach-Object { $h2[$_.Key] = $_.Value }
    $h2['X-Atlassian-Token'] = 'nocheck'
    $ct = 'multipart/form-data; boundary=' + $boundary
    if ($existing) { $upUrl = $BaseUrl + '/rest/api/content/' + $PageId + '/child/attachment/' + $existing.id + '/data' }
    else           { $upUrl = $BaseUrl + '/rest/api/content/' + $PageId + '/child/attachment' }
    try { $resp = Invoke-RestMethod -Method Post -Uri $upUrl -Headers $h2 -ContentType $ct -Body $body }
    catch { Write-Host ("  UPLOAD FAILED: {0}" -f $FileName) -ForegroundColor Red; Show-HttpError $_; throw }

    $attId = $null
    if ($resp.PSObject.Properties.Name -contains 'results' -and $resp.results) { $attId = $resp.results[0].id }
    if (-not $attId) { $attId = $resp.id }
    Write-Host ("  uploaded: {0}  (id {1})" -f $FileName, $attId)
    if ($Label -and $attId) {
        try {
            $lblUrl  = $BaseUrl + '/rest/api/content/' + $attId + '/label'
            $lblBody = '[{"prefix":"global","name":"' + $Label + '"}]'
            Invoke-RestMethod -Method Post -Uri $lblUrl -Headers $Headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($lblBody)) | Out-Null
            Write-Host ("    + label: {0}" -f $Label)
        } catch { Write-Host ("    (label {0} skipped)" -f $Label) }
    }
}

# --- Step 1: attachments ---
$drawioNames = @()   # names of draw.io diagram attachments (to auto-sync macro revision)
if ($M.attachments) {
    Write-Host ''
    Write-Host ('Step 1/2: uploading {0} attachment(s) ...' -f $M.attachments.Count)
    foreach ($a in $M.attachments) {
        Upload-Attachment (Resolve-Rel $a.path) $a.name $a.contentType $a.label $a.comment
        if ($a.label -eq 'drawio' -or $a.contentType -eq 'application/vnd.jgraph.mxfile') { $drawioNames += [string]$a.name }
    }
} else { Write-Host 'Step 1/2: no attachments.' }

# Read the just-uploaded version of a draw.io attachment (macro `revision` MUST equal it).
function Get-AttachmentVersion($FileName) {
    $enc = [Uri]::EscapeDataString($FileName)
    $u = $BaseUrl + '/rest/api/content/' + $PageId + '/child/attachment?filename=' + $enc + '&expand=version'
    try { $r = Invoke-RestMethod -Method Get -Uri $u -Headers $Headers; if ($r.results.Count -gt 0) { return [int]$r.results[0].version.number } } catch {}
    return $null
}

# --- Step 2: body PUT (version live + 1) ---
$storagePath = Resolve-Rel $M.storageFile
if (-not (Test-Path $storagePath)) { throw "storageFile not found: $storagePath" }
if ($M.title) { $title = [string]$M.title }
elseif ($M.titleFile) { $title = (Get-Content -Raw -Encoding UTF8 (Resolve-Rel $M.titleFile)).TrimEnd("`r","`n") }
else { throw "manifest needs 'title' or 'titleFile'" }

$getUrl = $BaseUrl + '/rest/api/content/' + $PageId + '?expand=version'
$cur    = Invoke-RestMethod -Method Get -Uri $getUrl -Headers $Headers
$curVer = [int]$cur.version.number
$newVer = $curVer + 1
Write-Host ''
Write-Host ('Step 2/2: publishing body  (v{0} -> v{1})' -f $curVer, $newVer)

function Esc([string]$s) {
    $s = $s.Replace('\', '\\').Replace('"', '\"')
    $s = $s.Replace("`r", '\r').Replace("`n", '\n').Replace("`t", '\t')
    return $s
}
$storage = Get-Content -Raw -Encoding UTF8 $storagePath

# --- Auto-sync draw.io macro `revision` to the attachment version we just uploaded. ---
# CRITICAL (SEIBERT draw.io Confluence Server plugin): the macro `revision` param must
# EQUAL the current mxfile attachment version. If revision < version -> the macro shows
# an OLD cached render ("diagram not updated"); if revision > version -> 404 (no such
# revision). Because each publish re-uploads the mxfile (+1 version), we rewrite the
# macro's revision to the freshly-read version so the page always shows the latest diagram.
$syncedAny = $false
foreach ($dn in ($drawioNames | Select-Object -Unique)) {
    $ver = Get-AttachmentVersion $dn
    if (-not $ver) { Write-Host ("  (revision auto-sync skipped: cannot read version of {0})" -f $dn) -ForegroundColor Yellow; continue }
    # Match the drawio macro block that carries this diagramName, rewrite its <revision>.
    $rx = '(?s)(<ac:structured-macro ac:name="drawio".*?<ac:parameter ac:name="diagramName">' +
          [regex]::Escape($dn) + '</ac:parameter>.*?<ac:parameter ac:name="revision">)\d+(</ac:parameter>)'
    $new = [regex]::Replace($storage, $rx, ('${1}' + $ver + '${2}'))
    if ($new -ne $storage) { $storage = $new; $syncedAny = $true; Write-Host ("  revision auto-synced: {0} -> {1}" -f $dn, $ver) }
    else { Write-Host ("  (revision unchanged for {0}; macro/param not found)" -f $dn) -ForegroundColor Yellow }
}
# Persist the corrected revision back to the storage file so repo == live.
if ($syncedAny) { Set-Content -Path $storagePath -Value $storage -Encoding UTF8 -NoNewline }

$msg     = if ($M.versionMessage) { [string]$M.versionMessage } else { 'NTAPP SRS sync' }
$payload = '{"version":{"number":' + $newVer + ',"message":"' + (Esc $msg) + '"},' +
           '"type":"page","title":"' + (Esc $title) + '",' +
           '"body":{"storage":{"value":"' + (Esc $storage) + '","representation":"storage"}}}'
$bytes = [Text.Encoding]::UTF8.GetBytes($payload)
Write-Host ('  body: {0} KB' -f [int]($bytes.Length / 1024))

$putUrl = $BaseUrl + '/rest/api/content/' + $PageId
try { $resp = Invoke-RestMethod -Method Put -Uri $putUrl -Headers $Headers -ContentType 'application/json; charset=utf-8' -Body $bytes }
catch { Write-Host ''; Write-Host '=== SERVER ERROR BODY ===' -ForegroundColor Yellow; Show-HttpError $_; throw }

Write-Host ''
Write-Host ('SUCCESS - new version: {0}' -f $resp.version.number)
Write-Host ('URL: {0}/pages/viewpage.action?pageId={1}' -f $BaseUrl, $PageId)
