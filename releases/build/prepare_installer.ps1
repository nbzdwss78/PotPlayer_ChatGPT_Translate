param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$BuildDir = $PSScriptRoot,
    [string]$ReleaseSuffix = '',
    [string]$VersionOverride = ''
)

$ErrorActionPreference = 'Stop'

function Get-PluginVersion {
    param([string]$Root)

    try {
        $version = git -C $Root describe --tags --abbrev=0 2>$null
        if (-not [string]::IsNullOrWhiteSpace($version)) {
            $version = $version.Trim()
            if ($version.StartsWith('v')) {
                return $version.Substring(1)
            }
            return $version
        }
    } catch {
    }

    return '1.9.2'
}

function Escape-CppWideString {
    param([string]$Value)

    $escaped = $Value.Replace('\', '\\').Replace('"', '\"').Replace("`r", '').Replace("`n", '\n')
    return 'L"' + $escaped + '"'
}

function Escape-CppString {
    param([string]$Value)

    $escaped = $Value.Replace('\', '\\').Replace('"', '\"').Replace("`r", '').Replace("`n", '\n')
    return '"' + $escaped + '"'
}

$generatedDir = Join-Path $BuildDir 'generated'
New-Item -ItemType Directory -Path $generatedDir -Force | Out-Null

$version = if ([string]::IsNullOrWhiteSpace($VersionOverride)) { Get-PluginVersion -Root $ProjectRoot } else { $VersionOverride.Trim() }
$releaseSuffixNormalized = [string]$ReleaseSuffix
if (-not [string]::IsNullOrWhiteSpace($releaseSuffixNormalized)) {
    if (-not $releaseSuffixNormalized.StartsWith('-')) {
        $releaseSuffixNormalized = '-' + $releaseSuffixNormalized
    }
    $version += $releaseSuffixNormalized
}
$languagePath = Join-Path $BuildDir 'language_strings.json'
$tokenLimitsPath = Join-Path $BuildDir 'model_token_limits.json'

$languageJson = Get-Content -LiteralPath $languagePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($lang in @('en', 'zh')) {
    $langObject = $languageJson.$lang
    foreach ($property in $langObject.PSObject.Properties) {
        $property.Value = ([string]$property.Value).Replace('{VERSION}', $version)
    }
}

$tokenLimitsCompressed = (
    Get-Content -LiteralPath $tokenLimitsPath -Raw -Encoding UTF8 |
    ConvertFrom-Json |
    ConvertTo-Json -Depth 100 -Compress
)

$header = New-Object System.Text.StringBuilder
[void]$header.AppendLine('#pragma once')
[void]$header.AppendLine('#include <string>')
[void]$header.AppendLine('#include <unordered_map>')
[void]$header.AppendLine()
[void]$header.AppendLine('inline constexpr wchar_t kPluginVersion[] = ' + (Escape-CppWideString $version) + ';')
[void]$header.AppendLine()
[void]$header.AppendLine('inline const std::unordered_map<std::wstring, std::unordered_map<std::wstring, std::wstring>> kLanguageStrings = {')
foreach ($lang in @('en', 'zh')) {
    [void]$header.AppendLine('    {' + (Escape-CppWideString $lang) + ', {')
    foreach ($property in $languageJson.$lang.PSObject.Properties) {
        [void]$header.AppendLine('        {' + (Escape-CppWideString $property.Name) + ', ' + (Escape-CppWideString ([string]$property.Value)) + '},')
    }
    [void]$header.AppendLine('    }},')
}
[void]$header.AppendLine('};')
[void]$header.AppendLine()
[void]$header.AppendLine('inline const std::string kModelTokenLimitsJson = ' + (Escape-CppString $tokenLimitsCompressed) + ';')

$headerPath = Join-Path $generatedDir 'installer_generated.h'
Set-Content -LiteralPath $headerPath -Value $header.ToString() -Encoding utf8

Write-Host "Generated $headerPath with version $version"
