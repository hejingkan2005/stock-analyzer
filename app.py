from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import yfinance.shared as yf_shared
from yfinance.exceptions import YFRateLimitError
from dash import Dash, Input, Output, State, ctx, dcc, html


DEFAULT_TICKER = "0700.HK"
PRESET_STOCKS = [
    {"label": "腾讯香港 (0700.HK)", "value": "0700.HK"},
    {"label": "阿里香港 (9988.HK)", "value": "9988.HK"},
]

LANGUAGES = [
    {"label": "中", "value": "zh"},
    {"label": "EN", "value": "en"},
]

I18N = {
    "zh": {
        "header_title": "港股投资分析 Dashboard",
        "header_subtitle": "港股投资分析: 价格、均线、分位数、RSI、年化收益与波动",
        "preset_stock": "预设股票",
        "ticker": "股票代码",
        "quick_range": "快捷区间",
        "date_range": "日期范围",
        "language": "语言",
        "latest_close": "最新收盘价",
        "percentile": "历史分位数",
        "daily_change": "单日涨跌",
        "price_ma": "价格与均线",
        "date": "日期",
        "price_hkd": "价格 (HKD)",
        "close": "收盘价",
        "rsi_title": "RSI 强弱指标",
        "annual_band": "年化收益 / 波动区间",
        "year": "年份",
        "rate": "比率",
        "return_plus_std": "收益 + 波动",
        "return_minus_std": "收益 - 波动",
        "annualized_return": "年化收益",
        "no_yearly_stats": "暂无年度统计数据。",
        "yearly_stats": "年度统计",
        "std": "波动率",
        "volatility_range": "波动区间 (收益-波动, 收益+波动)",
        "not_available": "暂无",
        "drawdown": "回撤",
        "drawdown_stats": "最大回撤统计",
        "no_drawdown": "暂无回撤统计数据。",
        "max_drawdown": "最大回撤",
        "current_drawdown": "当前回撤",
        "peak_date": "峰值日期",
        "trough_date": "谷底日期",
        "recovery_date": "修复日期",
        "current_underwater_days": "当前水下天数",
        "longest_underwater_days": "最长水下天数",
        "not_recovered": "尚未修复",
        "valuation_snapshot": "估值快照",
        "data_source": "数据来源: Yahoo Finance (TTM / 最新可用)",
        "trailing_pe": "静态市盈率",
        "forward_pe": "预期市盈率",
        "price_book": "市净率",
        "price_sales": "市销率 (TTM)",
        "dividend_yield": "股息率",
        "market_cap": "市值",
        "enterprise_value": "企业价值",
        "ev_revenue": "EV / Revenue",
        "ev_ebitda": "EV / EBITDA",
        "invalid_date": "开始日期必须早于结束日期。",
        "no_data": "未找到数据，请检查股票代码或日期范围。",
        "rate_limited": "Yahoo Finance 当前返回频率限制（429 Too Many Requests）。这不是代码或股票代码错误，请稍后重试。",
        "tools_title": "计算工具",
        "toolbar_toggle": "工具栏",
        "close_tool": "关闭",
        "tool_annualized_name": "年化收益率计算器",
        "compound_calc_title": "复利收益率计算器",
        "calc_mode": "计算模式",
        "mode_total_to_annualized": "总收益率 + 年数 -> 年化收益率",
        "mode_annualized_to_total": "年化收益率 + 年数 -> 总收益率",
        "input_rate": "收益率 (%)",
        "total_return": "总收益率 (%)",
        "annualized_return_input": "年化收益率 (%)",
        "holding_years": "持有年数",
        "annualized_return_result": "年化收益率",
        "total_return_result": "总收益率",
        "compound_calc_hint": "计算公式: (1 + 总收益率)^(1/n) - 1",
        "total_return_calc_hint": "计算公式: (1 + 年化收益率)^n - 1",
        "compound_calc_invalid": "请输入大于 -100% 的总收益率，以及大于 0 的持有年数。",
        "total_return_calc_invalid": "请输入大于 -100% 的年化收益率，以及大于 0 的持有年数。",
        "compound_calc_empty": "输入总收益率和持有年数后，这里会显示年化收益率。",
        "total_return_calc_empty": "输入年化收益率和持有年数后，这里会显示总收益率。",
        "preset_tencent": "腾讯香港 (0700.HK)",
        "preset_alibaba": "阿里香港 (9988.HK)",
    },
    "en": {
        "header_title": "HK Stock Analysis Dashboard",
        "header_subtitle": "Price, Moving Averages, Percentile, RSI, Annualized Return and Volatility",
        "preset_stock": "Preset Stock",
        "ticker": "Ticker",
        "quick_range": "Quick Range",
        "date_range": "Date Range",
        "language": "Language",
        "latest_close": "Latest Close",
        "percentile": "Percentile in History",
        "daily_change": "Daily Change",
        "price_ma": "Price with Moving Averages",
        "date": "Date",
        "price_hkd": "Price (HKD)",
        "close": "Close",
        "rsi_title": "RSI Strength Index",
        "annual_band": "Annualized Return / Std Band",
        "year": "Year",
        "rate": "Rate",
        "return_plus_std": "Return + Std",
        "return_minus_std": "Return - Std",
        "annualized_return": "Annualized Return",
        "no_yearly_stats": "No yearly stats available.",
        "yearly_stats": "Yearly Stats",
        "std": "Std",
        "volatility_range": "Volatility Range (Return-Std, Return+Std)",
        "not_available": "N/A",
        "drawdown": "Drawdown",
        "drawdown_stats": "Max Drawdown Stats",
        "no_drawdown": "No drawdown stats available.",
        "max_drawdown": "Max Drawdown",
        "current_drawdown": "Current Drawdown",
        "peak_date": "Peak Date",
        "trough_date": "Trough Date",
        "recovery_date": "Recovery Date",
        "current_underwater_days": "Current Underwater Days",
        "longest_underwater_days": "Longest Underwater Days",
        "not_recovered": "Not recovered",
        "valuation_snapshot": "Valuation Snapshot",
        "data_source": "Data source: Yahoo Finance (TTM / latest available)",
        "trailing_pe": "Trailing PE",
        "forward_pe": "Forward PE",
        "price_book": "Price / Book",
        "price_sales": "Price / Sales (TTM)",
        "dividend_yield": "Dividend Yield",
        "market_cap": "Market Cap",
        "enterprise_value": "Enterprise Value",
        "ev_revenue": "EV / Revenue",
        "ev_ebitda": "EV / EBITDA",
        "invalid_date": "Start date must be earlier than end date.",
        "no_data": "No data found. Check ticker or date range.",
        "rate_limited": "Yahoo Finance is currently rate limiting requests (429 Too Many Requests). This is not a ticker or app logic error. Try again later.",
        "tools_title": "Calculation Tools",
        "toolbar_toggle": "Tools",
        "close_tool": "Close",
        "tool_annualized_name": "Annualized Return Calculator",
        "compound_calc_title": "Compound Return Calculator",
        "calc_mode": "Calculation Mode",
        "mode_total_to_annualized": "Total Return + Years -> Annualized Return",
        "mode_annualized_to_total": "Annualized Return + Years -> Total Return",
        "input_rate": "Return (%)",
        "total_return": "Total Return (%)",
        "annualized_return_input": "Annualized Return (%)",
        "holding_years": "Holding Years",
        "annualized_return_result": "Annualized Return",
        "total_return_result": "Total Return",
        "compound_calc_hint": "Formula: (1 + total return)^(1/n) - 1",
        "total_return_calc_hint": "Formula: (1 + annualized return)^n - 1",
        "compound_calc_invalid": "Enter a total return greater than -100% and a holding period greater than 0.",
        "total_return_calc_invalid": "Enter an annualized return greater than -100% and a holding period greater than 0.",
        "compound_calc_empty": "Enter total return and holding years to see the annualized return.",
        "total_return_calc_empty": "Enter annualized return and holding years to see the total return.",
        "preset_tencent": "Tencent HK (0700.HK)",
        "preset_alibaba": "Alibaba HK (9988.HK)",
    },
}


