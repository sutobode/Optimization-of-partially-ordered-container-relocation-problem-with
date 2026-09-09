param(
    [switch]$Smoke,
    [switch]$Models,
    [string[]]$PytestArgs = @(),
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs = @()
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$arguments = @((Join-Path $root 'verify.py'))
if ($Smoke) {
    $arguments += '--smoke'
}
if ($Models) {
    $arguments += '--models'
}
$extraArgs = @()
if ($PytestArgs) {
    $extraArgs += $PytestArgs
}
if ($RemainingArgs) {
    $extraArgs += $RemainingArgs
}
if ($extraArgs) {
    $arguments += '--pytest-args'
    $arguments += $extraArgs
}

Push-Location $root
try {
    python @arguments
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
