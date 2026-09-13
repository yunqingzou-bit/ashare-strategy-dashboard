# 本机全量备份: 打包整个仓库(含原始数据) -> backups_local/, 保留最近30份
Set-Location (Join-Path $PSScriptRoot '..')
$root = $PWD.Path
$name = Split-Path $root -Leaf
$dest = Join-Path $root 'backups_local'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$zip = Join-Path $dest ($name + '-' + $stamp + '.zip')
$tmp = Join-Path $env:TEMP ('bk-' + $stamp)
robocopy $root $tmp /E /XD .git backups_local /NFL /NDL /NJH /NJS /NP | Out-Null
Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -Force
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $dest -Filter *.zip | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 | Remove-Item -Force -ErrorAction SilentlyContinue
$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Output ('backup ok: ' + $zip + ' (' + $mb + ' MB)')