def t(lang: str, key: str) -> str:
    safe_lang = lang if lang in I18N else "zh"
    return I18N[safe_lang].get(key, I18N["en"].get(key, key))


def make_preset_options(lang: str) -> list[dict]:
    return [
        {"label": t(lang, "preset_tencent"), "value": "0700.HK"},
        {"label": t(lang, "preset_alibaba"), "value": "9988.HK"},
    ]


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


@lru_cache(maxsize=64)
def _load_data_cached(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    df = yf.download(
        ticker,
        start=start_date,
        end=end_date + timedelta(days=1),
        auto_adjust=False,
        progress=False,
    )

    error_message = yf_shared._ERRORS.get(ticker.upper(), "")
    if "YFRateLimitError" in error_message:
        raise YFRateLimitError()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        return df

    price_col = "Adj Close" if "Adj Close" in df.columns else "Close"
    df = df[[price_col]].rename(columns={price_col: "Close"}).dropna().copy()

    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA250"] = df["Close"].rolling(window=250).mean()
    df["RSI"] = compute_rsi(df["Close"], period=14)
    return df


def load_data(ticker: str, start_date: date, end_date: date) -> tuple[pd.DataFrame, str | None]:
    try:
        return _load_data_cached(ticker, start_date, end_date).copy(), None
    except YFRateLimitError:
        return pd.DataFrame(), "rate_limit"
    except Exception:
        return pd.DataFrame(), "fetch_error"


GRAPH_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "scrollZoom": False,
    "doubleClick": "reset",
    "modeBarButtonsToRemove": [
        "zoom2d",
        "pan2d",
        "select2d",
        "lasso2d",
        "zoomIn2d",
        "zoomOut2d",
        "autoScale2d",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "toggleSpikelines",
    ],
}

