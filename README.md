# Company News Fetcher

定時搜尋台股與美股個股新聞，寫入 PostgreSQL 的 `company_news` 資料表。股票池會從 TWSE、TPEx 與 Nasdaq Trader 官方資料自動同步，並分批輪詢，適合處理數千檔股票。

新聞會進行二次相關性驗證：標題包含公司名稱或完整股票代號時直接收錄；否則下載原文並檢查正文。標題與正文都未命中，或正文無法解析時，不會寫入資料庫。

新聞來源採財經媒體白名單，只收錄 `.env` 的 `ALLOWED_NEWS_SOURCES`。內建名單包含國內的經濟日報、工商時報、鉅亨、MoneyDJ、Yahoo 股市、財訊快報等，以及 Reuters、Bloomberg、CNBC、MarketWatch、WSJ、Financial Times、Yahoo Finance 等國際財經媒體。來源名稱採不分大小寫的部分比對，可直接從環境變數增減：

```env
ALLOWED_NEWS_SOURCES=經濟日報,工商時報,MoneyDJ理財網,Reuters,Bloomberg,CNBC,Yahoo Finance
```

## 快速啟動

1. 複製環境設定：

   ```powershell
   Copy-Item .env.example .env
   ```

2. 可選擇編輯 `.env` 的 `STOCKS`，加入官方清單以外的自選股票：

   ```env
   STOCKS=TW:2330:台積電,TW:2317:鴻海,US:AAPL:Apple,US:NVDA:NVIDIA
   ```

3. 啟動 PostgreSQL 與排程器：

   ```powershell
   docker compose up --build -d
   docker compose logs -f fetcher
   ```

服務會自動建立 `companies` 與 `company_news`。啟動時同步完整股票池，每天 03:00 更新；每 30 分鐘選出最久未處理的 100 檔股票。調整 `FETCH_BATCH_SIZE` 與 `FETCH_INTERVAL_MINUTES` 可控制吞吐量。

每輪結束後會依市場與股票代號分組，只保留最新 20 則新聞；排序優先使用新聞發布時間，沒有發布時間時使用擷取時間。可透過以下設定調整：

```env
MAX_NEWS_PER_STOCK=20
```

以預設值估算，一天處理 4,800 檔。大量查詢可能觸發來源限流，建議依實際執行情況降低批次大小或增加間隔。

## 手動執行一次

容器已啟動時：

```powershell
docker compose run --rm fetcher company-news once
```

只更新股票池：

```powershell
docker compose run --rm fetcher company-news sync-universe
```

不使用 Docker 時，需先準備 PostgreSQL，並把 `DATABASE_URL` 的主機改為 `localhost`：

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
Copy-Item .env.example .env
.venv\Scripts\company-news once
```

`postgresql://` 與 `postgres://` 連線字串會自動使用 psycopg 3；也可以明確寫成 `postgresql+psycopg://`。

若使用 `requirements.txt` 安裝而非安裝專案本身，請改用模組方式執行：

```powershell
.venv\Scripts\python -m app.main once
```

## 資料欄位

`companies` 保存市場、代號、名稱、交易所、啟用狀態與最後擷取時間，排程依最後擷取時間公平輪詢。`company_news` 保存新聞內容；同一股票不會重複寫入同一網址。

## 注意事項

- Google News RSS 適合作為免 API Key 的起點；正式商用前應確認來源條款，或替換成授權新聞 API。
- RSS 的連結可能是 Google News 轉址，仍可穩定去重，但若需要原始媒體網址，可再加入轉址解析。
- 資料量變大後，若希望文章內容只保存一次，可再拆成 `news_articles` 與 `article_companies` 兩張表。
