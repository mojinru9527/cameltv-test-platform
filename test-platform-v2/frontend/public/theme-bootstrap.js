(() => {
  const defaultTheme = 'obsidian-flow'
  const knownThemes = new Set([
    'cyberpunk',
    'apple',
    'clay',
    'xlab',
    'liquid-glass',
    'obsidian-flow',
  ])
  const legacyThemes = new Map([
    ['blue', 'apple'],
    ['crystal', 'apple'],
    ['dark-minimal', 'xlab'],
    ['warm', 'clay'],
    ['column', 'clay'],
    ['nature', 'clay'],
    ['liquid', 'liquid-glass'],
  ])
  let mode = 'system'
  let colorTheme = defaultTheme

  try {
    const storedMode = localStorage.getItem('cameltv-theme-mode')
    const storedTheme = localStorage.getItem('cameltv-theme-color')
    if (storedMode === 'light' || storedMode === 'dark' || storedMode === 'system') {
      mode = storedMode
    }
    if (storedTheme) {
      const normalizedTheme = knownThemes.has(storedTheme)
        ? storedTheme
        : legacyThemes.get(storedTheme)
      if (normalizedTheme) colorTheme = normalizedTheme
    }
  } catch {
    // Storage can be unavailable in private or hardened browsing modes.
  }

  const isObsidian = colorTheme === 'obsidian-flow'
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  const resolvedMode = isObsidian
    ? 'dark'
    : mode === 'system'
      ? prefersDark ? 'dark' : 'light'
      : mode
  const root = document.documentElement

  root.classList.remove('light', 'dark')
  root.classList.add(resolvedMode)
  root.dataset.theme = colorTheme
  root.dataset.themeId = colorTheme
  if (isObsidian) root.dataset.uiTheme = 'obsidian-flow'
  else delete root.dataset.uiTheme
})()
