from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from dash import Dash, Input, Output, dcc, html


DEFAULT_TICKER = "0700.HK"
PRESET_STOCKS = [
    {"label": "腾讯香港 (0700.HK)", "value": "0700.HK"},
    {"label": "阿里香港 (9988.HK)", "value": "9988.HK"},
]


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def load_data(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    df = yf.download(
        ticker,
        start=start_date,
        end=end_date + timedelta(days=1),
        auto_adjust=False,
        progress=False,
    )

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


def make_price_figure(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Close", line=dict(width=2.4, color="#003049")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], mode="lines", name="MA5", line=dict(width=1.6, color="#f77f00")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], mode="lines", name="MA50", line=dict(width=1.6, color="#2a9d8f")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA250"], mode="lines", name="MA250", line=dict(width=1.6, color="#6a4c93")))

    fig.update_layout(
        title=f"{ticker} Price with MA",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Price (HKD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=48, b=20),
    )
    fig.update_xaxes(rangeslider_visible=True)
    return fig


def make_rsi_figure(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], mode="lines", name="RSI(14)", line=dict(width=2.2, color="#003049")))
    fig.add_hline(y=70, line_dash="dash", line_color="#d62828", annotation_text="70")
    fig.add_hline(y=30, line_dash="dash", line_color="#2a9d8f", annotation_text="30")
    fig.update_layout(
        title="RSI Strength Index",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="RSI",
        yaxis=dict(range=[0, 100]),
        margin=dict(l=20, r=20, t=48, b=20),
    )
    return fig


def compute_yearly_stats(df: pd.DataFrame) -> pd.DataFrame:
    yearly_df = df[["Close"]].copy()
    yearly_df["DailyReturn"] = yearly_df["Close"].pct_change()
    yearly_df = yearly_df.dropna(subset=["DailyReturn"])

    if yearly_df.empty:
        return pd.DataFrame(columns=["Year", "AnnualReturn", "StdAllYears", "LowerBand", "UpperBand"])

    # Use one annualized std computed from all daily returns in the selected history.
    std_all_years = yearly_df["DailyReturn"].std(ddof=1) * np.sqrt(252) if len(yearly_df) > 1 else np.nan

    rows = []
    for year, group in yearly_df.groupby(yearly_df.index.year):
        daily_ret = group["DailyReturn"]
        n = len(daily_ret)
        if n == 0:
            continue

        total_return = (1 + daily_ret).prod() - 1
        annual_return = (1 + total_return) ** (252 / n) - 1

        rows.append(
            {
                "Year": int(year),
                "AnnualReturn": float(annual_return),
                "StdAllYears": float(std_all_years) if pd.notna(std_all_years) else np.nan,
                "LowerBand": float(annual_return - std_all_years) if pd.notna(std_all_years) else np.nan,
                "UpperBand": float(annual_return + std_all_years) if pd.notna(std_all_years) else np.nan,
            }
        )

    return pd.DataFrame(rows).sort_values("Year")


def make_yearly_band_figure(yearly_stats: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if yearly_stats.empty:
        fig.update_layout(
            title="Annualized Return / Std Band",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            xaxis_title="Year",
            yaxis_title="Rate",
            margin=dict(l=20, r=20, t=48, b=20),
        )
        return fig

    fig.add_trace(
        go.Scatter(
            x=yearly_stats["Year"],
            y=yearly_stats["UpperBand"],
            mode="lines",
            name="Return + Std",
            line=dict(width=1.6, color="#90be6d"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=yearly_stats["Year"],
            y=yearly_stats["LowerBand"],
            mode="lines",
            name="Return - Std",
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
            name="Annualized Return",
            line=dict(width=2.4, color="#003049"),
        )
    )

    fig.update_layout(
        title="Annualized Return / Std Band",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        xaxis_title="Year",
        yaxis_title="Rate",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=48, b=20),
    )
    fig.update_yaxes(tickformat=".1%")
    return fig


def make_yearly_stats_table(yearly_stats: pd.DataFrame) -> html.Div:
    if yearly_stats.empty:
        return html.Div("No yearly stats available.", className="metric-title")

    header = html.Thead(
        html.Tr(
            [
                html.Th("Year"),
                html.Th("Annualized Return"),
                html.Th("Std (All Years)"),
                html.Th("Volatility Range (Return-Std, Return+Std)"),
            ]
        )
    )

    body_rows = []
    for _, row in yearly_stats.iterrows():
        annual_return = row["AnnualReturn"]
        annual_std = row["StdAllYears"]
        lower = row["LowerBand"]
        upper = row["UpperBand"]
        range_text = "N/A" if pd.isna(lower) or pd.isna(upper) else f"{lower:.2%} ~ {upper:.2%}"

        body_rows.append(
            html.Tr(
                [
                    html.Td(str(int(row["Year"]))),
                    html.Td(f"{annual_return:.2%}"),
                    html.Td("N/A" if pd.isna(annual_std) else f"{annual_std:.2%}"),
                    html.Td(range_text),
                ]
            )
        )

    table = html.Table([header, html.Tbody(body_rows)], className="yearly-table")
    return html.Div([html.H4("Yearly Stats"), table])


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


def make_drawdown_figure(drawdown: pd.Series, ticker: str) -> go.Figure:
    fig = go.Figure()
    if drawdown.empty:
        fig.update_layout(
            title="Drawdown",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            xaxis_title="Date",
            yaxis_title="Drawdown",
            margin=dict(l=20, r=20, t=48, b=20),
        )
        return fig

    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown,
            mode="lines",
            name="Drawdown",
            line=dict(width=2.2, color="#c1121f"),
            fill="tozeroy",
            fillcolor="rgba(193, 18, 31, 0.12)",
        )
    )
    fig.update_layout(
        title=f"{ticker} Drawdown",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Drawdown",
        margin=dict(l=20, r=20, t=48, b=20),
    )
    fig.update_yaxes(tickformat=".1%")
    return fig


