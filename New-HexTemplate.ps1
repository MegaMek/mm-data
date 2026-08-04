# MegaMek Data (C) 2026 by The MegaMek Team is licensed under CC BY-NC-SA 4.0.
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# NOTICE: The MegaMek organization is a non-profit group of volunteers
# creating free software for the BattleTech community.
#
# MechWarrior, BattleMech, `Mech and AeroTech are registered trademarks
# of The Topps Company, Inc. All Rights Reserved.
#
# Catalyst Game Labs and the Catalyst Game Labs logo are trademarks of
# InMediaRes Productions, LLC.
#
# MechWarrior Copyright Microsoft Corporation. MegaMek Data was created under
# Microsoft's "Game Content Usage Rules"
# <https://www.xbox.com/en-US/developers/rules> and it is not endorsed by or
# affiliated with Microsoft.

<#
.SYNOPSIS
    Generates MegaMek hex artwork templates on a transparent background.

.DESCRIPTION
    MegaMek's board view draws hexes flat-top / point-left-right. The reference hex
    image is 84 x 72 (HexTileset.HEX_W / HEX_H) with the polygon defined in
    BoardView.HEX_POLY as (21,0) (62,0) (83,35) (83,36) (62,71) (21,71) (0,36) (0,35).

    This script rasterises the same polygon at any integer multiple of that size.
    All output is written as 32-bit ARGB PNG with a fully transparent background.

    Three files are produced per size:
      hex-outline-<W>x<H>.png   1 px hex outline only - clean tracing guide
      hex-template-<W>x<H>.png  outline plus centre cross and quarter-width guides
      hex-mask-<W>x<H>.png      solid opaque white hex - clipping / alpha mask
                                (the 84 x 72 form of this is data/images/hexes/transparent/HexMask.png)

.PARAMETER Width
    Hex image width in pixels. Default 168 (2x the 84 px reference hex).

.PARAMETER Height
    Hex image height in pixels. Default 144 (2x the 72 px reference hex).

.PARAMETER OutputDirectory
    Directory to write the PNG files into. Created if it does not exist.

.EXAMPLE
    .\New-HexTemplate.ps1 -Width 168 -Height 144 -OutputDirectory .\out
#>

[CmdletBinding()]
param(
    [int] $Width = 168,
    [int] $Height = 144,
    [string] $OutputDirectory = '.'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path -LiteralPath $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
}
$outputRoot = (Resolve-Path -LiteralPath $OutputDirectory).Path

# --- hex geometry -------------------------------------------------------------
# Vertices, in continuous coordinates:
#   (W/4, 0)  (3W/4, 0)  (W, H/2)  (3W/4, H)  (W/4, H)  (0, H/2)
# A pixel belongs to the hex when its CENTRE falls inside the polygon, which is
# what keeps the mask hard-edged (no partial alpha) exactly like HexMask.png.
$halfHeight = $Height / 2.0
$quarterWidth = $Width / 4.0
$epsilon = 1e-9

$inside = New-Object 'bool[][]' $Height
for ($y = 0; $y -lt $Height; $y++) {
    $inside[$y] = New-Object 'bool[]' $Width
    $pixelCentreY = $y + 0.5
    $leftEdgeX = $quarterWidth * [Math]::Abs($halfHeight - $pixelCentreY) / $halfHeight
    $rightEdgeX = $Width - $leftEdgeX
    for ($x = 0; $x -lt $Width; $x++) {
        $pixelCentreX = $x + 0.5
        $inside[$y][$x] = ($pixelCentreX -ge ($leftEdgeX - $epsilon)) -and
                          ($pixelCentreX -le ($rightEdgeX + $epsilon))
    }
}

function Test-Inside {
    param([int] $X, [int] $Y)
    if (($X -lt 0) -or ($Y -lt 0) -or ($X -ge $Width) -or ($Y -ge $Height)) {
        return $false
    }
    return $inside[$Y][$X]
}

# An outline pixel is an inside pixel touching the outside on any of its four sides.
$isOutline = New-Object 'bool[][]' $Height
for ($y = 0; $y -lt $Height; $y++) {
    $isOutline[$y] = New-Object 'bool[]' $Width
    for ($x = 0; $x -lt $Width; $x++) {
        if (-not $inside[$y][$x]) { continue }
        $isOutline[$y][$x] = -not ((Test-Inside ($x - 1) $y) -and (Test-Inside ($x + 1) $y) -and
                                   (Test-Inside $x ($y - 1)) -and (Test-Inside $x ($y + 1)))
    }
}

