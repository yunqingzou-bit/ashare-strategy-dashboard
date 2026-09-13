# Windows 计划任务入口：更新看板并推送（本地兜底方案）
Set-Location (Join-Path $PSScriptRoot '..')
New-Item -ItemType Directory -Force -Path logs | Out-Null
$log = Join-Path 'logs' ('update-' + (Get-Date -Format 'yyyyMMdd') + '.log')
python scripts/update.py --days 45 *>> $log
if ($LASTEXITCODE -ne 0) { Add-Content $log 'STEP FAILED'; exit 1 }
git add docs/index.html
git commit -m ('daily update ' + (Get-Date -Format 'yyyy-MM-dd')) *>> $log
git push *>> $log
exit 0
