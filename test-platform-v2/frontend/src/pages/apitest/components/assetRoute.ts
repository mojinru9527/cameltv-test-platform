export interface AssetRouteParts {
  modulePath: string
  endpointPath: string
}

function segments(value: string): string[] {
  return String(value || '').split('/').map((part) => part.trim()).filter(Boolean)
}

function asPath(parts: string[], fallback = ''): string {
  return parts.length ? `/${parts.join('/')}` : fallback
}

export function splitAssetRoute(
  serviceName: string,
  storedModule: string,
  storedPath: string,
): AssetRouteParts {
  const service = serviceName.trim().replace(/^\/+|\/+$/g, '')
  const moduleParts = segments(storedModule)
  let pathParts = segments(storedPath)

  if (pathParts[0] === service) pathParts = pathParts.slice(1)

  if (storedModule.trim().startsWith('/') && moduleParts.length) {
    const beginsWithModule = moduleParts.every((part, index) => pathParts[index] === part)
    const endpointParts = beginsWithModule ? pathParts.slice(moduleParts.length) : pathParts
    return {
      modulePath: asPath(moduleParts, '/default'),
      endpointPath: asPath(endpointParts, '/'),
    }
  }

  if (pathParts.length >= 3) {
    return {
      modulePath: asPath(pathParts.slice(0, 2)),
      endpointPath: asPath(pathParts.slice(2)),
    }
  }
  if (pathParts.length === 2) {
    return {
      modulePath: asPath(pathParts.slice(0, 1)),
      endpointPath: asPath(pathParts.slice(1)),
    }
  }

  return {
    modulePath: asPath(moduleParts, '/default'),
    endpointPath: asPath(pathParts, '/'),
  }
}

export function composeAssetUrl(
  baseUrl: string,
  serviceName: string,
  modulePath: string,
  endpointPath: string,
): string {
  const base = baseUrl.trim().replace(/\/+$/g, '')
  if (!base) return ''

  const serviceParts = segments(serviceName)
  const routeParts = [...segments(modulePath), ...segments(endpointPath)]
  const service = serviceParts[serviceParts.length - 1] || ''
  const baseLast = (() => {
    try {
      const parsed = new URL(base)
      const parts = segments(parsed.pathname)
      return parts[parts.length - 1] || ''
    } catch {
      const parts = segments(base)
      return parts[parts.length - 1] || ''
    }
  })()
  const fullParts = baseLast === service ? routeParts : [...serviceParts, ...routeParts]
  return `${base}/${fullParts.join('/')}`
}

export function displayAssetSegment(value: string): string {
  return segments(value).join('-') || '未分类'
}
