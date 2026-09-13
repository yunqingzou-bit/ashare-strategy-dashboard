# A股选股策略回测看板

收盘后自动回放「涨幅/成交额/换手/涨停」候选池 + 六维评分选股模型，生成桌面与移动端自适应的单页看板，并部署到 GitHub Pages。

## 目录结构

```
scripts/
  fetch.py        抓全市场前复权日线(同花顺) + 每日涨停池/龙虎榜/公告(东方财富, 按日缓存)
  replay.py       逐日回放选股模型, 输出每日前5只与D+1..D+5走势
  report.py       生成逐只明细与5日内事件(龙虎榜/公告/涨跌停)
  build_site.py   渲染响应式单页看板 -> docs/index.html
  update.py       一键编排: fetch -> replay -> report -> build_site
  run_daily.ps1   Windows 计划任务入口(本地兜底: 更新后自动 git push)
  assets/         样式与交互(dash.css / dash_add.css / dash2.js)
data/             运行期数据(默认 gitignore); industry.json 为板块映射, 需提交
docs/             GitHub Pages 发布目录(index.html + .nojekyll)
.github/workflows/daily.yml   云端定时任务(工作日 10:30 UTC = 18:30 北京时间)
```

## 本地运行

```bash
pip install -r requirements.txt
python scripts/update.py --days 45
# 产物: docs/index.html  (直接双击打开即可)
```

参数：`--days N` 回放窗口(默认45个交易日)；`--skip-fetch` 跳过抓取仅重建页面。

## 部署到 GitHub Pages

```bash
git init -b main
git add .
git commit -m "init: dashboard"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

推送后：仓库 Settings → Pages → Source 选择 **Deploy from a branch** → 分支 `main`、目录 `/docs` → Save。
约 1 分钟后访问 `https://<用户名>.github.io/<仓库名>/`。

## 每日自动更新（两种方案，任选其一）

| 方案 | 触发 | 优点 | 注意 |
|---|---|---|---|
| A. GitHub Actions | `.github/workflows/daily.yml`，工作日 18:30(北京) | 不依赖本机开机 | 云端 runner 访问同花顺/东财可能被限流；首次成功后会缓存 `data/events` 加速 |
| B. Windows 计划任务 | `scripts/run_daily.ps1` | 数据源在本机已验证可用 | 需要本机开机并已配置 git 凭据 |

方案 B 创建任务（工作日 18:30，任务名用 ASCII 避免中文编码问题）：

```powershell
schtasks /Create /TN "ashare-dashboard-daily" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 18:30 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File <仓库路径>\scripts\run_daily.ps1"
schtasks /Run /TN "ashare-dashboard-daily"   # 立即跑一次验证
schtasks /Query /TN "ashare-dashboard-daily" /V /FO LIST
```

## 数据源与口径

| 数据 | 来源 |
|---|---|
| 全市场前复权日线 | 同花顺 `d.10jqka.com.cn` |
| 涨停池/炸板池/强势股池 | 东方财富 `push2ex`（历史可回溯约 3 周） |
| 龙虎榜（净买额/席位解读） | 东方财富数据中心 |
| 公告（按关键词筛选） | 东方财富公告接口 |
| 行业板块映射 | 新浪行业（49 类）+ 本地 `data/industry.json` |

已知口径差异：回放时板块分项用新浪行业成分股涨跌中位数替代同花顺行业指数+资金流；板质量分项用价格推导（涨停/连板/收盘=最高/换手）替代封单资金与首次封板时间。收益为「选股日收盘 → D+k 收盘」前复权持有收益，未扣手续费/印花税/滑点，也未处理「次日一字板买不进」。

## 免责声明

本项目为历史数据统计与回放，仅供研究与学习，不构成任何投资建议。
