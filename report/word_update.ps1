param([string]$Src, [string]$DstDocx, [string]$DstPdf)
# Opens a .docx in Microsoft Word (hidden), updates the table of contents and all fields, saves a .docx and exports a PDF.
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open((Resolve-Path $Src).Path, $false, $false)
    foreach ($i in 1..2) {
        $doc.Repaginate()
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        $doc.Fields.Update() | Out-Null
    }
    $doc.Repaginate()
    $dstD = [System.IO.Path]::GetFullPath($DstDocx)
    $dstP = [System.IO.Path]::GetFullPath($DstPdf)
    $doc.SaveAs2($dstD, 12)
    $doc.ExportAsFixedFormat($dstP, 17)
    Write-Output ("pages: " + $doc.ComputeStatistics(2))
    $doc.Close(0)
} finally {
    $word.Quit()
}
