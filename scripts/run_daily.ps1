# Windows 计划任务入口: 抓数 -> 重建看板 -> 推送 (工作日 18:30)
Set-Location (Join-Path $PSScriptRoot '..')
$repo = $PWD.Path
$ghbin = Join-Path $repo 'local-tools\gh\bin'
if (Test-Path $ghbin) { $env:PATH = $ghbin + ';' + $env:PATH }
New-Item -ItemType Directory -Force -Path logs | Out-Null
$log = Join-Path 'logs' ('update-' + (Get-Date -Format 'yyyyMMdd-HHmm') + '.log')
"[$((Get-Date).ToString('s'))] start" | Out-File -Append -Encoding utf8 $log
python scripts/update.py --days 45 *>> $log
if ($LASTEXITCODE -ne 0) {
  "[$((Get-Date).ToString('s'))] STEP FAILED code=$LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
  exit 1
}
git add docs/index.html 2>&1 | Out-File -Append -Encoding utf8 $log
git commit -m ('daily update ' + (Get-Date -Format 'yyyy-MM-dd')) *>> $log
git push *>> $log
"[$((Get-Date).ToString('s'))] done code=$LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
exit 0