TOP_RIGHT_LEGEND = {
    "orientation": "h",
    "yanchor": "bottom",
    "y": 1.02,
    "xanchor": "center",
    "x": 0.5,
}


def make_graph(graph_id: str) -> dcc.Graph:
    return dcc.Graph(id=graph_id, config=GRAPH_CONFIG)


def finalize_figure(fig: go.Figure) -> go.Figure:
    fig.update_layout(dragmode=False, legend=TOP_RIGHT_LEGEND)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def compute_annualized_return(total_return_pct: float, years: float) -> float:
    total_return = total_return_pct / 100
    return (1 + total_return) ** (1 / years) - 1


def compute_total_return(annualized_return_pct: float, years: float) -> float:
    annualized_return = annualized_return_pct / 100
    return (1 + annualized_return) ** years - 1


def make_price_figure(df: pd.DataFrame, ticker: str, lang: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name=t(lang, "close"), line=dict(width=2.4, color="#003049")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], mode="lines", name="MA5", line=dict(width=1.6, color="#f77f00")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], mode="lines", name="MA50", line=dict(width=1.6, color="#2a9d8f")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA250"], mode="lines", name="MA250", line=dict(width=1.6, color="#6a4c93")))

    fig.update_layout(
        title=f"{ticker} {t(lang, 'price_ma')}",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        hovermode="x unified",
        xaxis_title=t(lang, "date"),
        yaxis_title=t(lang, "price_hkd"),
        margin=dict(l=20, r=20, t=48, b=20),
    )
    fig.update_xaxes(rangeslider_visible=True)
    return finalize_figure(fig)


