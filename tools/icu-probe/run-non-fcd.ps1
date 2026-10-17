# Focused research corpus: assumes the locked reference and candidate were built
# using run.ps1. Does not replace the original 24-case reference outputs.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$cache = Join-Path $repo 'target/research/icu-probe'
$output = Join-Path $cache 'non-fcd'
$reference = Join-Path $output 'reference'
$cases = Join-Path $PSScriptRoot 'non-fcd-cases.tsv'
$oracle = Join-Path $cache 'reference/icu-reference.exe'
$candidate = Join-Path $cache 'rust/build/release/icu4x-compat-probe.exe'
foreach ($exe in @($oracle, $candidate)) {
    if (-not (Test-Path -LiteralPath $exe)) { throw "Build the probes using run.ps1 first: $exe" }
}
New-Item -ItemType Directory -Force -Path $reference | Out-Null
$start = [Diagnostics.ProcessStartInfo]::new($oracle)
$start.UseShellExecute = $false
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
$start.Environment['PATH'] = (Join-Path $cache 'reference/icu77/bin64') + [IO.Path]::PathSeparator + $env:PATH
$start.ArgumentList.Add($reference)
$start.ArgumentList.Add($cases)
$process = [Diagnostics.Process]::Start($start)
$stdout = $process.StandardOutput.ReadToEndAsync()
$stderr = $process.StandardError.ReadToEndAsync()
$process.WaitForExit()
$stdout.Result | Set-Content -LiteralPath (Join-Path $output 'reference-stdout.log') -Encoding UTF8
$stderr.Result | Set-Content -LiteralPath (Join-Path $output 'reference-stderr.log') -Encoding UTF8
if ($process.ExitCode -ne 0) { throw 'Non-FCD reference probe failed' }
& $candidate --reference (Join-Path $reference 'codepoints.bin') --summary (Join-Path $output 'candidate-summary.json') --cases $cases --ordering-output (Join-Path $output 'candidate-ordering.tsv')
if ($LASTEXITCODE -ne 0) { throw 'Non-FCD candidate failed' }
& python -B -X utf8 (Join-Path $PSScriptRoot 'compare_ordering.py') --cases $cases --reference (Join-Path $reference 'sortkeys.tsv') --candidate (Join-Path $output 'candidate-ordering.tsv') --output (Join-Path $output 'ordering-summary.json')
$comparisonExit = $LASTEXITCODE
if ($comparisonExit -notin @(0, 1)) { throw 'Non-FCD comparison input invalid' }
$files = @($PSCommandPath, $cases, $oracle, $candidate, (Join-Path $cache 'rust/rustc.txt'), (Join-Path $PSScriptRoot 'rust/Cargo.lock'))
$files += @('icuuc77.dll', 'icuin77.dll', 'icudt77.dll') | ForEach-Object { Join-Path $cache "reference/icu77/bin64/$_" }
$files += @('reference/metadata.json', 'reference/sortkeys.tsv', 'candidate-summary.json', 'candidate-ordering.tsv', 'ordering-summary.json') | ForEach-Object { Join-Path $output $_ }
[ordered]@{
    purpose = 'Non-FCD ordering falsification probe; full Rust sort-key output remains unavailable'
    generated_utc = [DateTime]::UtcNow.ToString('o')
    files = @($files | ForEach-Object { [ordered]@{ path = $_; sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant() } })
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $output 'manifest.json') -Encoding UTF8
exit $comparisonExit
