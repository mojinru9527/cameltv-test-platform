/**
 * 通过业务账号服务登录接口换取 {userId, userSig} 鉴权 JSON（v1 平台 auth_token）。
 *
 * 接口（form-data）：
 *   POST ${CAMELTV_LOGIN_URL}
 *   countryCode=86&mobile=<手机号>&password=<密码>
 *
 * 环境变量：
 *   CAMELTV_USERNAME      手机号（本地号，不带 +86）
 *   CAMELTV_PASSWORD      密码
 *   CAMELTV_COUNTRY_CODE  国家码，默认 +86（脚本自动去掉 + 号）
 *   CAMELTV_LOGIN_URL     登录接口完整地址（必填）
 *
 * 输出：{userId,userSig} 的 JSON 字符串（原样作为 Authorization: Bearer 值）。
 * 凭据只从进程环境读取；失败时退出码非 0，错误信息不含凭据值。
 */

function getCredentials() {
  const username = process.env.CAMELTV_USERNAME?.trim() ?? ''
  const password = process.env.CAMELTV_PASSWORD ?? ''
  const loginUrl = process.env.CAMELTV_LOGIN_URL?.trim() ?? ''
  if (!username || !password || !loginUrl) {
    const missing = [
      username ? '' : 'CAMELTV_USERNAME',
      password ? '' : 'CAMELTV_PASSWORD',
      loginUrl ? '' : 'CAMELTV_LOGIN_URL',
    ].filter(Boolean)
    throw new Error(`[auth] missing env: ${missing.join(', ')}`)
  }
  return {
    username,
    password,
    loginUrl,
    countryCode: (process.env.CAMELTV_COUNTRY_CODE?.trim() || '+86').replace(/^\+/, ''),
  }
}

/** 递归查找 {userId,userSig} 对象；找不到返回 null。 */
function findToken(node) {
  if (!node) return null
  if (typeof node === 'string') {
    const text = node.trim()
    if (text.startsWith('{') && text.includes('userSig')) {
      try {
        const parsed = JSON.parse(text)
        if (parsed && parsed.userId && parsed.userSig) {
          return JSON.stringify({ userId: parsed.userId, userSig: parsed.userSig })
        }
      } catch {
        // 继续走普通字符串分支
      }
      return null
    }
    return null
  }
  if (Array.isArray(node)) {
    for (const item of node) {
      const hit = findToken(item)
      if (hit) return hit
    }
    return null
  }
  if (typeof node === 'object') {
    if (node.userId && node.userSig) {
      return JSON.stringify({ userId: node.userId, userSig: node.userSig })
    }
    for (const value of Object.values(node)) {
      const hit = findToken(value)
      if (hit) return hit
    }
  }
  return null
}

async function main() {
  const { username, password, loginUrl, countryCode } = getCredentials()

  const body = new URLSearchParams({
    countryCode,
    mobile: username,
    password,
  })

  let response
  try {
    response = await fetch(loginUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
      redirect: 'follow',
    })
  } catch (error) {
    throw new Error(`[auth] request failed: ${error instanceof Error ? error.message : String(error)}`)
  }

  const text = await response.text()
  if (!response.ok) {
    throw new Error(`[auth] login http ${response.status}: ${text.slice(0, 200)}`)
  }

  let parsed
  try {
    parsed = JSON.parse(text)
  } catch {
    parsed = text
  }

  const token = findToken(parsed)
  if (!token) {
    const shape =
      typeof parsed === 'object' && parsed !== null
        ? Object.keys(parsed).join(',')
        : typeof parsed
    throw new Error(`[auth] token not found in response (top-level keys: ${shape})`)
  }

  process.stdout.write(`${token}\n`)
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`)
  process.exit(1)
})
