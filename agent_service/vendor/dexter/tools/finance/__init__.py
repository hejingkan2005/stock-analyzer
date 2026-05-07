"""Financial Datasets API wrapped as LangChain tools.

This is a flattened port: the TypeScript original groups several of these tools
behind LLM-routed meta-tools (``get_financials`` / ``get_market_data``). For
simplicity the Python port exposes all sub-tools directly to the agent.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ...utils.format import format_tool_result
from .api import TTL_1H, TTL_15M, TTL_24H, get, post, strip_fields_deep

REDUNDANT_FINANCIAL_FIELDS = ("accession_number", "currency", "period")
REDUNDANT_INSIDER_FIELDS = ("issuer",)


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------


class FinancialStatementsInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. 'AAPL'.")
    period: str = Field(..., description="One of 'annual', 'quarterly', 'ttm'.")
    limit: int = Field(4, description="Max number of report periods (default 4).")
    report_period_gt: Optional[str] = Field(None, description="Report period >  YYYY-MM-DD.")
    report_period_gte: Optional[str] = Field(None, description="Report period >= YYYY-MM-DD.")
    report_period_lt: Optional[str] = Field(None, description="Report period <  YYYY-MM-DD.")
    report_period_lte: Optional[str] = Field(None, description="Report period <= YYYY-MM-DD.")


def _fin_params(inp: FinancialStatementsInput) -> dict:
    return inp.model_dump(exclude_none=True)


def _income_statements(**kwargs) -> str:
    inp = FinancialStatementsInput(**kwargs)
    res = get("/financials/income-statements/", _fin_params(inp), cacheable=True, ttl_ms=TTL_24H)
    data = strip_fields_deep(res["data"].get("income_statements", []), REDUNDANT_FINANCIAL_FIELDS)
    return format_tool_result(data, [res["url"]])


def _balance_sheets(**kwargs) -> str:
    inp = FinancialStatementsInput(**kwargs)
    res = get("/financials/balance-sheets/", _fin_params(inp), cacheable=True, ttl_ms=TTL_24H)
    data = strip_fields_deep(res["data"].get("balance_sheets", []), REDUNDANT_FINANCIAL_FIELDS)
    return format_tool_result(data, [res["url"]])


def _cash_flow_statements(**kwargs) -> str:
    inp = FinancialStatementsInput(**kwargs)
    res = get("/financials/cash-flow-statements/", _fin_params(inp), cacheable=True, ttl_ms=TTL_24H)
    data = strip_fields_deep(res["data"].get("cash_flow_statements", []), REDUNDANT_FINANCIAL_FIELDS)
    return format_tool_result(data, [res["url"]])


def _all_financial_statements(**kwargs) -> str:
    inp = FinancialStatementsInput(**kwargs)
    res = get("/financials/", _fin_params(inp), cacheable=True, ttl_ms=TTL_24H)
    data = strip_fields_deep(res["data"].get("financials", []), REDUNDANT_FINANCIAL_FIELDS)
    return format_tool_result(data, [res["url"]])


get_income_statements = StructuredTool.from_function(
    func=_income_statements,
    name="get_income_statements",
    description="Fetch a company's income statements (revenues, expenses, net income) over a reporting period.",
    args_schema=FinancialStatementsInput,
)

get_balance_sheets = StructuredTool.from_function(
    func=_balance_sheets,
    name="get_balance_sheets",
    description="Fetch a company's balance sheets (assets, liabilities, equity) at points in time.",
    args_schema=FinancialStatementsInput,
)

get_cash_flow_statements = StructuredTool.from_function(
    func=_cash_flow_statements,
    name="get_cash_flow_statements",
    description="Fetch a company's cash flow statements (operating, investing, financing).",
    args_schema=FinancialStatementsInput,
)

get_all_financial_statements = StructuredTool.from_function(
    func=_all_financial_statements,
    name="get_all_financial_statements",
    description="Fetch income, balance sheet, and cash flow statements together. Use only when multiple types are needed.",
    args_schema=FinancialStatementsInput,
)


# ---------------------------------------------------------------------------
# Key ratios / metrics
# ---------------------------------------------------------------------------


class TickerOnlyInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. 'AAPL'.")


class HistoricalRatiosInput(FinancialStatementsInput):
    pass


def _key_ratios(ticker: str) -> str:
    res = get("/financials/metrics/snapshot/", {"ticker": ticker.upper()})
    return format_tool_result(res["data"].get("snapshot", {}), [res["url"]])


def _historical_key_ratios(**kwargs) -> str:
    inp = HistoricalRatiosInput(**kwargs)
    params = _fin_params(inp)
    res = get("/financials/metrics/", params, cacheable=True, ttl_ms=TTL_24H)
    return format_tool_result(res["data"].get("financial_metrics", []), [res["url"]])


get_key_ratios = StructuredTool.from_function(
    func=_key_ratios,
    name="get_financial_metrics_snapshot",
    description="Latest snapshot of financial metrics: P/E, EPS, ROE, margins, market cap, etc.",
    args_schema=TickerOnlyInput,
)

get_historical_key_ratios = StructuredTool.from_function(
    func=_historical_key_ratios,
    name="get_key_ratios",
    description="Historical financial metrics over multiple reporting periods (P/E, ROE, margins, etc.).",
    args_schema=HistoricalRatiosInput,
)


# ---------------------------------------------------------------------------
# Analyst estimates / segments / earnings
# ---------------------------------------------------------------------------


class EstimatesInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol.")
    period: str = Field("annual", description="'annual' or 'quarterly'.")
    limit: int = Field(4, description="Max number of periods.")


def _analyst_estimates(**kwargs) -> str:
    inp = EstimatesInput(**kwargs)
    res = get("/financials/estimates/", inp.model_dump(exclude_none=True), cacheable=True, ttl_ms=TTL_1H)
    return format_tool_result(res["data"].get("estimates", []), [res["url"]])


get_analyst_estimates = StructuredTool.from_function(
    func=_analyst_estimates,
    name="get_analyst_estimates",
    description="Wall-Street consensus estimates for revenue, EPS, EBITDA, and price targets.",
    args_schema=EstimatesInput,
)


def _financial_segments(ticker: str) -> str:
    res = get("/financials/segments/", {"ticker": ticker.upper()}, cacheable=True, ttl_ms=TTL_24H)
    return format_tool_result(res["data"].get("segments", []), [res["url"]])


get_financial_segments = StructuredTool.from_function(
    func=_financial_segments,
    name="get_financial_segments",
    description="Revenue / margin breakdowns by product line or geography.",
    args_schema=TickerOnlyInput,
)


def _earnings(ticker: str) -> str:
    res = get("/earnings/", {"ticker": ticker.upper()}, cacheable=True, ttl_ms=TTL_1H)
    return format_tool_result(res["data"].get("earnings", []), [res["url"]])


get_earnings = StructuredTool.from_function(
    func=_earnings,
    name="get_earnings",
    description="Most recent earnings release: actual vs expected EPS / revenue, surprises.",
    args_schema=TickerOnlyInput,
)


# ---------------------------------------------------------------------------
# Prices (stock + crypto)
# ---------------------------------------------------------------------------


class StockPricesInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol.")
    interval: str = Field("day", description="'day' / 'week' / 'month' / 'year'.")
    start_date: str = Field(..., description="YYYY-MM-DD.")
    end_date: str = Field(..., description="YYYY-MM-DD.")


def _stock_price(ticker: str) -> str:
    res = get("/prices/snapshot/", {"ticker": ticker.upper()})
    return format_tool_result(res["data"].get("snapshot", {}), [res["url"]])


def _stock_prices(**kwargs) -> str:
    inp = StockPricesInput(**kwargs)
    res = get(
        "/prices/",
        {
            "ticker": inp.ticker.upper(),
            "interval": inp.interval,
            "start_date": inp.start_date,
            "end_date": inp.end_date,
        },
        cacheable=True,
        ttl_ms=TTL_24H,
    )
    return format_tool_result(res["data"].get("prices", []), [res["url"]])


def _stock_tickers() -> str:
    res = get("/prices/snapshot/tickers/", {}, cacheable=True, ttl_ms=TTL_24H)
    return format_tool_result(res["data"].get("tickers", []), [res["url"]])


class _NoArgs(BaseModel):
    pass


get_stock_price = StructuredTool.from_function(
    func=_stock_price,
    name="get_stock_price",
    description="Current stock price snapshot (price, market cap, volume, 52-week high/low).",
    args_schema=TickerOnlyInput,
)

get_stock_prices = StructuredTool.from_function(
    func=_stock_prices,
    name="get_stock_prices",
    description="Historical stock OHLCV over a date range.",
    args_schema=StockPricesInput,
)

get_stock_tickers = StructuredTool.from_function(
    func=lambda: _stock_tickers(),
    name="get_available_stock_tickers",
    description="List of all stock tickers supported by the price tools.",
    args_schema=_NoArgs,
)


def _crypto_snapshot(ticker: str) -> str:
    res = get("/crypto/prices/snapshot/", {"ticker": ticker.upper()})
    return format_tool_result(res["data"].get("snapshot", {}), [res["url"]])


def _crypto_prices(**kwargs) -> str:
    inp = StockPricesInput(**kwargs)
    res = get(
        "/crypto/prices/",
        {
            "ticker": inp.ticker.upper(),
            "interval": inp.interval,
            "start_date": inp.start_date,
            "end_date": inp.end_date,
        },
        cacheable=True,
        ttl_ms=TTL_24H,
    )
    return format_tool_result(res["data"].get("prices", []), [res["url"]])


def _crypto_tickers() -> str:
    res = get("/crypto/prices/snapshot/tickers/", {}, cacheable=True, ttl_ms=TTL_24H)
    return format_tool_result(res["data"].get("tickers", []), [res["url"]])


get_crypto_price_snapshot = StructuredTool.from_function(
    func=_crypto_snapshot,
    name="get_crypto_price_snapshot",
    description="Current cryptocurrency price snapshot.",
    args_schema=TickerOnlyInput,
)

get_crypto_prices = StructuredTool.from_function(
    func=_crypto_prices,
    name="get_crypto_prices",
    description="Historical cryptocurrency OHLCV over a date range.",
    args_schema=StockPricesInput,
)

get_crypto_tickers = StructuredTool.from_function(
    func=lambda: _crypto_tickers(),
    name="get_available_crypto_tickers",
    description="List of all crypto tickers supported by the price tools.",
    args_schema=_NoArgs,
)


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------


class NewsInput(BaseModel):
    ticker: Optional[str] = Field(None, description="Ticker for company news; omit for broad market news.")
    limit: int = Field(5, description="Max articles (default 5, hard-capped at 10).")


def _company_news(**kwargs) -> str:
    inp = NewsInput(**kwargs)
    params: dict = {"limit": min(inp.limit, 10)}
    if inp.ticker:
        params["ticker"] = inp.ticker.upper()
    res = get("/news", params, cacheable=True, ttl_ms=TTL_15M)
    return format_tool_result(res["data"].get("news", []), [res["url"]])


get_company_news = StructuredTool.from_function(
    func=_company_news,
    name="get_company_news",
    description="Recent news headlines (title, source, date, URL). Pass ticker for company-specific news; omit for broad market news.",
    args_schema=NewsInput,
)


# ---------------------------------------------------------------------------
# Insider trades
# ---------------------------------------------------------------------------


class InsiderTradesInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker.")
    limit: int = Field(10, description="Max trades (default 10, max 1000).")
    filing_date: Optional[str] = Field(None, description="Exact filing date YYYY-MM-DD.")
    filing_date_gte: Optional[str] = Field(None, description="Filing date >= YYYY-MM-DD.")
    filing_date_lte: Optional[str] = Field(None, description="Filing date <= YYYY-MM-DD.")
    filing_date_gt: Optional[str] = Field(None, description="Filing date >  YYYY-MM-DD.")
    filing_date_lt: Optional[str] = Field(None, description="Filing date <  YYYY-MM-DD.")
    name: Optional[str] = Field(None, description="Filter by insider name.")


def _insider_trades(**kwargs) -> str:
    inp = InsiderTradesInput(**kwargs)
    params = inp.model_dump(exclude_none=True)
    params["ticker"] = params["ticker"].upper()
    res = get("/insider-trades/", params, cacheable=True, ttl_ms=TTL_1H)
    data = strip_fields_deep(res["data"].get("insider_trades", []), REDUNDANT_INSIDER_FIELDS)
    return format_tool_result(data, [res["url"]])


get_insider_trades = StructuredTool.from_function(
    func=_insider_trades,
    name="get_insider_trades",
    description="Insider trading activity (Form 4) for a ticker.",
    args_schema=InsiderTradesInput,
)


# ---------------------------------------------------------------------------
# SEC filings
# ---------------------------------------------------------------------------


class FilingsInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker.")
    filing_type: Optional[str] = Field(None, description="'10-K', '10-Q', '8-K' (omit for all).")
    limit: int = Field(5, description="Max filings.")


def _filings(**kwargs) -> str:
    inp = FilingsInput(**kwargs)
    params: dict = {"ticker": inp.ticker.upper(), "limit": inp.limit}
    if inp.filing_type:
        params["filing_type"] = inp.filing_type
    res = get("/filings/", params, cacheable=True, ttl_ms=TTL_1H)
    return format_tool_result(res["data"].get("filings", []), [res["url"]])


read_filings = StructuredTool.from_function(
    func=_filings,
    name="read_filings",
    description="List SEC filings (10-K, 10-Q, 8-K) for a ticker. Returns metadata + URLs; use web_fetch on a URL to read the body.",
    args_schema=FilingsInput,
)


# ---------------------------------------------------------------------------
# Stock screener
# ---------------------------------------------------------------------------


class ScreenerInput(BaseModel):
    filters: dict = Field(
        ...,
        description="Filter object, e.g. {'market_cap': {'gte': 10_000_000_000}, 'pe_ratio': {'lte': 25}}.",
    )
    sort_by: Optional[str] = Field(None, description="Field to sort by (e.g. 'market_cap').")
    sort_order: Optional[str] = Field("desc", description="'asc' or 'desc'.")
    limit: int = Field(20, description="Max results (default 20).")


def _screener(**kwargs) -> str:
    inp = ScreenerInput(**kwargs)
    body = {
        "filters": inp.filters,
        "limit": inp.limit,
    }
    if inp.sort_by:
        body["sort_by"] = inp.sort_by
        body["sort_order"] = inp.sort_order or "desc"
    res = post("/financials/search/screener/", body)
    return format_tool_result(res["data"].get("results", []), [res["url"]])


screen_stocks = StructuredTool.from_function(
    func=_screener,
    name="stock_screener",
    description="Screen stocks by financial criteria (market cap, P/E, growth rates, margins, etc.).",
    args_schema=ScreenerInput,
)


# Public list used by the registry
ALL_FINANCE_TOOLS = [
    get_income_statements,
    get_balance_sheets,
    get_cash_flow_statements,
    get_all_financial_statements,
    get_key_ratios,
    get_historical_key_ratios,
    get_analyst_estimates,
    get_financial_segments,
    get_earnings,
    get_stock_price,
    get_stock_prices,
    get_stock_tickers,
    get_crypto_price_snapshot,
    get_crypto_prices,
    get_crypto_tickers,
    get_company_news,
    get_insider_trades,
    read_filings,
    screen_stocks,
]
