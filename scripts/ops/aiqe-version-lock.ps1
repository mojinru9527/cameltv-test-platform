<#
.SYNOPSIS
  AIQE 版本锁：写入/校验 git commit + 镜像 tag + alembic head。
#>
[CmdletBinding()]
param(
    [ValidateSet("write", "verify")]
    [string]$Action = "verify",
    [string]$RepositoryPath = ".",
    [string]$LockPath = "config/aiqe-version.lock",
    [string]$ImageTag = "",
    [string]$MigrationHead = "unknown",
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"

function Write-LockFile {
    param([string]$Path, [string]$Commit, [string]$Tag, [string]$Head)
    $payload = [ordered]@{
        commit        = $Commit
        image_tag     = $Tag
        migration_head = $Head
        written_at    = (Get-Date).ToUniversalTime().ToString("o")
    }
    $payload | ConvertTo-Json | Set-Content -LiteralPath $Path -Encoding utf8
}

function Test-LockFile {
    param([string]$Path, [string]$ExpectedCommit, [string]$ExpectedTag)
    if (-not (Test-Path -LiteralPath $Path)) { throw "锁文件不存在: $Path" }
    $data = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
    foreach ($field in @("commit", "image_tag", "migration_head", "written_at")) {
        if (-not $data.PSObject.Properties.Name.Contains($field)) {
            throw "锁文件缺少字段: $field"
        }
    }
    if ($ExpectedCommit -and $data.commit -ne $ExpectedCommit) {
        throw "commit 不一致: lock=$($data.commit) repo=$ExpectedCommit"
    }
    if ($ExpectedTag -and $data.image_tag -ne $ExpectedTag) {
        throw "镜像 tag 不一致: lock=$($data.image_tag) expected=$ExpectedTag"
    }
    return $data
}

if ($SelfTest) {
    $temp = Join-Path ([System.IO.Path]::GetTempPath()) ("aiqe-lock-" + [guid]::NewGuid().ToString("N") + ".lock")
    try {
        Write-LockFile -Path $temp -Commit "abc1234" -Tag "release-test" -Head "20261123_ta033_mutation_ledger"
        $data = Test-LockFile -Path $temp -ExpectedCommit "abc1234" -ExpectedTag "release-test"
        if ($data.migration_head -ne "20261123_ta033_mutation_ledger") { throw "head 不匹配" }
        Write-Host "SELFTEST=PASS"
        exit 0
    }
    finally {
        Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
    }
}

$repo = (Resolve-Path -LiteralPath $RepositoryPath).Path
$commit = (& git -C $repo rev-parse --short HEAD).Trim()
$lockFull = if ([System.IO.Path]::IsPathRooted($LockPath)) { $LockPath } else { Join-Path $repo $LockPath }

if ($Action -eq "write") {
    $tag = if ($ImageTag) { $ImageTag } else { "dev-$commit" }
    New-Item -ItemType Directory -Path (Split-Path -Parent $lockFull) -Force | Out-Null
    Write-LockFile -Path $lockFull -Commit $commit -Tag $tag -Head $MigrationHead
    Test-LockFile -Path $lockFull -ExpectedCommit $commit | Out-Null
    Write-Host "AIQE_VERSION_LOCK=WRITTEN commit=$commit tag=$tag head=$MigrationHead"
    exit 0
}

$data = Test-LockFile -Path $lockFull -ExpectedCommit $commit -ExpectedTag $ImageTag
Write-Host "AIQE_VERSION_LOCK=OK commit=$($data.commit) tag=$($data.image_tag) head=$($data.migration_head)"
exit 0
