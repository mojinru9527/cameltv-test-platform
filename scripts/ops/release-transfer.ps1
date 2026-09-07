function Send-ReleaseArchive {
    param(
        [Parameter(Mandatory)][string]$KeyPath,
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination
    )
    & scp -i $KeyPath -o BatchMode=yes $Source $Destination
    if ($LASTEXITCODE -ne 0) {
        throw "Release archive upload failed (exit $LASTEXITCODE): $Source"
    }
}

function Wait-ReleaseUploads {
    param([Parameter(Mandatory)][System.Management.Automation.Job[]]$Jobs)
    try {
        $Jobs | Wait-Job | Out-Null
        foreach ($job in $Jobs) {
            $output = Receive-Job $job -ErrorAction Continue 2>&1 | Out-String
            if ($job.State -ne 'Completed') {
                throw "Release archive upload failed: $output"
            }
        }
    } finally {
        $Jobs | Remove-Job -Force
    }
}
