param(
  [string]$BoostRoot = 'D:\NewProgram\librime-rs\target\regex-oracle-cache\boost_1_89_0',
  [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
  $OutputDirectory = Join-Path (Resolve-Path (Join-Path $PSScriptRoot '../../../..')) 'target/research/benchmark'
}
$outDir = $OutputDirectory
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$installation = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
& (Join-Path $installation 'Common7\Tools\Launch-VsDevShell.ps1') -Arch amd64 -HostArch amd64 -SkipAutomaticLocation | Out-Null
$source = Join-Path $PSScriptRoot 'boost-bench.cpp'
$binary = Join-Path $outDir 'boost-bench.exe'
$object = Join-Path $outDir 'boost-bench.obj'
& cl /nologo /O2 /Ob2 /DNDEBUG /EHsc /std:c++17 /DBOOST_REGEX_NO_LIB /utf-8 /W4 /I $BoostRoot $source "/Fo:$object" "/Fe:$binary" 2>&1 | Out-File -LiteralPath (Join-Path $outDir 'build.log') -Encoding UTF8
if ($LASTEXITCODE -ne 0) { throw "compilation failed; see $outDir/build.log" }
# The C++ metadata stream contains ASCII only.
& $binary 2> (Join-Path $outDir 'metadata.txt') | Out-File -LiteralPath (Join-Path $outDir 'results.csv') -Encoding UTF8
if ($LASTEXITCODE -ne 0) { throw "benchmark failed; see $outDir/metadata.txt" }
Get-Content -LiteralPath (Join-Path $outDir 'results.csv') -Encoding UTF8