def make_rsi_figure(df: pd.DataFrame, lang: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], mode="lines", name="RSI(14)", line=dict(width=2.2, color="#003049")))
    fig.add_hline(y=70, line_dash="dash", line_color="#d62828", annotation_text="70")
    fig.add_hline(y=30, line_dash="dash", line_color="#2a9d8f", annotation_text="30")
    fig.update_layout(
        title=t(lang, "rsi_title"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        hovermode="x unified",
        xaxis_title=t(lang, "date"),
        yaxis_title="RSI",
        yaxis=dict(range=[0, 100]),
        margin=dict(l=20, r=20, t=48, b=20),
    )
    return finalize_figure(fig)


def compute_yearly_stats(df: pd.DataFrame) -> pd.DataFrame:
    yearly_df = df[["Close"]].copy()
    yearly_df["DailyReturn"] = yearly_df["Close"].pct_change()
    yearly_df = yearly_df.dropna(subset=["DailyReturn"])

    if yearly_df.empty:
        return pd.DataFrame(columns=["Year", "AnnualReturn", "AnnualStd", "LowerBand", "UpperBand"])

    rows = []
    for year, group in yearly_df.groupby(yearly_df.index.year):
        daily_ret = group["DailyReturn"]
        n = len(daily_ret)
        if n == 0:
            continue

        total_return = (1 + daily_ret).prod() - 1
        annual_return = (1 + total_return) ** (252 / n) - 1
        annual_std = daily_ret.std(ddof=1) * np.sqrt(252) if n > 1 else np.nan

        rows.append(
            {
                "Year": int(year),
                "AnnualReturn": float(annual_return),
                "AnnualStd": float(annual_std) if pd.notna(annual_std) else np.nan,
                "LowerBand": float(annual_return - annual_std) if pd.notna(annual_std) else np.nan,
                "UpperBand": float(annual_return + annual_std) if pd.notna(annual_std) else np.nan,
            }
        )

    return pd.DataFrame(rows).sort_values("Year")


def make_yearly_band_figure(yearly_stats: pd.DataFrame, lang: str) -> go.Figure:
    fig = go.Figure()
    if yearly_stats.empty:
        fig.update_layout(
            title=t(lang, "annual_band"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            xaxis_title=t(lang, "year"),
            yaxis_title=t(lang, "rate"),
            margin=dict(l=20, r=20, t=48, b=20),
        )
        return finalize_figure(fig)

    fig.add_trace(
        go.Scatter(
            x=yearly_stats["Year"],
            y=yearly_stats["UpperBand"],
            mode="lines",
            name=t(lang, "return_plus_std"),
            line=dict(width=1.6, color="#90be6d"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=yearly_stats["Year"],
            y=yearly_stats["LowerBand"],
            mode="lines",
            name=t(lang, "return_minus_std"),
            line=dict(width=1.6, color="#f94144"),
            fill="tonexty",
            fillcolor="rgba(33, 158, 188, 0.16)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=yearly_stats["Year"],
            y=yearly_stats["AnnualReturn"],
            mode="lines+markers",
            name=t(lang, "annualized_return"),
            line=dict(width=2.4, color="#003049"),
        )
    )

    fig.update_layout(
        title=t(lang, "annual_band"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        xaxis_title=t(lang, "year"),
        yaxis_title=t(lang, "rate"),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=48, b=20),
    )
    fig.update_yaxes(tickformat=".1%")
    return finalize_figure(fig)


def make_yearly_stats_table(yearly_stats: pd.DataFrame, lang: str) -> html.Div:
    if yearly_stats.empty:
        return html.Div(t(lang, "no_yearly_stats"), className="metric-title")

    header = html.Thead(
        html.Tr(
            [
                html.Th(t(lang, "year")),
                html.Th(t(lang, "annualized_return")),
                html.Th(t(lang, "std")),
                html.Th(t(lang, "volatility_range")),
            ]
        )
    )

    body_rows = []
    for _, row in yearly_stats.iterrows():
        annual_return = row["AnnualReturn"]
        annual_std = row["AnnualStd"]
        lower = row["LowerBand"]
        upper = row["UpperBand"]
        range_text = t(lang, "not_available") if pd.isna(lower) or pd.isna(upper) else f"{lower:.2%} ~ {upper:.2%}"

        body_rows.append(
            html.Tr(
                [
                    html.Td(str(int(row["Year"]))),
                    html.Td(f"{annual_return:.2%}"),
                    html.Td(t(lang, "not_available") if pd.isna(annual_std) else f"{annual_std:.2%}"),
                    html.Td(range_text),
                ]
            )
        )

    table = html.Table([header, html.Tbody(body_rows)], className="yearly-table")
    return html.Div([html.H4(t(lang, "yearly_stats")), table])


def compute_drawdown_stats(df: pd.DataFrame) -> tuple[pd.Series, dict]:
    close = df["Close"].dropna()
    if close.empty:
        return pd.Series(dtype=float), {}

    normalized = close / close.iloc[0]
    running_max = normalized.cummax()
    drawdown = normalized / running_max - 1

    max_drawdown = float(drawdown.min())
    trough_date = drawdown.idxmin()
    peak_date = normalized.loc[:trough_date].idxmax()
    recovery_date = None
    after_trough = drawdown.loc[trough_date:]
    recovery_candidates = after_trough[after_trough >= 0].index
    if len(recovery_candidates) > 0:
        recovery_date = recovery_candidates[0]

    current_drawdown = float(drawdown.iloc[-1])
    peak_points = drawdown[drawdown == 0].index
    last_peak = peak_points[-1] if len(peak_points) > 0 else drawdown.index[0]
    current_underwater_days = 0 if current_drawdown == 0 else int((drawdown.index[-1] - last_peak).days)

    longest_underwater_days = 0
    streak_start = None
    for idx, value in drawdown.items():
        if value < 0 and streak_start is None:
            streak_start = idx
        if value >= 0 and streak_start is not None:
            longest_underwater_days = max(longest_underwater_days, int((idx - streak_start).days))
            streak_start = None
    if streak_start is not None:
        longest_underwater_days = max(longest_underwater_days, int((drawdown.index[-1] - streak_start).days))

    stats = {
        "max_drawdown": max_drawdown,
        "current_drawdown": current_drawdown,
        "peak_date": peak_date,
        "trough_date": trough_date,
        "recovery_date": recovery_date,
        "current_underwater_days": current_underwater_days,
        "longest_underwater_days": longest_underwater_days,
    }
    return drawdown, stats


def make_drawdown_figure(drawdown: pd.Series, ticker: str, lang: str) -> go.Figure:
    fig = go.Figure()
    if drawdown.empty:
        fig.update_layout(
            title=t(lang, "drawdown"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            xaxis_title=t(lang, "date"),
            yaxis_title=t(lang, "drawdown"),
            margin=dict(l=20, r=20, t=48, b=20),
        )
        return finalize_figure(fig)

    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown,
            mode="lines",
            name=t(lang, "drawdown"),
            line=dict(width=2.2, color="#c1121f"),
            fill="tozeroy",
            fillcolor="rgba(193, 18, 31, 0.12)",
        )
    )
    fig.update_layout(
        title=f"{ticker} {t(lang, 'drawdown')}",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        hovermode="x unified",
        xaxis_title=t(lang, "date"),
        yaxis_title=t(lang, "drawdown"),
        margin=dict(l=20, r=20, t=48, b=20),
    )
    fig.update_yaxes(tickformat=".1%")
    return finalize_figure(fig)


def make_drawdown_panel(drawdown_stats: dict, lang: str) -> html.Div:
    if not drawdown_stats:
        return html.Div(t(lang, "no_drawdown"), className="metric-title")

    recovery_text = t(lang, "not_recovered") if drawdown_stats["recovery_date"] is None else str(drawdown_stats["recovery_date"].date())
    return html.Div(
        [
            html.H4(t(lang, "drawdown_stats")),
            html.Table(
                [
                    html.Tbody(
                        [
                            html.Tr([html.Th(t(lang, "max_drawdown")), html.Td(f"{drawdown_stats['max_drawdown']:.2%}")]),
                            html.Tr([html.Th(t(lang, "current_drawdown")), html.Td(f"{drawdown_stats['current_drawdown']:.2%}")]),
                            html.Tr([html.Th(t(lang, "peak_date")), html.Td(str(drawdown_stats["peak_date"].date()))]),
                            html.Tr([html.Th(t(lang, "trough_date")), html.Td(str(drawdown_stats["trough_date"].date()))]),
                            html.Tr([html.Th(t(lang, "recovery_date")), html.Td(recovery_text)]),
                            html.Tr([html.Th(t(lang, "current_underwater_days")), html.Td(str(drawdown_stats["current_underwater_days"]))]),
                            html.Tr([html.Th(t(lang, "longest_underwater_days")), html.Td(str(drawdown_stats["longest_underwater_days"]))]),
                        ]
                    )
                ],
                className="summary-table",
            ),
        ]
    )


def format_large_number(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    abs_value = abs(float(value))
    if abs_value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value:,.0f}"


@lru_cache(maxsize=32)
def get_valuation_snapshot(ticker: str) -> list[tuple[str, str]]:
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    dividend = info.get("dividendYield")
    valuation_items = [
        ("Trailing PE", "N/A" if info.get("trailingPE") is None else f"{info.get('trailingPE'):.2f}"),
        ("Forward PE", "N/A" if info.get("forwardPE") is None else f"{info.get('forwardPE'):.2f}"),
        ("Price / Book", "N/A" if info.get("priceToBook") is None else f"{info.get('priceToBook'):.2f}"),
        (
            "Price / Sales (TTM)",
            "N/A" if info.get("priceToSalesTrailing12Months") is None else f"{info.get('priceToSalesTrailing12Months'):.2f}",
        ),
        ("Dividend Yield", "N/A" if dividend is None else f"{dividend:.2%}"),
        ("Market Cap", format_large_number(info.get("marketCap"))),
        ("Enterprise Value", format_large_number(info.get("enterpriseValue"))),
        ("EV / Revenue", "N/A" if info.get("enterpriseToRevenue") is None else f"{info.get('enterpriseToRevenue'):.2f}"),
        ("EV / EBITDA", "N/A" if info.get("enterpriseToEbitda") is None else f"{info.get('enterpriseToEbitda'):.2f}"),
    ]
    return valuation_items


def make_valuation_panel(ticker: str, lang: str) -> html.Div:
    items = get_valuation_snapshot(ticker)
    name_map = {
        "Trailing PE": t(lang, "trailing_pe"),
        "Forward PE": t(lang, "forward_pe"),
        "Price / Book": t(lang, "price_book"),
        "Price / Sales (TTM)": t(lang, "price_sales"),
        "Dividend Yield": t(lang, "dividend_yield"),
        "Market Cap": t(lang, "market_cap"),
        "Enterprise Value": t(lang, "enterprise_value"),
        "EV / Revenue": t(lang, "ev_revenue"),
        "EV / EBITDA": t(lang, "ev_ebitda"),
    }
    rows = [html.Tr([html.Th(name_map.get(name, name)), html.Td(value)]) for name, value in items]
    return html.Div(
        [
            html.H4(t(lang, "valuation_snapshot")),
            html.Div(t(lang, "data_source"), className="metric-title"),
            html.Table([html.Tbody(rows)], className="summary-table"),
        ]
    )


app = Dash(__name__)
server = app.server

today = date.today()
default_start = today - timedelta(days=365 * 5)

sidebar_layout = html.Aside(
    [
        html.Div(
            id="tool-menu",
            className="tool-menu",
            children=[html.Button(id="tool-annualized-btn", className="tool-menu-btn")],
        ),
        html.Div(
            id="sidebar-tool-content",
            className="tool-grid",
            children=[
                html.Div(
                    className="card calculator-card",
                    children=[
                        html.Div(
                            [
                                html.H4(id="compound-calc-title"),
                                html.Button(id="tool-close-btn", className="tool-close-btn"),
                            ],
                            className="calculator-header",
                        ),
                        html.Div(id="calc-mode-title", className="metric-title"),
                        dcc.RadioItems(id="calc-mode-toggle", value="total_to_annualized", className="calc-mode-toggle"),
                        html.Div(id="compound-calc-hint", className="metric-title"),
                        html.Div(
                            className="calculator-form",
                            children=[
                                html.Div(
                                    [
                                        html.Label(id="input-rate-title", className="calculator-label"),
                                        dcc.Input(id="calc-rate-input", type="number", value=100, debounce=True, step=1, className="calculator-input"),
                                    ]
                                ),
                                html.Div(
                                    [
                                        html.Label(id="input-years-title", className="calculator-label"),
                                        dcc.Input(id="calc-years-input", type="number", value=3, debounce=True, step=1, min=1, className="calculator-input"),
                                    ]
                                ),
                            ],
                        ),
                        html.Div(id="calc-result", className="calculator-result"),
                    ],
                )
            ],
        ),
    ],
    id="sidebar",
    className="sidebar sidebar-collapsed",
)

main_page_layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.H2(id="header-title", style={"margin": "0 0 6px 0"}),
                        html.Div(id="header-subtitle"),
                    ],
                    className="header-main",
                ),
                html.Div(
                    [
                        html.Span("🌐", className="lang-icon"),
                        dcc.RadioItems(id="language-radio", options=LANGUAGES, value="zh", inline=True, className="lang-radio"),
                    ],
                    className="header-lang",
                ),
            ],
            className="header",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(id="preset-title", className="metric-title"),
                        dcc.Dropdown(id="preset-stock", options=make_preset_options("zh"), value=DEFAULT_TICKER, clearable=False),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.Div(id="ticker-title", className="metric-title"),
                        dcc.Input(id="ticker-input", type="text", value=DEFAULT_TICKER, debounce=True, style={"width": "100%", "padding": "8px", "fontSize": "16px"}),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.Div(id="range-title", className="metric-title"),
                        dcc.RadioItems(
                            id="range-radio",
                            options=[
                                {"label": "1M", "value": "1M"},
                                {"label": "3M", "value": "3M"},
                                {"label": "6M", "value": "6M"},
                                {"label": "1Y", "value": "1Y"},
                                {"label": "5Y", "value": "5Y"},
                            ],
                            value="5Y",
                            inline=True,
                            labelStyle={"marginRight": "10px"},
                        ),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.Div(id="date-title", className="metric-title"),
                        dcc.DatePickerRange(id="date-range", start_date=default_start, end_date=today, display_format="YYYY-MM-DD"),
                    ],
                    className="card",
                ),
            ],
            className="controls",
        ),
        html.Div(id="metrics", className="metrics"),
        html.Div(className="card", children=[make_graph("price-chart")]),
        html.Div(style={"height": "10px"}),
        html.Div(className="card", children=[make_graph("rsi-chart")]),
        html.Div(style={"height": "10px"}),
        html.Div(className="card", children=[make_graph("yearly-band-chart")]),
        html.Div(style={"height": "10px"}),
        html.Div(className="card", id="yearly-stats-table"),
        html.Div(style={"height": "10px"}),
        html.Div(className="card", children=[make_graph("drawdown-chart")]),
        html.Div(style={"height": "10px"}),
        html.Div(className="two-col-panels", children=[html.Div(className="card", id="drawdown-panel"), html.Div(className="card", id="valuation-panel")]),
        html.Div(id="error-message", style={"color": "#b00020", "marginTop": "12px", "fontWeight": "600"}),
    ],
    className="page",
)

