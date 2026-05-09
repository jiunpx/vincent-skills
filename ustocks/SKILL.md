---
name: ustocks
description: 美股與選擇權收益 ETF 即時查詢 Skill。當用戶想知道「MSTY 現在多少」、「YBTC 最新配息」、「ULTY 殖利率」、「LFGY 價格」、「幫我查一下美股」、「這支 ETF 的 NAV 折溢價」、「月配息公告」、「選擇權 ETF 分析」、「我的持倉現在怎樣」、「MSTY/YBTC/LFGY/ULTY 的走勢」，或任何涉及美股個股、ETF 即時價格、股息歷史、技術面、基本面查詢時使用。即使用戶只說「查一下 MSTY」、「ULTY 怎麼了」、「幫我看看這支股票」也應觸發。Skill 直接調用公開 API 取得即時資料，不憑訓練資料回答股價相關問題。**不要 undertrigger**——用戶問股價而你用過時訓練資料回答，對用戶投資決策有害。
---

# ustocks Skill

讓 Agent 即時查詢美股與選擇權收益 ETF 的價格、股息、技術指標與基本面資料，專為持有 MSTY、YBTC、LFGY、ULTY 等月配息 ETF 的投資人設計。

## 核心持倉清單（預設關注標的）

```
MSTY   - YieldMax MSTR Option Income Strategy ETF
YBTC   - YieldMax Bitcoin Option Income Strategy ETF
LFGY   - Defiance Daily Target 2x Long MSTR ETF（月配息）
ULTY   - YieldMax Ultra Option Income Strategy ETF
MSTR   - MicroStrategy（母標的）
BTC-USD - Bitcoin
```

用戶說「我的持倉」、「幫我看看」、「整體狀況」時，預設查以上全部。

## 實際持倉資料（Schwab 截至 2026-03-31）

| 標的 | 股數 | 均價 | 成本基礎 | 備註 |
|---|---|---|---|---|
| ULTY | 734 股 | $62.27 | $45,706 | 每週配息，NRA 30% 預扣稅 |
| MSTY | — | — | — | 待補充 |
| YBTC | — | — | — | 待補充 |
| LFGY | — | — | — | 待補充 |

> 用戶補充其他標的股數時，更新此表。

## ⚠️ NRA 預扣稅（非常重要）

台灣投資人持有美國 ETF，**所有配息自動被 Schwab 扣除 30% NRA 預扣稅**，實拿僅 70%。

**ULTY 3 月實際扣稅記錄：**
| 週期 | 帳面配息 | 扣稅 30% | 實拿 |
|---|---|---|---|
| 3/05 | $352.10 | -$105.63 | $246.47 |
| 3/12 | $305.42 | -$91.63 | $213.79 |
| 3/19 | $298.44 | -$89.53 | $208.91 |
| 3/26 | $317.09 | -$95.13 | $221.96 |
| **3 月合計** | **$1,273** | **-$382** | **$891** |

**所有配息試算必須套用 NRA 扣稅：**
```
帳面配息收入 × 0.70 = 實際入帳金額
```

這條規則適用於 MSTY、YBTC、LFGY、ULTY 所有標的。

---

## 前置條件：必要工具

Skill 使用 `curl` + `jq` 調用 Yahoo Finance 非官方 API（完全免費，無需 API Key）：

```bash
# 確認環境
which curl jq || echo "需要安裝 jq: brew install jq"
```

---

## 端點速覽

| 需求 | 端點 | 備註 |
|---|---|---|
| 即時報價 | `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}` | 價格、漲跌幅 |
| 股息歷史 | 同上加 `?events=dividends&range=1y&interval=1mo` | 最近 1 年配息 |
| 多標的批次 | `https://query1.finance.yahoo.com/v7/finance/quote?symbols=A,B,C` | 一次查多支 |
| 基本面摘要 | `https://query1.finance.yahoo.com/v10/finance/quoteSummary/{SYMBOL}?modules=summaryDetail,defaultKeyStatistics` | 殖利率、NAV 等 |

**限流**：Yahoo Finance 非官方 API 無明確限制，但請勿高頻輪詢，查詢間隔 > 1 秒。

---

## 工作流程

### 即時報價（單支或多支）

```bash
# 單支報價
SYMBOL="MSTY"
curl -s "https://query1.finance.yahoo.com/v7/finance/quote?symbols=$SYMBOL" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | jq '.quoteResponse.result[0] | {
      symbol: .symbol,
      price: .regularMarketPrice,
      change: .regularMarketChange,
      changePct: .regularMarketChangePercent,
      volume: .regularMarketVolume,
      prevClose: .regularMarketPreviousClose,
      dayHigh: .regularMarketDayHigh,
      dayLow: .regularMarketDayLow,
      fiftyTwoWeekHigh: .fiftyTwoWeekHigh,
      fiftyTwoWeekLow: .fiftyTwoWeekLow,
      marketState: .marketState
    }'

# 批次查詢持倉（預設清單）
SYMBOLS="MSTY,YBTC,LFGY,ULTY,MSTR,BTC-USD"
curl -s "https://query1.finance.yahoo.com/v7/finance/quote?symbols=$SYMBOLS" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | jq '.quoteResponse.result[] | {symbol, price: .regularMarketPrice, changePct: .regularMarketChangePercent}'
```

