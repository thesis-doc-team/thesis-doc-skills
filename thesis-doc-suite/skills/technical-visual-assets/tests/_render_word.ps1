
param([string]$Docx,[string]$Pdf)
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($Docx, $false, $true)
  $doc.ExportAsFixedFormat($Pdf, 17)
  $doc.Close([ref]$false)
} finally {
  $word.Quit()
}
