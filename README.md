# 腾讯香港（0700.HK）投资分析 App

这是一个基于 Dash 的投资分析示例应用，默认以腾讯控股香港 `0700.HK` 为分析标的，提供：

1. 可交互价格图（支持时间区间选择）
2. MA5 / MA50 / MA250
3. 当天价格在历史区间中的分位数
4. RSI（强弱指标）
5. 历年年化收益率、标准差、波动区间（收益率±标准差）
6. 最大回撤模块（最大回撤、当前回撤、回撤持续天数、回撤曲线）
7. 估值维度（PE / PB / PS / 股息率 / 市值等快照）

内置预设标的：

- 腾讯香港 `0700.HK`
- 阿里香港 `9988.HK`

## 快速开始

```bash
pip install -r requirements.txt
python app.py
```

启动后访问 `http://127.0.0.1:8050`。

## 说明

- 数据来源：Yahoo Finance（通过 `yfinance`）
- 默认分析标的：`0700.HK`
- RSI 周期：14

## Cloudflare 部署说明

你遇到的报错：

`Could not find a wrangler.json, wrangler.jsonc, or wrangler.toml file in the provided directory.`

已在项目根目录新增 `wrangler.toml`，可解决该错误。

### 方式 A：直接验证 Wrangler 配置

```bash
wrangler deploy
```

这会部署 `cloudflare/worker.js`。

### 方式 B：给 Dash 后端做 Cloudflare 反向代理

Cloudflare Workers 不能直接运行 Dash/Flask 这种长驻 Python 服务器进程。
推荐将 Dash 先部署到支持 Python Web 服务的平台（如 Render/Fly.io/VM），再用 Worker 代理：

```bash
wrangler secret put BACKEND_URL
wrangler deploy
```

将 `BACKEND_URL` 设为你的 Dash 服务地址（例如 `https://your-dash-service.example.com`）。