def make_drawdown_panel(drawdown_stats: dict) -> html.Div:
    if not drawdown_stats:
        return html.Div("No drawdown stats available.", className="metric-title")

    recovery_text = "Not recovered" if drawdown_stats["recovery_date"] is None else str(drawdown_stats["recovery_date"].date())
    return html.Div(
        [
            html.H4("Max Drawdown Stats"),
            html.Table(
                [
                    html.Tbody(
                        [
                            html.Tr([html.Th("Max Drawdown"), html.Td(f"{drawdown_stats['max_drawdown']:.2%}")]),
                            html.Tr([html.Th("Current Drawdown"), html.Td(f"{drawdown_stats['current_drawdown']:.2%}")]),
                            html.Tr([html.Th("Peak Date"), html.Td(str(drawdown_stats["peak_date"].date()))]),
                            html.Tr([html.Th("Trough Date"), html.Td(str(drawdown_stats["trough_date"].date()))]),
                            html.Tr([html.Th("Recovery Date"), html.Td(recovery_text)]),
                            html.Tr([html.Th("Current Underwater Days"), html.Td(str(drawdown_stats["current_underwater_days"]))]),
                            html.Tr([html.Th("Longest Underwater Days"), html.Td(str(drawdown_stats["longest_underwater_days"]))]),
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


def make_valuation_panel(ticker: str) -> html.Div:
    items = get_valuation_snapshot(ticker)
    rows = [html.Tr([html.Th(name), html.Td(value)]) for name, value in items]
    return html.Div(
        [
            html.H4("Valuation Snapshot"),
            html.Div("Data source: Yahoo Finance (TTM / latest available)", className="metric-title"),
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
                        html.H2("港股投资分析 Dashboard", style={"margin": "0 0 6px 0"}),
                        html.Div("港股投资分析: 价格、均线、分位数、RSI、年化收益与波动"),
                    ],
                    className="header",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("预设股票", className="metric-title"),
                                dcc.Dropdown(
                                    id="preset-stock",
                                    options=PRESET_STOCKS,
                                    value=DEFAULT_TICKER,
                                    clearable=False,
                                ),
                            ],
                            className="card",
                        ),
                        html.Div(
                            [
                                html.Div("Ticker", className="metric-title"),
                                dcc.Input(id="ticker-input", type="text", value=DEFAULT_TICKER, debounce=True, style={"width": "100%", "padding": "8px", "fontSize": "16px"}),
                            ],
                            className="card",
                        ),
                        html.Div(
                            [
                                html.Div("Quick Range", className="metric-title"),
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
                                html.Div("Date Range", className="metric-title"),
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
                html.Div(className="card", children=[dcc.Graph(id="price-chart")]),
                html.Div(style={"height": "10px"}),
                html.Div(className="card", children=[dcc.Graph(id="rsi-chart")]),
                html.Div(style={"height": "10px"}),
                html.Div(className="card", children=[dcc.Graph(id="yearly-band-chart")]),
                html.Div(style={"height": "10px"}),
                html.Div(className="card", id="yearly-stats-table"),
                html.Div(style={"height": "10px"}),
                html.Div(className="card", children=[dcc.Graph(id="drawdown-chart")]),
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
)
def update_dashboard(ticker: str, start_date: str, end_date: str):
    ticker = (ticker or DEFAULT_TICKER).strip().upper()
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()

    if start >= end:
        return [], go.Figure(), go.Figure(), go.Figure(), html.Div(), go.Figure(), html.Div(), html.Div(), "Start date must be earlier than end date."

    df = load_data(ticker, start, end)
    if df.empty:
        return [], go.Figure(), go.Figure(), go.Figure(), html.Div(), go.Figure(), html.Div(), html.Div(), "No data found. Check ticker or date range."

    latest_close = float(df["Close"].iloc[-1])
    latest_rsi = df["RSI"].iloc[-1]
    percentile = float((df["Close"] <= latest_close).mean() * 100)

    if len(df) > 1:
        daily_change = (df["Close"].iloc[-1] / df["Close"].iloc[-2] - 1) * 100
        daily_change_text = f"{daily_change:.2f}%"
    else:
        daily_change_text = "N/A"

    cards = [
        html.Div([html.Div("Latest Close", className="metric-title"), html.Div(f"{latest_close:.2f} HKD", className="metric-value")], className="card"),
        html.Div([html.Div("Percentile in History", className="metric-title"), html.Div(f"{percentile:.2f}%", className="metric-value")], className="card"),
        html.Div([html.Div("RSI(14)", className="metric-title"), html.Div("N/A" if pd.isna(latest_rsi) else f"{latest_rsi:.2f}", className="metric-value")], className="card"),
        html.Div([html.Div("Daily Change", className="metric-title"), html.Div(daily_change_text, className="metric-value")], className="card"),
    ]

    yearly_stats = compute_yearly_stats(df)
    drawdown, drawdown_stats = compute_drawdown_stats(df)

    return (
        cards,
        make_price_figure(df, ticker),
        make_rsi_figure(df),
        make_yearly_band_figure(yearly_stats),
        make_yearly_stats_table(yearly_stats),
        make_drawdown_figure(drawdown, ticker),
        make_drawdown_panel(drawdown_stats),
        make_valuation_panel(ticker),
        "",
    )


if __name__ == "__main__":
    app.run(debug=False)
