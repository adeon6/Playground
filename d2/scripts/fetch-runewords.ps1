$ErrorActionPreference = "Stop"

$baseUrl = "https://www.d2r-reimagined.com"
$workspace = Split-Path -Parent $PSScriptRoot
$outputDir = Join-Path $workspace "data"
$outputFile = Join-Path $outputDir "runewords.js"

function Get-Text([string]$Url) {
    return (Invoke-WebRequest -Uri $Url -UseBasicParsing).Content
}

$homepage = Get-Text $baseUrl
$indexMatch = [regex]::Match($homepage, '<script type="module" crossorigin src="([^"]+)"></script>')
if (-not $indexMatch.Success) {
    throw "Could not find the site index script."
}

$indexScriptUrl = [Uri]::new([Uri]$baseUrl, $indexMatch.Groups[1].Value).AbsoluteUri
$indexScript = Get-Text $indexScriptUrl
$chunkMatches = [regex]::Matches($indexScript, 'assets/runewords-[^"''`]+\.js')
$chunkPaths = $chunkMatches | ForEach-Object { $_.Value } | Select-Object -Unique

if (-not $chunkPaths) {
    throw "Could not find any runeword chunks."
}

$jsonText = $null
foreach ($chunkPath in $chunkPaths) {
    $chunkUrl = [Uri]::new([Uri]$baseUrl, $chunkPath).AbsoluteUri
    $chunkSource = Get-Text $chunkUrl
    $jsonMatch = [regex]::Match($chunkSource, 'JSON\.parse\(`([\s\S]*?)`\)')
    if ($jsonMatch.Success) {
        $jsonText = $jsonMatch.Groups[1].Value
        break
    }
}

if (-not $jsonText) {
    throw "Found runeword chunks, but none contained the JSON payload."
}

$runewords = $jsonText | ConvertFrom-Json
$compactJson = $runewords | ConvertTo-Json -Depth 8 -Compress

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
Set-Content -Path $outputFile -Value "window.RUNewordsData = $compactJson;" -Encoding UTF8

Write-Host "Saved $($runewords.Count) runewords to $outputFile"
