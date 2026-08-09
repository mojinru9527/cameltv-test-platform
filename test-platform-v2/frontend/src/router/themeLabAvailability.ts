export function isThemeLabEnabled(isDevelopment: boolean, explicitFlag?: string): boolean {
  return isDevelopment || explicitFlag === 'true'
}