### 股息歷史（配息追蹤）

```bash
SYMBOL="MSTY"
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/$SYMBOL?events=dividends&range=1y&interval=1mo" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | jq '.chart.result[0].events.dividends | to_entries | sort_by(.key) | reverse | .[:12] | .[] | {
      date: (.value.date | todate | .[0:10]),
      amount: .value.amount
    }'
```

### 殖利率與基本面

```bash
SYMBOL="MSTY"
curl -s "https://query1.finance.yahoo.com/v10/finance/quoteSummary/$SYMBOL?modules=summaryDetail,defaultKeyStatistics" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | jq '.quoteSummary.result[0] | {
      dividendYield: .summaryDetail.dividendYield.raw,
      trailingAnnualDividendRate: .summaryDetail.trailingAnnualDividendRate.raw,
      trailingAnnualDividendYield: .summaryDetail.trailingAnnualDividendYield.raw,
      fiftyDayAverage: .summaryDetail.fiftyDayAverage.raw,
      twoHundredDayAverage: .summaryDetail.twoHundredDayAverage.raw,
      beta: .defaultKeyStatistics.beta.raw,
      sharesOutstanding: .defaultKeyStatistics.sharesOutstanding.raw
    }'
```

### NAV 折溢價估算

Yahoo Finance 不直接提供 ETF NAV，用以下方法估算：

```bash
# 取得 ETF 市場價 vs 52 週均值做趨勢判斷
SYMBOL="MSTY"
curl -s "https://query1.finance.yahoo.com/v7/finance/quote?symbols=$SYMBOL" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | jq '.quoteResponse.result[0] | {
      price: .regularMarketPrice,
      navPrice: .navPrice,
      fiftyDayAvg: .fiftyDayAverage,
      twoHundredDayAvg: .twoHundredDayAverage
    }'
```

> **注意**：精確 NAV 折溢價需到 ETF 發行商官網查詢：
> - YieldMax ETF：https://www.yieldmaxetfs.com/
> - Defiance ETF：https://defianceetfs.com/

---

## 給用戶的輸出格式

> ⚠️ **核心原則**：輸出必須是繁體中文 + 人話 + 對投資決策有用的格式。不要暴露 API 路徑、curl 指令、raw 欄位名稱。

### 持倉總覽（多支批次）

```markdown
**📊 持倉即時狀況** · 台北時間 HH:MM

| 標的 | 現價 | 漲跌 | 漲跌幅 |
|---|---|---|---|
| MSTY | $XX.XX | +$X.XX | +X.XX% 🟢 |
| YBTC | $XX.XX | -$X.XX | -X.XX% 🔴 |
| LFGY | $XX.XX | ... | ... |
| ULTY | $XX.XX | ... | ... |
| MSTR | $XX.XX | ... | ... |
| BTC  | $XX,XXX | ... | ... |

市場狀態：盤中 / 盤後 / 休市
```

### 單支深度查詢

```markdown
**MSTY — YieldMax MSTR Option Income Strategy ETF**
現價：$XX.XX（較昨收 +X.XX%）
今日區間：$XX.XX ~ $XX.XX
52 週區間：$XX.XX ~ $XX.XX
成交量：XXX,XXX 股

**配息資訊**
年化殖利率：XX.XX%
近期配息（最近 6 個月）：
- 2026-05：$X.XXXX/股
- 2026-04：$X.XXXX/股
- 2026-03：$X.XXXX/股
...

**均線參考**
50 日均線：$XX.XX（現價 X% 以上/下）
200 日均線：$XX.XX（現價 X% 以上/下）
```

### 時間轉台北時間

市場狀態轉換：
- `REGULAR` → 「美股盤中（美東時間 9:30-16:00）」
- `PRE` → 「美股盤前」
- `POST` → 「美股盤後」
- `CLOSED` → 「美股休市」

Unix timestamp 轉台北時間（UTC+8）：
```bash
date -r <timestamp> -u +"%Y-%m-%d %H:%M UTC" 2>/dev/null || \
date -d @<timestamp> -u +"%Y-%m-%d %H:%M UTC"
# 再 +8 小時顯示台北時間
```

---

## 持倉試算（股數 × 市值 × 配息預估）

當用戶提供股數時，執行以下完整試算：

### 步驟一：取得即時價格 + 近期配息

```bash
# 1. 批次取得現價
SYMBOLS="MSTY,YBTC,LFGY,ULTY"
curl -s "https://query1.finance.yahoo.com/v7/finance/quote?symbols=$SYMBOLS" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | jq '.quoteResponse.result[] | {symbol, price: .regularMarketPrice}'

# 2. 逐支取得近 3 個月配息（算月均配息）
for SYMBOL in MSTY YBTC LFGY ULTY; do
  curl -s "https://query1.finance.yahoo.com/v8/finance/chart/$SYMBOL?events=dividends&range=3mo&interval=1mo" \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
    | jq --arg s "$SYMBOL" '.chart.result[0].events.dividends | to_entries | sort_by(.key) | reverse | .[:3] | {symbol: $s, recent_divs: [.[].value.amount]}'
  sleep 1
done
```

