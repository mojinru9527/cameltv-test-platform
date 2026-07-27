#!/usr/bin/env groovy
/**
 * CamelTv 测试平台 — Jenkins CI 集成函数库
 *
 * 用法: 将此文件加载为 Jenkins Shared Library，或直接复制到 pipeline 中
 *
 * 环境变量:
 *   CAMELTV_API_BASE  — 测试平台 API 地址 (如 https://test.cameltv.com/api/v1)
 *   CAMELTV_API_TOKEN — API Token (tpat_xxx)
 */

/**
 * 触发测试计划执行
 * @param planId 测试计划 ID
 * @return Map { triggerResult, runIds }
 */
def triggerPlan(int planId) {
    def apiBase = env.CAMELTV_API_BASE ?: 'http://localhost:8000/api/v1'

    // 1) Health check
    def healthResp = httpRequest(
        url: "${apiBase}/open/health",
        validResponseCodes: '200',
        quiet: true
    )
    def health = readJSON(text: healthResp.content)
    if (health.data?.status != 'ok') {
        error("CamelTv API 不可达")
    }
    echo "✅ CamelTv API v${health.data.version} 可达"

    // 2) Trigger
    def triggerResp = httpRequest(
        url: "${apiBase}/open/plans/${planId}/trigger",
        httpMode: 'POST',
        customHeaders: [[name: 'Authorization', value: "Bearer ${env.CAMELTV_API_TOKEN}"]],
        validResponseCodes: '200',
        quiet: false
    )
    def trigger = readJSON(text: triggerResp.content)
    echo "🚀 触发计划「${trigger.data.plan_name}」，入队 ${trigger.data.cases_queued} 条用例"

    return [triggerResult: trigger.data]
}

/**
 * 轮询等待执行结果（阻塞直到所有用例终态）
 * @param runId 执行记录 ID
 * @param timeoutSeconds 最大等待时间（秒），默认 300
 * @return Map { status, actual_result, trace_id, executed_at }
 */
def pollRun(int runId, int timeoutSeconds = 300) {
    def apiBase = env.CAMELTV_API_BASE ?: 'http://localhost:8000/api/v1'
    def startTime = System.currentTimeMillis()
    def terminalStatuses = ['pass', 'fail', 'skip', 'block']

    while (true) {
        def resp = httpRequest(
            url: "${apiBase}/open/runs/${runId}",
            customHeaders: [[name: 'Authorization', value: "Bearer ${env.CAMELTV_API_TOKEN}"]],
            validResponseCodes: '200,404',
            quiet: true
        )
        def run = readJSON(text: resp.content)

        if (resp.status == 404) {
            error("执行记录 ${runId} 不存在")
        }

        def status = run.data.status
        echo "  run #${runId}: ${status}"

        if (terminalStatuses.contains(status)) {
            return run.data
        }

        if ((System.currentTimeMillis() - startTime) / 1000 > timeoutSeconds) {
            error("执行 #${runId} 超时 (${timeoutSeconds}s)")
        }

        sleep(5)  // Poll every 5s
    }
}

/**
 * 回写执行结果
 * @param runId 执行记录 ID
 * @param status 状态: pass/fail/skip/block
 * @param actualResult 实际结果描述
 * @param traceId ELK trace ID (可选)
 * @param notes 备注 (可选)
 */
def postResult(int runId, String status, String actualResult = '', String traceId = '', String notes = '') {
    def apiBase = env.CAMELTV_API_BASE ?: 'http://localhost:8000/api/v1'

    def body = [
        run_id: runId,
        status: status,
        actual_result: actualResult,
        trace_id: traceId,
        notes: notes ?: "Jenkins build ${env.BUILD_NUMBER}"
    ]

    def resp = httpRequest(
        url: "${apiBase}/open/results",
        httpMode: 'POST',
        requestBody: groovy.json.JsonOutput.toJson(body),
        customHeaders: [
            [name: 'Authorization', value: "Bearer ${env.CAMELTV_API_TOKEN}"],
            [name: 'Content-Type', value: 'application/json']
        ],
        validResponseCodes: '200',
        quiet: true
    )
    def result = readJSON(text: resp.content)
    echo "📝 run #${runId} → ${status}"
    return result.data
}
