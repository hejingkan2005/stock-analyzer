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

## Azure 部署（App Service）

项目已适配 Azure 运行：

- `app.py` 会读取 `PORT` 并监听 `0.0.0.0`
- `requirements.txt` 已包含 `gunicorn`
- 一键部署脚本：`scripts/deploy-azure.ps1`

### 1) 先确认 Azure 登录和订阅权限

```bash
az account show
az account list -o table
```

如果遇到 `AADSTS700082`（refresh token 过期），重新登录：

```bash
az logout
az login --tenant <your-tenant-id>
```

如果遇到 `AuthorizationFailed`，说明当前订阅没有创建资源权限。请切换到有权限订阅，或申请 `Contributor` 角色。

### 2) 一键部署

```bash
powershell -ExecutionPolicy Bypass -File scripts/deploy-azure.ps1 -SubscriptionId <your-subscription-id>
```

脚本会自动完成：

1. 打包应用
2. 创建 Resource Group / Linux App Service Plan / Web App
3. 设置启动命令：`gunicorn --bind=0.0.0.0:$PORT --timeout 600 app:server`
4. Zip 部署

成功后会输出访问地址：`https://<app-name>.azurewebsites.net`