app.layout = html.Div(
    [
        dcc.Store(id="tool-sidebar-state", data={"open": False, "selected": None}),
        html.Button(id="toolbar-toggle-btn", className="toolbar-toggle-btn"),
        html.Div(id="sidebar-overlay", className="sidebar-overlay"),
        html.Div(
            [
                html.Div([sidebar_layout], className="left-panel"),
                html.Div([main_page_layout], className="right-panel"),
            ],
            id="app-shell",
            className="app-shell sidebar-closed",
        ),
    ],
)


@app.callback(
    Output("ticker-input", "value"),
    Input("preset-stock", "value"),
)
def sync_ticker_with_preset(preset_ticker: str):
    return preset_ticker or DEFAULT_TICKER


@app.callback(
    Output("header-title", "children"),
    Output("header-subtitle", "children"),
    Output("toolbar-toggle-btn", "children"),
    Output("preset-title", "children"),
    Output("ticker-title", "children"),
    Output("range-title", "children"),
    Output("date-title", "children"),
    Output("tool-annualized-btn", "children"),
    Output("compound-calc-title", "children"),
    Output("tool-close-btn", "children"),
    Output("calc-mode-title", "children"),
    Output("calc-mode-toggle", "options"),
    Output("range-radio", "options"),
    Output("preset-stock", "options"),
    Input("language-radio", "value"),
)
def update_static_text(lang: str):
    current_lang = lang if lang in I18N else "zh"
    return (
        t(current_lang, "header_title"),
        t(current_lang, "header_subtitle"),
        t(current_lang, "toolbar_toggle"),
        t(current_lang, "preset_stock"),
        t(current_lang, "ticker"),
        t(current_lang, "quick_range"),
        t(current_lang, "date_range"),
        t(current_lang, "tool_annualized_name"),
        t(current_lang, "compound_calc_title"),
        t(current_lang, "close_tool"),
        t(current_lang, "calc_mode"),
        [
            {"label": t(current_lang, "mode_total_to_annualized"), "value": "total_to_annualized"},
            {"label": t(current_lang, "mode_annualized_to_total"), "value": "annualized_to_total"},
        ],
        [
            {"label": "1月" if current_lang == "zh" else "1M", "value": "1M"},
            {"label": "3月" if current_lang == "zh" else "3M", "value": "3M"},
            {"label": "6月" if current_lang == "zh" else "6M", "value": "6M"},
            {"label": "1年" if current_lang == "zh" else "1Y", "value": "1Y"},
            {"label": "5年" if current_lang == "zh" else "5Y", "value": "5Y"},
        ],
        make_preset_options(current_lang),
    )


