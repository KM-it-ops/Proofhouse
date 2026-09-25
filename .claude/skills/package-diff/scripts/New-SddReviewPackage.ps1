# Creates an SDD review package for BASE..HEAD (Windows / PowerShell).
param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$BaseSha,
    [string]$HeadSha = "",
    [Parameter(Mandatory = $true)][string]$OutFile,
    [string]$TaskLabel = "Task"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $RepoRoot)) {
    throw "RepoRoot not found: $RepoRoot"
}

Push-Location $RepoRoot
try {
    git rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Not a git work tree: $RepoRoot" }

    if ([string]::IsNullOrWhiteSpace($HeadSha)) {
        $HeadSha = (git rev-parse HEAD).Trim()
    }

    git merge-base --is-ancestor $BaseSha $HeadSha
    if ($LASTEXITCODE -ne 0) {
        throw "BASE $BaseSha is not an ancestor of HEAD $HeadSha"
    }

    $outDir = Split-Path -Parent $OutFile
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    }

    Set-Content -LiteralPath $OutFile -Value @"
# Review package $TaskLabel
BASE: $BaseSha
HEAD: $HeadSha

## Commits
"@ -Encoding utf8

    git log --oneline "$BaseSha..$HeadSha" | Add-Content -LiteralPath $OutFile -Encoding utf8
    Add-Content -LiteralPath $OutFile -Value "`n## Stat`n" -Encoding utf8
    git diff --stat "$BaseSha..$HeadSha" | Add-Content -LiteralPath $OutFile -Encoding utf8
    Add-Content -LiteralPath $OutFile -Value "`n## Diff`n``````diff`n" -Encoding utf8
    git diff -U10 "$BaseSha..$HeadSha" | Add-Content -LiteralPath $OutFile -Encoding utf8
    Add-Content -LiteralPath $OutFile -Value "``````" -Encoding utf8

    Write-Output $OutFile
}
finally {
    Pop-Location
}
