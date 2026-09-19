param(
    [string]$MegaMekRoot = (Join-Path $PSScriptRoot '..\..\megamek_temp'),
    [string]$Blender = '',
    [switch]$Preview
)
$ErrorActionPreference = 'Stop'
$dataRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$codeRoot = (Resolve-Path $MegaMekRoot).Path
if (-not $Blender) {
    $command = Get-Command blender -ErrorAction SilentlyContinue
    if ($command) {
        $Blender = $command.Source
    } else {
        $installation = Get-ChildItem -Path (Join-Path $env:ProgramFiles 'Blender Foundation\Blender*\blender.exe') |
            Sort-Object FullName -Descending | Select-Object -First 1
        if (-not $installation) { throw 'Pass -Blender with the Blender executable path.' }
        $Blender = $installation.FullName
    }
}
& (Join-Path $codeRoot 'gradlew.bat') -p $codeRoot "-PunitModelDataRoot=$dataRoot" :megamek:exportMekModelCatalog --console=plain
if ($LASTEXITCODE -ne 0) { throw 'MegaMek catalog export failed.' }
$buildArguments = @('--background', '--factory-startup', '--python-exit-code', '1', '--python',
    (Join-Path $PSScriptRoot 'build_unit_models.py'), '--')
if ($Preview) { $buildArguments += '--preview' }
& $Blender @buildArguments
if ($LASTEXITCODE -ne 0) { throw 'Unit model generation failed.' }
# Blender includes Python; use it to validate so no separate Python/Pillow install is needed.
& $Blender --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'validate_unit_models.py') --
if ($LASTEXITCODE -ne 0) { throw 'Unit model validation failed.' }
Write-Output "Validated unit models: $(Join-Path $dataRoot 'data\models\units')"
