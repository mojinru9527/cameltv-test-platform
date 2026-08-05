#requires -Version 5.1
<#
api-regression.ps1 — 自包含 CI 回归脚本（Batch 98，替代 V1 envcheck / api run / logagg batch）

子命令:
  health       -BaseUrls "u1,u2"            环境 HTTP 探活（替代 V1 envcheck）
  run          -BaseUrl -AuthToken [-Grep] [-Proxy] [-ReportDir]
                                            执行生成式 Playwright API 测试（替代 V1 api run）
  collect-elk  -JunitPath -ElasticUrl [-KibanaUrl]
                                            解析 JUnit 失败用例 traceId 并输出 ELK 链接（替代 V1 logagg batch）

约束: 仅 PowerShell 内建 cmdlet + 正则；无 Python/第三方依赖；run 前自动安装依赖（有 lockfile 用 npm ci，否则 npm install）。
用法示例:
  pwsh scripts/ci/api-regression.ps1 health -BaseUrls "https://www.camel1.tv/,https://api.cameltv.live/"
  pwsh scripts/ci/api-regression.ps1 run -BaseUrl "https://api.cameltv.live" -AuthToken $env:CAMELTV_AUTH_TOKEN -ReportDir "$env:GITHUB_WORKSPACE/artifacts"
  pwsh scripts/ci/api-regression.ps1 collect-elk -JunitPath "artifacts/api-test-junit.xml" -ElasticUrl $env:ELASTIC_URL -KibanaUrl $env:KIBANA_URL
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("health", "run", "collect-elk")]
    [string]$Command = "",

    [string]$BaseUrls,
    [string]$BaseUrl,
    [string]$AuthToken,
    [string]$Grep,
    [string]$Proxy,
    [string]$ReportDir,
    [string]$JunitPath,
    [string]$ElasticUrl,
    [string]$KibanaUrl
)

$ErrorActionPreference = "Stop"

function Invoke-HealthChecks {
    param([string]$UrlsCsv)
    $urls = @($UrlsCsv -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($urls.Count -eq 0) { throw "health 子命令需要 -BaseUrls" }
    $failures = @()
    foreach ($u in $urls) {
        try {
            $r = Invoke-WebRequest -Uri $u -Method Get -TimeoutSec 15 -MaximumRedirection 3 -UseBasicParsing
            Write-Host "[health] OK   $u -> $($r.StatusCode)"
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            Write-Host "[health] FAIL $u -> $code ($($_.Exception.Message))"
            $failures += $u
        }
    }
    if ($failures.Count -gt 0) {
        Write-Error "[health] $($failures.Count) endpoint(s) failed: $($failures -join ', ')"
        exit 1
    }
    Write-Host "[health] all endpoints healthy"
}

function Invoke-ApiRun {
    param([string]$BaseUrl, [string]$AuthToken, [string]$Grep, [string]$Proxy, [string]$ReportDir)
    if (-not $BaseUrl) { throw "run 子命令需要 -BaseUrl" }

    # 定位生成式测试目录（仓库根 或 任意子目录 cwd 均可；Batch 100 起 v1 已退役）
    $specDir = Join-Path $PWD "tests/api-testing/generated"
    if (-not (Test-Path -LiteralPath (Join-Path $specDir "playwright.config.ts"))) {
        throw "未找到生成式测试目录（期望 playwright.config.ts）: $specDir"
    }

    Push-Location -LiteralPath $specDir
    try {
        if (-not (Test-Path -LiteralPath "node_modules")) {
            if (Test-Path -LiteralPath "package-lock.json") {
                Write-Host "[run] npm ci ..."
                & npm ci 2>&1 | ForEach-Object { Write-Host $_ }
            } else {
                Write-Host "[run] npm install（无 package-lock.json）..."
                & npm install 2>&1 | ForEach-Object { Write-Host $_ }
            }
            if ($LASTEXITCODE -ne 0) { throw "npm 依赖安装失败（exit=$LASTEXITCODE）" }
        }

        # playwright.config.ts 读取的环境变量
        $env:CAMELTV_BASE_URL = $BaseUrl
        $env:CAMELTV_AUTH_TOKEN = if ($AuthToken) { $AuthToken } else { "" }
        if ($Proxy) { $env:HTTP_PROXY = $Proxy } else { Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue }

        $outDir = if ($ReportDir) { $ReportDir } else { Join-Path $specDir "reports" }
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
        $junit = Join-Path $outDir "api-test-junit.xml"
        $json = Join-Path $outDir "api-test-results.json"
        $env:JUNIT_OUTPUT = $junit
        $env:JSON_OUTPUT = $json

        $cmd = @("playwright", "test", "--config=./playwright.config.ts")
        if ($Grep) { $cmd += @("--grep", $Grep) }
        Write-Host "[run] npx $($cmd -join ' ')  (base=$BaseUrl)"
        & npx @cmd
        $code = $LASTEXITCODE
        Write-Host "[run] playwright exit=$code junit=$junit"
        exit $code
    } finally {
        Pop-Location
    }
}

function Invoke-CollectElk {
    param([string]$JunitPath, [string]$ElasticUrl, [string]$KibanaUrl)
    if (-not $JunitPath -or -not (Test-Path -LiteralPath $JunitPath)) {
        throw "collect-elk 子命令需要有效的 -JunitPath"
    }
    [xml]$xml = Get-Content -LiteralPath $JunitPath -Raw
    $traceIds = New-Object System.Collections.Generic.HashSet[string]
    foreach ($tc in $xml.SelectNodes('//testcase')) {
        $failure = $tc.SelectSingleNode('failure')
        if ($failure) {
            $text = $failure.InnerText
            $syserr = $tc.SelectSingleNode('system-err')
            if ($syserr) { $text += [string]$syserr.InnerText }
            foreach ($m in [regex]::Matches($text, 'traceId[:=]\s*([\w-]{8,})')) {
                [void]$traceIds.Add($m.Groups[1].Value)
            }
        }
    }
    if ($traceIds.Count -eq 0) {
        Write-Host "[collect-elk] 失败用例中未提取到 traceId（无 ELK 链接）"
        return
    }
    Write-Host "[collect-elk] 提取到 $($traceIds.Count) 个 traceId："
    foreach ($tid in ($traceIds | Sort-Object)) {
        if ($KibanaUrl) {
            $link = "$KibanaUrl/app/discover#/?_g=(refreshInterval:(pause:!t,value:0))&_a=(query:(language:kuery,query:'traceId:$tid'))"
        } else {
            $link = "$ElasticUrl/_search?q=traceId:$tid"
        }
        Write-Host "  - $tid"
        Write-Host "    $link"
    }
}

switch ($Command) {
    "health"      { Invoke-HealthChecks -UrlsCsv $BaseUrls }
    "run"         { Invoke-ApiRun -BaseUrl $BaseUrl -AuthToken $AuthToken -Grep $Grep -Proxy $Proxy -ReportDir $ReportDir }
    "collect-elk" { Invoke-CollectElk -JunitPath $JunitPath -ElasticUrl $ElasticUrl -KibanaUrl $KibanaUrl }
    default       { throw "用法: api-regression.ps1 health|run|collect-elk [参数]" }
}
