from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import yfinance.shared as yf_shared
from yfinance.exceptions import YFRateLimitError
from dash import Dash, Input, Output, dcc, html


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


def make_graph(graph_id: str) -> dcc.Graph:
    return dcc.Graph(id=graph_id, config=GRAPH_CONFIG)


def finalize_figure(fig: go.Figure) -> go.Figure:
    fig.update_layout(dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
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

app.layout = html.Div(
    [
        html.Div(
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
                                dcc.RadioItems(
                                    id="language-radio",
                                    options=LANGUAGES,
                                    value="zh",
                                    inline=True,
                                    className="lang-radio",
                                ),
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
                                dcc.Dropdown(
                                    id="preset-stock",
                                    options=make_preset_options("zh"),
                                    value=DEFAULT_TICKER,
                                    clearable=False,
                                ),
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
                                dcc.DatePickerRange(
                                    id="date-range",
                                    start_date=default_start,
                                    end_date=today,
                                    display_format="YYYY-MM-DD",
                                ),
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
        ),
    ]
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
    Output("preset-title", "children"),
    Output("ticker-title", "children"),
    Output("range-title", "children"),
    Output("date-title", "children"),
    Output("range-radio", "options"),
    Output("preset-stock", "options"),
    Input("language-radio", "value"),
)
def update_static_text(lang: str):
    current_lang = lang if lang in I18N else "zh"
    return (
        t(current_lang, "header_title"),
        t(current_lang, "header_subtitle"),
        t(current_lang, "preset_stock"),
        t(current_lang, "ticker"),
        t(current_lang, "quick_range"),
        t(current_lang, "date_range"),
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