@app.callback(
    Output("tool-sidebar-state", "data"),
    Input("toolbar-toggle-btn", "n_clicks"),
    Input("tool-annualized-btn", "n_clicks"),
    Input("tool-close-btn", "n_clicks"),
    Input("sidebar-overlay", "n_clicks"),
    State("tool-sidebar-state", "data"),
    prevent_initial_call=True,
)
def update_tool_sidebar_state(toolbar_clicks, annualized_clicks, close_tool_clicks, overlay_clicks, state):
    sidebar_state = state or {"open": False, "selected": None}
    trigger = ctx.triggered_id

    if trigger == "toolbar-toggle-btn":
        is_open = not bool(sidebar_state.get("open"))
        return {"open": is_open, "selected": sidebar_state.get("selected") if is_open else None}

    if trigger == "sidebar-overlay":
        return {"open": False, "selected": None}

    if trigger == "tool-annualized-btn":
        return {"open": True, "selected": "annualized"}

    if trigger == "tool-close-btn":
        return {"open": True, "selected": None}

    return sidebar_state


@app.callback(
    Output("app-shell", "className"),
    Output("sidebar", "className"),
    Output("sidebar-overlay", "className"),
    Output("tool-menu", "style"),
    Output("sidebar-tool-content", "style"),
    Input("tool-sidebar-state", "data"),
)
def render_tool_sidebar(state):
    sidebar_state = state or {"open": False, "selected": None}
    is_open = bool(sidebar_state.get("open"))
    selected = sidebar_state.get("selected")

    if not is_open:
        return (
            "app-shell sidebar-closed",
            "sidebar sidebar-collapsed",
            "sidebar-overlay",
            {"display": "none"},
            {"display": "none"},
        )

    menu_style = {"display": "grid"}
    content_style = {"display": "none"}

    if selected == "annualized":
        content_style = {"display": "grid"}

    return (
        "app-shell sidebar-open",
        "sidebar sidebar-expanded",
        "sidebar-overlay active",
        menu_style,
        content_style,
    )


