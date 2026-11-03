param(
    [Parameter(Mandatory)] [string] $HtmlPath,
    [Parameter(Mandatory)] [string] $TextPath
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

$fragment = [System.IO.File]::ReadAllText($HtmlPath, [System.Text.Encoding]::UTF8)
$text = [System.IO.File]::ReadAllText($TextPath, [System.Text.Encoding]::UTF8)

# CF_HTML offsets are UTF-8 byte offsets, so the header is built with fixed-width
# numbers and measured in bytes; a string-based SetData mangles emoji on .NET Framework.
$utf8 = New-Object System.Text.UTF8Encoding($false)
$headerTemplate = "Version:0.9`r`nStartHTML:{0:D10}`r`nEndHTML:{1:D10}`r`nStartFragment:{2:D10}`r`nEndFragment:{3:D10}`r`n"
$prefix = "<html><head><meta charset=`"utf-8`"></head><body><!--StartFragment-->"
$suffix = "<!--EndFragment--></body></html>"

$headerLength = $utf8.GetByteCount(($headerTemplate -f 0, 0, 0, 0))
$startHtml = $headerLength
$startFragment = $startHtml + $utf8.GetByteCount($prefix)
$endFragment = $startFragment + $utf8.GetByteCount($fragment)
$endHtml = $endFragment + $utf8.GetByteCount($suffix)

$cfHtml = ($headerTemplate -f $startHtml, $endHtml, $startFragment, $endFragment) + $prefix + $fragment + $suffix

$data = New-Object System.Windows.Forms.DataObject
$data.SetData([System.Windows.Forms.DataFormats]::Html, (New-Object System.IO.MemoryStream(, $utf8.GetBytes($cfHtml))))
$data.SetData([System.Windows.Forms.DataFormats]::UnicodeText, $text)
[System.Windows.Forms.Clipboard]::SetDataObject($data, $true)

Write-Output 'copied: html+text'