# --- palette ------------------------------------------------------------------
$transparent = [System.Drawing.Color]::FromArgb(0, 0, 0, 0)
$outlineColour = [System.Drawing.Color]::FromArgb(255, 255, 0, 255)   # magenta - never a terrain colour
$guideColour = [System.Drawing.Color]::FromArgb(170, 0, 190, 190)     # teal, semi transparent
$centreColour = [System.Drawing.Color]::FromArgb(255, 255, 140, 0)    # orange centre crosshair
$maskColour = [System.Drawing.Color]::FromArgb(255, 255, 255, 255)

function New-TransparentBitmap {
    $bitmap = New-Object System.Drawing.Bitmap($Width, $Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    for ($y = 0; $y -lt $Height; $y++) {
        for ($x = 0; $x -lt $Width; $x++) {
            $bitmap.SetPixel($x, $y, $transparent)
        }
    }
    return $bitmap
}

function Test-DashOn {
    param([int] $Position)
    # 4 px on, 4 px off
    return ((([Math]::Floor($Position / 4)) % 2) -eq 0)
}

function Save-Bitmap {
    param([System.Drawing.Bitmap] $Bitmap, [string] $FileName)
    $fullPath = Join-Path $outputRoot $FileName
    $Bitmap.Save($fullPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $Bitmap.Dispose()
    Write-Host ("[OK] {0}" -f $fullPath)
}

# --- 1. mask ------------------------------------------------------------------
$maskBitmap = New-TransparentBitmap
for ($y = 0; $y -lt $Height; $y++) {
    for ($x = 0; $x -lt $Width; $x++) {
        if ($inside[$y][$x]) { $maskBitmap.SetPixel($x, $y, $maskColour) }
    }
}
Save-Bitmap $maskBitmap ("hex-mask-{0}x{1}.png" -f $Width, $Height)

# --- 2. outline only ----------------------------------------------------------
$outlineBitmap = New-TransparentBitmap
for ($y = 0; $y -lt $Height; $y++) {
    for ($x = 0; $x -lt $Width; $x++) {
        if ($isOutline[$y][$x]) { $outlineBitmap.SetPixel($x, $y, $outlineColour) }
    }
}
Save-Bitmap $outlineBitmap ("hex-outline-{0}x{1}.png" -f $Width, $Height)

# --- 3. full template: outline plus guides ------------------------------------
$templateBitmap = New-TransparentBitmap

$centreX = [int] ($Width / 2)
$centreY = [int] ($Height / 2)
$leftQuarterX = [int] ($Width / 4)
$rightQuarterX = $Width - $leftQuarterX - 1

# dashed quarter-width verticals - these mark where the flat top and bottom edges begin
foreach ($guideX in @($leftQuarterX, $rightQuarterX)) {
    for ($y = 0; $y -lt $Height; $y++) {
        if ((Test-DashOn $y) -and $inside[$y][$guideX]) {
            $templateBitmap.SetPixel($guideX, $y, $guideColour)
        }
    }
}

# dashed horizontal centre line - the point-to-point axis
for ($x = 0; $x -lt $Width; $x++) {
    if ((Test-DashOn $x) -and $inside[$centreY][$x]) {
        $templateBitmap.SetPixel($x, $centreY, $guideColour)
    }
}

# dashed vertical centre line
for ($y = 0; $y -lt $Height; $y++) {
    if ((Test-DashOn $y) -and $inside[$y][$centreX]) {
        $templateBitmap.SetPixel($centreX, $y, $guideColour)
    }
}

# solid centre crosshair
$crosshairArm = [Math]::Max(4, [int] ($Width / 24))
for ($offset = -$crosshairArm; $offset -le $crosshairArm; $offset++) {
    if (Test-Inside ($centreX + $offset) $centreY) {
        $templateBitmap.SetPixel($centreX + $offset, $centreY, $centreColour)
    }
    if (Test-Inside $centreX ($centreY + $offset)) {
        $templateBitmap.SetPixel($centreX, $centreY + $offset, $centreColour)
    }
}

# outline drawn last so it always wins over the guides
for ($y = 0; $y -lt $Height; $y++) {
    for ($x = 0; $x -lt $Width; $x++) {
        if ($isOutline[$y][$x]) { $templateBitmap.SetPixel($x, $y, $outlineColour) }
    }
}
Save-Bitmap $templateBitmap ("hex-template-{0}x{1}.png" -f $Width, $Height)

# --- summary ------------------------------------------------------------------
$insidePixelCount = 0
foreach ($row in $inside) { foreach ($cell in $row) { if ($cell) { $insidePixelCount++ } } }
Write-Host ("Hex {0} x {1}: {2} opaque pixels of {3}; column pitch {4} px, row pitch {5} px, odd-column drop {6} px." -f `
    $Width, $Height, $insidePixelCount, ($Width * $Height), ($Width - [int]($Width / 4)), $Height, [int]($Height / 2))