@app.callback(
    Output("compound-calc-hint", "children"),
    Output("input-rate-title", "children"),
    Output("input-years-title", "children"),
    Output("calc-result", "children"),
    Input("calc-mode-toggle", "value"),
    Input("calc-rate-input", "value"),
    Input("calc-years-input", "value"),
    Input("language-radio", "value"),
)
def update_compound_calculator(mode: str, rate_pct: float | None, years: float | None, lang: str):
    current_lang = lang if lang in I18N else "zh"
    active_mode = mode if mode in {"total_to_annualized", "annualized_to_total"} else "total_to_annualized"

    if active_mode == "annualized_to_total":
        hint = t(current_lang, "total_return_calc_hint")
        rate_label = t(current_lang, "annualized_return_input")
        if rate_pct is None or years is None:
            result = html.Div(t(current_lang, "total_return_calc_empty"), className="metric-title")
            return hint, rate_label, t(current_lang, "holding_years"), result

        if rate_pct <= -100 or years <= 0:
            result = html.Div(t(current_lang, "total_return_calc_invalid"), className="calculator-error")
            return hint, rate_label, t(current_lang, "holding_years"), result

        total_return = compute_total_return(float(rate_pct), float(years))
        result = html.Div(
            [
                html.Div(t(current_lang, "total_return_result"), className="metric-title"),
                html.Div(f"{total_return:.2%}", className="metric-value"),
            ]
        )
        return hint, rate_label, t(current_lang, "holding_years"), result

    hint = t(current_lang, "compound_calc_hint")
    rate_label = t(current_lang, "total_return")
    if rate_pct is None or years is None:
        result = html.Div(t(current_lang, "compound_calc_empty"), className="metric-title")
        return hint, rate_label, t(current_lang, "holding_years"), result

    if rate_pct <= -100 or years <= 0:
        result = html.Div(t(current_lang, "compound_calc_invalid"), className="calculator-error")
        return hint, rate_label, t(current_lang, "holding_years"), result

    annualized_return = compute_annualized_return(float(rate_pct), float(years))
    result = html.Div(
        [
            html.Div(t(current_lang, "annualized_return_result"), className="metric-title"),
            html.Div(f"{annualized_return:.2%}", className="metric-value"),
        ]
    )
    return hint, rate_label, t(current_lang, "holding_years"), result


