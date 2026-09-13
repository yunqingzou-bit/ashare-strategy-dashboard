# A股选股策略回测看板

收盘后自动回放「涨幅/成交额/换手/涨停」候选池 + 六维评分选股模型，生成桌面与移动端自适应的单页看板，并发布到 GitHub Pages。

在线看板：https://yunqingzou-bit.github.io/ashare-strategy-dashboard/

## 目录结构

```
scripts/
  fetch.py        抓全市场前复权日线(同花顺) + 每日涨停池/龙虎榜/公告(东方财富, 按日缓存)
  replay.py       逐日回放选股模型, 输出每日前5只与D+1..D+5走势
  report.py       生成逐只明细与5日内事件 -> data/final.json
  build_site.py   渲染响应式单页看板 -> docs/index.html
  update.py       一键编排: fetch -> replay -> report -> build_site
  run_daily.ps1   Windows 计划任务入口(更新后自动 git push)
  assets/         样式与交互(dash.css / dash_add.css / dash2.js)
data/             运行期数据(已 gitignore); industry.json 为板块映射, 需提交
docs/             GitHub Pages 发布目录(index.html + .nojekyll)
local-tools/      本机专用工具(gh.exe 等, 已 gitignore)
```

## 本地运行

```bash
pip install -r requirements.txt
python scripts/update.py --days 45
# 产物: docs/index.html  (双击即可打开)
```

参数：`--days N` 回放窗口(默认45个交易日)；`--skip-fetch` 跳过抓取仅重建页面。

## 每日自动更新

**默认走云端 GitHub Actions，不依赖本机开关机。**

| 项 | 值 |
|---|---|
| 工作流 | `.github/workflows/daily.yml` |
| 触发 | 工作日 18:30（北京）= 10:30 UTC，另支持手动 `workflow_dispatch` |
| 执行内容 | 抓数 → 回放 → 重建 `docs/index.html` → 自动 commit + push |
| 发布 | push 后 GitHub Pages 自动重建（约 30 秒） |
| 加速 | `actions/cache` 缓存 `data/events/`，日常运行只抓新交易日 |
| 超时上限 | 150 分钟 |

### 云端数据源可达性（实测于 GitHub ubuntu-latest runner）

| 数据源 | 用途 | 云端可达 |
|---|---|---|
| 新浪 `Market_Center.getHQNodeData` | 全 A 股名单 | ✅ |
| 同花顺 `d.10jqka.com.cn` | 全市场前复权日线 | ✅ |
| 东方财富 `push2ex` | 涨停/炸板/强势股池 | ✅ |
| 东方财富 `datacenter-web` | 龙虎榜、两融 | ✅ |
| 东方财富 `np-anotice-stock` | 公告 | ✅ |
| 东方财富 `push2`(clist) | 全市场快照 | ❌ 502（未使用） |
| 深交所 `szse.cn` | akshare 内置名单源 | ❌ 连接重置（已弃用） |

> 关键点：`akshare.stock_info_a_code_name()` 依赖深交所/上交所接口，在 GitHub 托管 runner 上会被重置连接。本项目已改为**新浪分页取全 A 股名单**（`scripts/fetch.py` 的 `universe()`），akshare 仅作为本机兜底。

### 本机兜底（可选，当前已停用）

为避免与云端定时任务重复推送，本机计划任务 `ashare-dashboard-daily` 已停用；需要时：

```powershell
schtasks /Change /TN "ashare-dashboard-daily" /ENABLE    # 启用（工作日 18:30）
schtasks /Change /TN "ashare-dashboard-daily" /DISABLE   # 停用
schtasks /Run /TN "ashare-dashboard-daily"               # 立即跑一次
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