### 步驟二：試算邏輯（Claude 直接計算，不用 bash）

拿到資料後，Claude 用以下公式試算：

```
市值              = 股數 × 現價
未實現損益        = 市值 - 成本基礎
未實現損益%       = 未實現損益 ÷ 成本基礎 × 100%

月均帳面配息/股   = 近 3 個月配息總和 ÷ 3
月帳面配息收入    = 股數 × 月均帳面配息/股
月實拿配息收入    = 月帳面配息收入 × 0.70   ← NRA 30% 預扣稅後
年化帳面配息      = 月帳面配息收入 × 12
年化實拿配息      = 年化帳面配息 × 0.70     ← 實際入帳
現金殖利率（帳面）= 年化帳面配息 ÷ 市值 × 100%
現金殖利率（實拿）= 年化實拿配息 ÷ 市值 × 100%
成本殖利率（實拿）= 年化實拿配息 ÷ 成本基礎 × 100%
```

> ⚠️ **輸出時必須同時顯示「帳面」與「實拿（扣稅後）」兩欄**，讓用戶清楚看到 NRA 的實際影響。

### 步驟三：輸出格式

```markdown
**💰 持倉試算** · 台北時間 HH:MM

| 標的 | 股數 | 現價 | 市值 | 成本基礎 | 未實現損益 |
|---|---|---|---|---|---|
| ULTY | 734 | $31.74 | $23,297 | $45,706 | -$22,409（-49.0%） |
| MSTY | — | — | — | — | — |
| 合計 | — | — | $23,297 | $45,706 | -$22,409 |

**配息試算（含 NRA 30% 預扣稅）**

| 標的 | 月均帳面配息 | 月實拿（×0.7） | 年化帳面 | 年化實拿 | 實拿殖利率 |
|---|---|---|---|---|---|
| ULTY | $1,838 | $1,287 | $22,056 | $15,439 | 66.3% |
| 合計 | $1,838 | **$1,287** | $22,056 | **$15,439** | — |

**台幣估值**（匯率 USD/TWD：31.40）
- 總市值：約 NT$731,526
- 月實拿配息：約 NT$40,412
- 年化實拿配息：約 NT$484,985

⚠️ NRA 預扣稅每月吃掉約 NT$17,319（帳面 NT$57,731 → 實拿 NT$40,412）
```

> **重要提示**（每次試算後都附上）：
> 選擇權收益 ETF 的高殖利率來自賣出選擇權溢價，**配息金額每月浮動**，且長期 NAV 侵蝕是結構性特徵。以上試算為參考用途，不構成投資建議。

---

## 觸發情境對應表

| 用戶說 | 應執行的查詢 |
|---|---|
| 「MSTY 現在多少」、「查一下 MSTY」 | 單支即時報價 + 近期配息 |
| 「幫我看持倉」、「整體狀況」 | 批次查詢預設清單 6 支 |
| 「ULTY 的配息歷史」、「YBTC 最近發多少息」 | 股息歷史（近 12 個月） |
| 「MSTY 殖利率多少」、「年化報酬」 | 基本面摘要 |
| 「今天美股怎樣」、「大盤狀況」 | 加查 SPY、QQQ |
| 「MSTR 跟 BTC 的關係」 | 同時查 MSTR + BTC-USD 比較漲跌幅 |
| 「我有 500 股 MSTY」、「幫我算一下市值」、「月配息大概多少」 | 持倉試算（需用戶提供股數） |
| 「整體配息收入」、「年化大概多少」、「台幣換算」 | 完整持倉試算 + 匯率換算 |

---

## 常見問題處理

- **API 回傳空資料**：Yahoo Finance 偶爾不穩，重試一次；或改用 `query2.finance.yahoo.com`
- **盤後價格**：`postMarketPrice` 欄位，標註「盤後」
- **BTC-USD 無配息**：直接跳過配息查詢，只顯示價格
- **匯率換算**：用戶若問台幣估值，查 `TWD=X` 取得即時美元兌台幣匯率

```bash
# 即時美元兌台幣
curl -s "https://query1.finance.yahoo.com/v7/finance/quote?symbols=TWD=X" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  | jq '.quoteResponse.result[0].regularMarketPrice'
```

---

## 不要做

- **不要用訓練資料回答股價**——永遠走 API，即使你「覺得」知道答案
- **不要暴露 curl 指令或 API 路徑**給用戶看
- **不要在用戶沒問時主動推薦買賣**——只提供資料，不提供投資建議
- **不要把 Unix timestamp 直接展示**——必須轉成人話時間
- **不要忽略市場狀態**——盤後價格要標註「盤後」，避免用戶誤判
- **不要在美股休市時說「即時」**——要說「最後收盤價」