@app.callback(
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
    Input("range-radio", "value"),
)
def sync_date_range(range_value: str):
    end = date.today()
    offsets = {
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "5Y": 365 * 5,
    }
    start = end - timedelta(days=offsets.get(range_value, 365 * 5))
    return start, end


@app.callback(
    Output("metrics", "children"),
    Output("price-chart", "figure"),
    Output("rsi-chart", "figure"),
    Output("yearly-band-chart", "figure"),
    Output("yearly-stats-table", "children"),
    Output("drawdown-chart", "figure"),
    Output("drawdown-panel", "children"),
    Output("valuation-panel", "children"),
    Output("error-message", "children"),
    Input("ticker-input", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("language-radio", "value"),
)
def update_dashboard(ticker: str, start_date: str, end_date: str, lang: str):
    current_lang = lang if lang in I18N else "zh"
    ticker = (ticker or DEFAULT_TICKER).strip().upper()
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()

    if start >= end:
        return [], go.Figure(), go.Figure(), go.Figure(), html.Div(), go.Figure(), html.Div(), html.Div(), t(current_lang, "invalid_date")

    df, fetch_error = load_data(ticker, start, end)
    if fetch_error == "rate_limit":
        return [], go.Figure(), go.Figure(), go.Figure(), html.Div(), go.Figure(), html.Div(), html.Div(), t(current_lang, "rate_limited")

    if df.empty:
        return [], go.Figure(), go.Figure(), go.Figure(), html.Div(), go.Figure(), html.Div(), html.Div(), t(current_lang, "no_data")

    latest_close = float(df["Close"].iloc[-1])
    latest_rsi = df["RSI"].iloc[-1]
    percentile = float((df["Close"] <= latest_close).mean() * 100)

    if len(df) > 1:
        daily_change = (df["Close"].iloc[-1] / df["Close"].iloc[-2] - 1) * 100
        daily_change_text = f"{daily_change:.2f}%"
    else:
        daily_change_text = t(current_lang, "not_available")

    cards = [
        html.Div([html.Div(t(current_lang, "latest_close"), className="metric-title"), html.Div(f"{latest_close:.2f} HKD", className="metric-value")], className="card"),
        html.Div([html.Div(t(current_lang, "percentile"), className="metric-title"), html.Div(f"{percentile:.2f}%", className="metric-value")], className="card"),
        html.Div([html.Div("RSI(14)", className="metric-title"), html.Div(t(current_lang, "not_available") if pd.isna(latest_rsi) else f"{latest_rsi:.2f}", className="metric-value")], className="card"),
        html.Div([html.Div(t(current_lang, "daily_change"), className="metric-title"), html.Div(daily_change_text, className="metric-value")], className="card"),
    ]

    yearly_stats = compute_yearly_stats(df)
    drawdown, drawdown_stats = compute_drawdown_stats(df)

    return (
        cards,
        make_price_figure(df, ticker, current_lang),
        make_rsi_figure(df, current_lang),
        make_yearly_band_figure(yearly_stats, current_lang),
        make_yearly_stats_table(yearly_stats, current_lang),
        make_drawdown_figure(drawdown, ticker, current_lang),
        make_drawdown_panel(drawdown_stats, current_lang),
        make_valuation_panel(ticker, current_lang),
        "",
    )


if __name__ == "__main__":
    app.run(debug=False)
