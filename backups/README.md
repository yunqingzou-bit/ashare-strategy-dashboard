# 每日备份说明

## 备份内容（云端自动，不依赖本机）

| 文件 | 内容 | 生成方式 |
|---|---|---|
| `backups/final-YYYY-MM-DD.json` | 当日全部选股结果（每只标的的评分、子分项、D+1~D+5、事件） | 每日云端任务复制 `data/final.json` |
| `backups/result-YYYY-MM-DD.json` | 当日回放原始结果（含每日统计与基准） | 每日云端任务复制 `data/result.json` |
| `docs/index.html`、`docs/tables.html` | 当日发布的两个页面 | 每次提交都在 git 历史中 |
| `data/industry.json`、`scripts/` | 板块映射与全部代码 | 常驻仓库 |

保留策略：`backups/` 目录只保留最近 180 天（`find -mtime +180 -delete`），更早的仍永久保留在 git 历史里。

## 每日 tag

每次运行会给当天提交打一个 `data-YYYY-MM-DD` 标签，便于按日检出：

```bash
git fetch --tags
git tag -l 'data-*' | tail -5
git checkout data-2026-09-14 -- docs backups   # 取回某天的页面与快照
```

## 恢复方式

```bash
# 只回滚页面：
git checkout <commit> -- docs/index.html docs/tables.html

# 用某天快照重算/对比：
cp backups/final-2026-09-14.json data/final.json
python scripts/build_tables.py

# 从零重建（数据源可公开重取）：
pip install -r requirements.txt
python scripts/update.py --days 45
```

## 本机全量备份（可选，需本机开机）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backup_local.ps1
# 每天 20:00 自动执行：
schtasks /Create /TN "ashare-dashboard-backup" /SC DAILY /ST 20:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\Documents\Codex\2026-09-13\5-9-11\scripts\backup_local.ps1" /F
```

该脚本把整个仓库（含 `data/bars.json`、`data/events/` 等原始数据，约 100 MB）打包到 `backups_local/`，保留最近 30 份。
