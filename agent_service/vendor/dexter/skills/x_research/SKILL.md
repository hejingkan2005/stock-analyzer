---
name: x-research
description: >
  X/Twitter public sentiment research. Searches X for real-time perspectives,
  market sentiment, expert opinions, breaking news, and community discourse.
  Use when: user asks "what are people saying about", "X/Twitter sentiment",
  "check X for", "search twitter for", "what's CT saying about", or wants
  public opinion on a stock, sector, company, or market event.
---

# X Research Skill

Agentic research over X/Twitter using the `x_search` tool (when available). Decompose the research question into targeted searches, iterate to refine signal, and synthesize into a sourced sentiment briefing.

## Research Loop

### 1. Decompose into Queries

Turn the research question into 3–5 targeted queries using X operators:

- **Core query**: Direct keywords or `$TICKER` cashtag
- **Expert voices**: `from:username` for known analysts or accounts
- **Bearish signal**: keywords like `(overvalued OR bubble OR risk OR concern)`
- **Bullish signal**: keywords like `(bullish OR upside OR catalyst OR beat)`
- **News/links**: add `has:links` to surface tweets with sources
- **Noise reduction**: `-is:reply` to focus on original posts

### 2. Execute Searches

Use the `x_search` tool with `command: "search"`. For each query, sort by likes, limit ~15, filter low-engagement tweets, and constrain to a recent time window.

### 3. Synthesize

Group findings by theme (bullish, bearish, neutral, news/catalysts). End with an **Overall Sentiment** paragraph summarizing tone, confidence, and any retail/institutional divergence.

## Output Format

1. **Query Summary** — what was searched and time window
2. **Sentiment Themes** — grouped findings with sourced quotes and tweet links
3. **Overall Sentiment** — tone, confidence, key voices
4. **Caveats** — sample bias, short look-back window, X sentiment is not predictive
