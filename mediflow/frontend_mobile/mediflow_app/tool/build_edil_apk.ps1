# Agregado por Edil: APK reproducible para pruebas; sin claves ni llamadas OCI/IA.
[CmdletBinding()]
param(
    [ValidateSet('Usb', 'Emulator', 'Tailnet', 'Release')][string]$Target = 'Usb',
    [string]$ApiBaseUrl = ''
)

$edilAppDir = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
    if ($Target -in @('Tailnet', 'Release')) { throw 'Tailnet/Release requiere una URL HTTPS real del backend; no se usa una URL de ejemplo.' }
    $ApiBaseUrl = if ($Target -eq 'Usb') { 'http://127.0.0.1:8000' } else { 'http://10.0.2.2:8000' }
}
$edilUri = $null
if (-not [Uri]::TryCreate($ApiBaseUrl, [UriKind]::Absolute, [ref]$edilUri) -or
    $edilUri.Scheme -notin @('http', 'https') -or -not $edilUri.Host -or
    $edilUri.UserInfo -or $edilUri.Query -or $edilUri.Fragment) {
    throw 'API_BASE_URL debe ser HTTP/HTTPS sin credenciales, query ni fragmento.'
}
if ($Target -in @('Tailnet', 'Release') -and $edilUri.Scheme -ne 'https') { throw 'Tailnet/Release requiere HTTPS; no se debilita la seguridad Android.' }
if ($Target -eq 'Release') {
    $edilGradle = Get-Content -LiteralPath (Join-Path $edilAppDir 'android/app/build.gradle.kts') -Raw -ErrorAction Stop
    if ($edilGradle -match 'signingConfig\s*=\s*signingConfigs\.getByName\("debug"\)') {
        throw 'La firma release sigue usando la clave debug. Configura firma de distribucion fuera de Git antes de generar un APK final.'
    }
}
$edilFlutterCommand = Get-Command flutter.bat -ErrorAction SilentlyContinue
$edilFlutter = if ($edilFlutterCommand) { $edilFlutterCommand.Source } elseif ($env:FLUTTER_ROOT) {
    Join-Path $env:FLUTTER_ROOT 'bin/flutter.bat'
} else { 'D:\flutter\flutter\bin\flutter.bat' }
if (-not (Test-Path -LiteralPath $edilFlutter)) { throw 'No se encontro Flutter. Configura PATH o FLUTTER_ROOT.' }
$edilOutputDir = Join-Path $edilAppDir 'build/edil-s4'
New-Item -ItemType Directory -Path $edilOutputDir -Force -ErrorAction Stop | Out-Null
$edilName = $Target.ToLowerInvariant()
$edilLog = Join-Path $edilOutputDir ("build-$edilName.log")
$edilVariant = if ($Target -eq 'Release') { '--release' } else { '--debug' }
$edilArgs = @('build', 'apk', $edilVariant, '--no-pub', "--dart-define=API_BASE_URL=$ApiBaseUrl")
Push-Location -LiteralPath $edilAppDir
try {
    & $edilFlutter @edilArgs 2>&1 | Tee-Object -FilePath $edilLog
    $edilExit = $LASTEXITCODE
    if ($edilExit -ne 0) { throw "Flutter termino con codigo $edilExit. Revisa $edilLog" }
} finally { Pop-Location }
$edilSourceName = if ($Target -eq 'Release') { 'app-release.apk' } else { 'app-debug.apk' }
$edilSource = Join-Path $edilAppDir "build/app/outputs/flutter-apk/$edilSourceName"
if (-not (Test-Path -LiteralPath $edilSource)) { throw 'Flutter no genero el archivo APK esperado.' }
$edilArtifact = Join-Path $edilOutputDir "mediflow-s4-$edilName.apk"
Copy-Item -LiteralPath $edilSource -Destination $edilArtifact -ErrorAction Stop
$edilReport = [ordered]@{
    created_at = (Get-Date).ToUniversalTime().ToString('o')
    target = $Target
    build_variant = $edilVariant.TrimStart('-')
    api_base_url = $ApiBaseUrl
    apk = $edilArtifact
    bytes = (Get-Item -LiteralPath $edilArtifact).Length
    sha256 = (Get-FileHash -LiteralPath $edilArtifact -Algorithm SHA256).Hash.ToLowerInvariant()
    tested_on_physical_device = $false
    real_oci_or_gemini_test_executed = $false
    distribution_ready = $false
}
$edilReport | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $edilOutputDir "apk-$edilName.json") -Encoding UTF8 -ErrorAction Stop
Write-Output "APK generado: $edilArtifact"
Write-Output "SHA256: $($edilReport.sha256)"
if ($Target -eq 'Usb') { Write-Output 'Prueba posterior: adb reverse tcp:8000 tcp:8000; instalar APK y comprobar el flujo en el telefono.' }
Write-Output 'La compilacion no demuestra prueba fisica ni procesamiento OCI/Gemini.'
