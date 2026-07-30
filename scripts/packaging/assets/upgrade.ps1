#Requires -Version 5.0
<#
.SYNOPSIS
  From the portable deploy root: fetch latest GitHub Release zip for this OS/arch,
  stop catalog-service, merge-extract (never overwrite existing .env).
#>
[CmdletBinding()]
param(
    [Alias("y")]
    [switch]$Yes,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

foreach ($a in @($ExtraArgs)) {
    if ($a -in @("-y", "--yes", "-Yes", "/y", "/yes")) {
        $Yes = $true
    }
}

$ErrorActionPreference = "Stop"
$DeployRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $DeployRoot

$DefaultRepo = "0x00pluto/material-tags-catalog-service"
$Repo = if ($env:CATALOG_UPDATE_REPO) { $env:CATALOG_UPDATE_REPO.Trim() } else { $DefaultRepo }
$Token = if ($env:GITHUB_TOKEN) { $env:GITHUB_TOKEN } elseif ($env:GH_TOKEN) { $env:GH_TOKEN } else { $null }

function Get-OsArch {
    $os = "windows"
    $archRaw = $env:PROCESSOR_ARCHITECTURE
    if (-not $archRaw) {
        $archRaw = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    }
    $archRaw = $archRaw.ToLowerInvariant()
    if ($archRaw -in @("amd64", "x86_64", "x64")) {
        $arch = "amd64"
    }
    elseif ($archRaw -in @("arm64", "aarch64")) {
        $arch = "arm64"
    }
    else {
        throw "Unsupported arch: $archRaw"
    }
    return @{ Os = $os; Arch = $arch }
}

function Get-LocalVersion {
    $exe = Join-Path $DeployRoot "catalog-service\catalog-service.exe"
    if (-not (Test-Path $exe)) { return $null }
    try {
        $out = & $exe --version 2>&1 | Out-String
        $m = [regex]::Match($out, "(\d+\.\d+\.\d+(?:[+][^\s]+)?)")
        if ($m.Success) { return $m.Groups[1].Value.Trim() }
    }
    catch { }
    return $null
}

function Get-ApiHeaders {
    $h = @{
        "Accept"     = "application/vnd.github+json"
        "User-Agent" = "material-tags-catalog-upgrade"
    }
    if ($Token) {
        $h["Authorization"] = "Bearer $Token"
    }
    return $h
}

function Find-Asset([object]$Release, [string]$Os, [string]$Arch) {
    $suffix = "-$Os-$Arch.zip"
    $prefix = "material-tags-catalog-"
    foreach ($a in $Release.assets) {
        $name = [string]$a.name
        if ($name.StartsWith($prefix) -and $name.EndsWith($suffix)) {
            $mid = $name.Substring($prefix.Length, $name.Length - $prefix.Length - $suffix.Length)
            if ($mid.Length -gt 0) {
                return @{
                    Name               = $name
                    BrowserDownloadUrl = [string]$a.browser_download_url
                    Version            = $mid
                }
            }
        }
    }
    return $null
}

function Stop-CatalogService {
    Write-Host "Stopping catalog-service (if running) ..."
    Get-Process -Name "catalog-service" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

function Backup-Env {
    $envPath = Join-Path $DeployRoot ".env"
    if (Test-Path $envPath) {
        $bak = Join-Path $DeployRoot ".env.bak.upgrade"
        Copy-Item -Force $envPath $bak
        Write-Host "Backed up .env -> .env.bak.upgrade"
    }
}

function Merge-FromPackageDir([string]$PackageDir) {
    $preserveEnv = Test-Path (Join-Path $DeployRoot ".env")
    Get-ChildItem -Force -LiteralPath $PackageDir | ForEach-Object {
        if ($_.Name -eq ".env" -and $preserveEnv) {
            Write-Host "Skip existing .env"
            return
        }
        $dest = Join-Path $DeployRoot $_.Name
        if ($_.PSIsContainer) {
            if (-not (Test-Path $dest)) {
                New-Item -ItemType Directory -Path $dest | Out-Null
            }
            & robocopy $_.FullName $dest /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
            # robocopy: 0-7 success
            if ($LASTEXITCODE -ge 8) {
                throw "robocopy failed merging $($_.Name) (code=$LASTEXITCODE)"
            }
            $global:LASTEXITCODE = 0
        }
        else {
            Copy-Item -Force -LiteralPath $_.FullName -Destination $dest
        }
    }
}

$plat = Get-OsArch
$Os = $plat.Os
$Arch = $plat.Arch
Write-Host "Deploy root: $DeployRoot"
Write-Host "Platform: $Os-$Arch"
Write-Host "Repo: $Repo"

$apiUrl = "https://api.github.com/repos/$Repo/releases/latest"
Write-Host "Fetching $apiUrl ..."
$headers = Get-ApiHeaders
try {
    $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Get
}
catch {
    Write-Error "Failed to fetch latest release: $_"
    exit 1
}

$asset = Find-Asset $release $Os $Arch
if (-not $asset) {
    Write-Error "No asset matching material-tags-catalog-*-$Os-$Arch.zip in latest release '$($release.tag_name)'."
    exit 1
}

$remoteVersion = $asset.Version
$localVersion = Get-LocalVersion
Write-Host "Remote: $($asset.Name) (version=$remoteVersion)"
Write-Host "Local version: $(if ($localVersion) { $localVersion } else { '(unknown)' })"

if ($localVersion -and ($localVersion -eq $remoteVersion)) {
    Write-Host "Already up to date ($localVersion). Nothing to do."
    exit 0
}

if (-not $Yes) {
    $ans = Read-Host "Download and merge-upgrade to $($asset.Name)? [y/N]"
    if ($ans -notmatch '^[Yy]$') {
        Write-Host "Cancelled."
        exit 0
    }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mtc-upgrade-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
$zipPath = Join-Path $tempRoot $asset.Name
$extractDir = Join-Path $tempRoot "extract"

try {
    Stop-CatalogService
    Backup-Env

    Write-Host "Downloading $($asset.BrowserDownloadUrl) ..."
    $dlHeaders = Get-ApiHeaders
    Invoke-WebRequest -Uri $asset.BrowserDownloadUrl -Headers $dlHeaders -OutFile $zipPath -UseBasicParsing

    Write-Host "Extracting ..."
    New-Item -ItemType Directory -Path $extractDir | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

    $topDirs = @(Get-ChildItem -Directory -LiteralPath $extractDir)
    if ($topDirs.Count -ne 1) {
        throw "Expected exactly one top-level directory in zip, found $($topDirs.Count)."
    }
    $packageDir = $topDirs[0].FullName
    Write-Host "Merging from $packageDir ..."
    Merge-FromPackageDir $packageDir

    Write-Host ""
    Write-Host "Upgrade files merged. .env was preserved if present."
    Write-Host "Next: double-click start.bat, then open http://127.0.0.1:8787/health and check version=$remoteVersion"
    exit 0
}
catch {
    Write-Error "Upgrade failed: $_"
    exit 1
}
finally {
    if (Test-Path $tempRoot) {
        Remove-Item -Recurse -Force $tempRoot -ErrorAction SilentlyContinue
    }
}
