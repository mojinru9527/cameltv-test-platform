function Get-ExportDigest([string]$MetadataPath) {
    $metadata = Get-Content -LiteralPath $MetadataPath -Raw | ConvertFrom-Json
    $digest = $metadata.'containerimage.config.digest'
    if ($digest -notmatch '^sha256:([0-9a-f]{64})$') {
        throw 'Fresh build metadata is missing a valid image config digest'
    }
    return $Matches[1]
}
