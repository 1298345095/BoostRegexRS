param(
    [string]$BoostRoot = 'D:\NewProgram\librime-rs\target\regex-oracle-cache\boost_1_89_0'
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$resultRoot = Join-Path $repo 'target/research/icu-probe'
$reference = Join-Path $resultRoot 'reference/output'
$candidate = Join-Path $resultRoot 'rust'
$cases = Join-Path $PSScriptRoot 'reference/cases.tsv'
New-Item -ItemType Directory -Force -Path $candidate | Out-Null
$previousTarget = $env:CARGO_TARGET_DIR
try {
    & pwsh -NoProfile -File (Join-Path $PSScriptRoot 'reference/run.ps1') -BoostRoot $BoostRoot
    if ($LASTEXITCODE -ne 0) { throw 'Reference probe failed' }
    $env:CARGO_TARGET_DIR = Join-Path $candidate 'build'
    & rustc +stable -Vv | Set-Content -LiteralPath (Join-Path $candidate 'rustc.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify stable rustc' }
    & cargo +stable -V | Set-Content -LiteralPath (Join-Path $candidate 'cargo.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify stable cargo' }
    $manifest = Join-Path $PSScriptRoot 'rust/Cargo.toml'
    & cargo +stable tree --locked --manifest-path $manifest | Set-Content -LiteralPath (Join-Path $candidate 'cargo-tree.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve locked candidate dependencies' }
    & cargo +stable run --locked --release --manifest-path $manifest -- --reference (Join-Path $reference 'codepoints.bin') --summary (Join-Path $candidate 'summary.json') --cases $cases --ordering-output (Join-Path $candidate 'ordering.tsv') *> (Join-Path $candidate 'run.log')
    if ($LASTEXITCODE -ne 0) { throw "Rust probe failed; see $candidate/run.log" }
    & python -B -X utf8 (Join-Path $PSScriptRoot 'compare_ordering.py') --cases $cases --reference (Join-Path $reference 'sortkeys.tsv') --candidate (Join-Path $candidate 'ordering.tsv') --output (Join-Path $resultRoot 'ordering-summary.json')
    $comparisonExit = $LASTEXITCODE
    if ($comparisonExit -notin @(0, 1)) { throw 'Ordering comparator failed; inspect ordering-summary.json' }
    $summary = Get-Content -LiteralPath (Join-Path $candidate 'summary.json') -Raw | ConvertFrom-Json
    $differences = @($summary.icu_compat_adapter.PSObject.Properties | Where-Object { $_.Value.mismatches -ne 0 -or $_.Value.unsupported -ne 0 })
    if ($differences.Count -gt 0) { $comparisonExit = 1 }
    Write-Output "Probe results: $resultRoot; exit 1 means observed differences or incomplete reference coverage. Full sort-key compatibility is not validated."
} finally {
    $env:CARGO_TARGET_DIR = $previousTarget
}
exit $comparisonExit
