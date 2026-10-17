param(
    [string]$BoostRoot = 'D:\NewProgram\librime-rs\target\regex-oracle-cache\boost_1_89_0',
    [string]$OutputDirectory = '',
    [string]$CacheDirectory = '',
    [switch]$AddressSanitizer
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
if (-not $CacheDirectory) { $CacheDirectory = Join-Path $repo 'target/research/icu-probe/reference' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $CacheDirectory 'output' }
$CacheDirectory = [IO.Path]::GetFullPath($CacheDirectory)
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $CacheDirectory, $OutputDirectory | Out-Null
$asset = 'icu4c-77_1-Win64-MSVC2022.zip'
$archive = Join-Path $CacheDirectory $asset
$manifest = Join-Path $CacheDirectory 'SHASUM512.txt'
foreach ($name in @($asset, 'SHASUM512.txt', 'LICENSE')) {
    $path = Join-Path $CacheDirectory $name
    if (-not (Test-Path -LiteralPath $path)) {
        & gh release download release-77-1 --repo unicode-org/icu --pattern $name --dir $CacheDirectory
        if ($LASTEXITCODE -ne 0) { throw "Could not download ICU asset $name" }
    }
}
$hashLine = @(Get-Content -LiteralPath $manifest | Where-Object { $_ -match "\s+\*?$([regex]::Escape($asset))$" })
if ($hashLine.Count -ne 1) { throw 'Cannot identify exactly one archive hash in official manifest' }
$expected = ($hashLine[0] -split '\s+')[0]
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA512).Hash
if ($actual -ne $expected) { throw 'ICU archive SHA512 mismatch' }
$icu = Join-Path $CacheDirectory 'icu77'
if (-not (Test-Path -LiteralPath (Join-Path $icu 'include/unicode/utypes.h'))) {
    Expand-Archive -LiteralPath $archive -DestinationPath $icu
}
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 build tools not found' }
& (Join-Path $vs 'Common7/Tools/Launch-VsDevShell.ps1') -Arch amd64 -HostArch amd64 -SkipAutomaticLocation | Out-Null
$exe = Join-Path $CacheDirectory 'icu-reference.exe'
$object = Join-Path $CacheDirectory 'icu-reference.obj'
$buildLog = Join-Path $CacheDirectory 'build.log'
$argsList = @('/nologo', '/std:c++17', '/EHsc', '/Zi', '/MD', '/utf-8')
if ($AddressSanitizer) { $argsList += '/fsanitize=address' } else { $argsList += '/O2' }
$argsList += @("/Fd$(Join-Path $CacheDirectory 'reference-compiler.pdb')", "/I$BoostRoot", "/I$(Join-Path $icu 'include')", (Join-Path $PSScriptRoot 'probe.cpp'), "/Fo$object", "/Fe$exe", '/link', "/LIBPATH:$(Join-Path $icu 'lib64')", 'icuuc.lib', 'icuin.lib', 'icudt.lib')
& cl.exe @argsList *> $buildLog
if ($LASTEXITCODE -ne 0) { throw "Reference compilation failed; see $buildLog" }
$start = [Diagnostics.ProcessStartInfo]::new($exe)
$start.UseShellExecute = $false
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
$start.Environment['PATH'] = (Join-Path $icu 'bin64') + [IO.Path]::PathSeparator + $env:PATH
$start.ArgumentList.Add($OutputDirectory)
$start.ArgumentList.Add((Join-Path $PSScriptRoot 'cases.tsv'))
$process = [Diagnostics.Process]::Start($start)
$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$process.WaitForExit()
$stdoutTask.Result | Set-Content -LiteralPath (Join-Path $OutputDirectory 'stdout.log') -Encoding UTF8
$stderrTask.Result | Set-Content -LiteralPath (Join-Path $OutputDirectory 'stderr.log') -Encoding UTF8
Write-Output $stdoutTask.Result
if ($process.ExitCode -ne 0) { throw "Reference execution failed: $($process.ExitCode)" }
$emptyExe = Join-Path $CacheDirectory 'empty-probe.exe'
$emptyArgs = @('/nologo', '/std:c++17', '/EHsc', '/O2', '/MD', '/utf-8', "/Fd$(Join-Path $CacheDirectory 'empty-compiler.pdb')", "/I$BoostRoot", "/I$(Join-Path $icu 'include')", (Join-Path $PSScriptRoot 'empty-probe.cpp'), "/Fo$(Join-Path $CacheDirectory 'empty-probe.obj')", "/Fe$emptyExe", '/link', "/LIBPATH:$(Join-Path $icu 'lib64')", 'icuuc.lib', 'icuin.lib', 'icudt.lib')
if ($AddressSanitizer) { $emptyArgs = @('/fsanitize=address', '/Zi') + $emptyArgs }
& cl.exe @emptyArgs *> (Join-Path $CacheDirectory 'empty-build.log')
if ($LASTEXITCODE -ne 0) { throw 'Empty diagnostic compilation failed' }
$diagnostics = @()
foreach ($mode in @('boost_primary', 'boost_identical', 'icu_null', 'icu_nonnull')) {
    $diagnosticStart = [Diagnostics.ProcessStartInfo]::new($emptyExe)
    $diagnosticStart.UseShellExecute = $false
    $diagnosticStart.RedirectStandardOutput = $true
    $diagnosticStart.RedirectStandardError = $true
    $diagnosticStart.Environment['PATH'] = (Join-Path $icu 'bin64') + [IO.Path]::PathSeparator + $env:PATH
    $diagnosticStart.ArgumentList.Add($mode)
    $diagnostic = [Diagnostics.Process]::Start($diagnosticStart)
    $diagnosticOut = $diagnostic.StandardOutput.ReadToEndAsync()
    $diagnosticErr = $diagnostic.StandardError.ReadToEndAsync()
    $diagnostic.WaitForExit()
    $diagnostics += [ordered]@{ mode = $mode; exit_code = $diagnostic.ExitCode; stdout = $diagnosticOut.Result.Trim(); stderr = $diagnosticErr.Result.Trim() }
}
$diagnostics | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'empty-diagnostics.json') -Encoding UTF8
$files = @($archive, $manifest, $exe, (Join-Path $PSScriptRoot 'probe.cpp'), (Join-Path $PSScriptRoot 'cases.tsv'), $PSCommandPath)
$files += @($emptyExe, (Join-Path $PSScriptRoot 'empty-probe.cpp'))
$asanEvidence = Join-Path $CacheDirectory 'asan-output/empty-diagnostics.json'
if (Test-Path -LiteralPath $asanEvidence) { $files += $asanEvidence }
$files += @(Get-ChildItem -LiteralPath (Join-Path $icu 'bin64') -Filter '*.dll' | Select-Object -ExpandProperty FullName)
$files += @(Get-ChildItem -LiteralPath $OutputDirectory -File | Where-Object { $_.Name -ne 'manifest.json' } | Select-Object -ExpandProperty FullName)
$evidence = [ordered]@{
    release = 'https://github.com/unicode-org/icu/releases/tag/release-77-1'
    asset_url = "https://github.com/unicode-org/icu/releases/download/release-77-1/$asset"
    hash_manifest_url = 'https://github.com/unicode-org/icu/releases/download/release-77-1/SHASUM512.txt'
    archive_sha512 = $actual.ToLowerInvariant()
    manifest_sha512_match = $true
    address_sanitizer = [bool]$AddressSanitizer
    os = [Runtime.InteropServices.RuntimeInformation]::OSDescription
    process_architecture = [Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString()
    boost_root = $BoostRoot
    boost_version_header_sha256 = (Get-FileHash -LiteralPath (Join-Path $BoostRoot 'boost/version.hpp') -Algorithm SHA256).Hash.ToLowerInvariant()
    boost_icu_traits_header_sha256 = (Get-FileHash -LiteralPath (Join-Path $BoostRoot 'boost/regex/v5/icu.hpp') -Algorithm SHA256).Hash.ToLowerInvariant()
    generated_utc = [DateTime]::UtcNow.ToString('o')
    files = @($files | ForEach-Object { [ordered]@{ path = $_; bytes = (Get-Item -LiteralPath $_).Length; sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant() } })
}
$evidence | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'manifest.json') -Encoding UTF8
Write-Output "Reference output: $OutputDirectory"
