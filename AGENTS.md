# AGENTS.md — CivicLens 交接與作業規範

> 本文件為任何接手本專案的 AI 代理或人員而寫。內文以臺灣正體中文撰寫；指令、檔名與網址維持原文。
> This file is the handover guide for any AI agent or person taking over the project. It is written in Traditional Chinese (Taiwan); commands and paths are literal.

## 1. 專案是什麼、現在在哪裡

- **CivicLens**（https://civiclens.eugeneyip.net/ ，GitHub `EugeneYip/civiclens`）是中立的選舉資訊靜態網站，部署於 GitHub Pages，main 分支即正式網站。
- **2026-11-28 選舉已結束，網站處於「歷史紀錄」模式**（V0.1.88 起）：
  - 全部 18,248 個投票所已開票完成（中選會 11/29 00:10）。
  - 中選會計票網站已於 00:21 標示全部 941 席當選人，本站依其「註記」顯示當選。
  - 正式當選以中選會審定公告為準。
- 最早的下一場：**2028 年 1 月總統副總統及立法委員選舉**。沿用方式見 `docs/ELECTION_PLAYBOOK.md` 第七節。

## 2. 開工前必讀（依序）

1. 本文件。
2. `docs/ELECTION_PLAYBOOK.md`：完整作業手冊，包括原則、時程、官方來源、轉錄、開票夜、地圖、事故與教訓、沿用要點。
3. `docs/METHODOLOGY.md`：資料與查核規格，記錄每一類資料的來源與限制。
4. `CHANGELOG.md` 最後幾版：了解最近的變更。

## 3. 不可違反的原則

- **只用官方或可追溯來源**：中選會、選委會、法規資料庫、內政部。第三方資料只能輔助，且須標示來源與限制。
- **不推測**：
  - 不估算、不補值。
  - 當選以中選會標示為準。只有全部投票所送達後，才可依法規顯示「預計當選」，而且原住民選區不可逐區推估（婦女保障名額為全縣合併計算）。
  - 未取得的資料寫「尚未」，不寫「沒有」。
- **逐字與如實**：公報政見逐字轉錄。無法辨讀的公報要說明原因，不可猜字。
- **隱私**：私人電話與服務處地址不轉錄；身分證樣式字串一律擋下；原始轉錄檔不提交。
- **中立**：同意與不同意、各政黨採相同樣式；用語不帶立場。
- **驗證後才發布**：
  1. 單元測試與瀏覽器測試通過。
  2. 提交並推送開發分支。
  3. GitHub Actions 通過。
  4. 快轉 main。
  5. 實測正式網站，確認檔案與提交版本逐位元組相符。
- **不規避存取限制**：網站拒絕連線時（例如 403），不得偽造標頭繞過，應改用其他官方或可追溯來源。
- **對外文字**：網站內容與回報一律使用正式臺灣正體中文，嚴禁簡體字及大陸用語。

## 4. 環境與指令

```bash
python3 scripts/build.py                      # 由 scripts/template.html 產生 index.html（必須提交產生結果）
python3 -m unittest discover -s tests -v      # 單元測試（CI 同此指令；本機亦可用 python3 -m pytest -q）
node tests/test_results.cjs                   # 結果頁邏輯測試
python3 scripts/build_county_shards.py --check && python3 scripts/build_party_summary.py --check && python3 scripts/audit_coverage.py
```

瀏覽器測試需要 playwright-core 與 Chrome 或 Chromium，並先在本機啟動 HTTP 伺服器：

```bash
python3 -m http.server 8765 --bind 127.0.0.1 &
```

```bash
CHROME_BIN=/path/to/chrome node tests/browser_smoke.cjs
```

部署（commit 已推送至開發分支）：

```bash
scripts/ops/deploy.sh <SHA> index.html VERSION    # 等候 CI → 快轉 main → 輪詢正式網站，直到逐位元組相符
```

- **下載檔視為不可信資料**：每批放在獨立目錄，路徑以參數傳入，以 `python3 -I` 執行。
- **CI**（`.github/workflows/validate.yml`、`browser-smoke.yml`）：執行上述測試，並檢查 `index.html` 與建置結果一致。

## 5. 修改時的固定步驟

1. 修改原始檔（`scripts/template.html`、`scripts/*.js`、`scripts/style.css`、`data/*.json` 或產生器），**不要直接手改產生檔**：
   - `index.html` 由 `scripts/build.py` 產生。
   - `data/county/*.json` 由 `scripts/build_county_shards.py` 產生。
   - `data/results-map.json` 由 `scripts/build_results_map.py` 產生。
   - `data/council-maps/`、`data/taiwan-counties-map.json` 由地圖建置腳本產生。
2. 版本號：`VERSION`、`CHANGELOG.md` 新增一節、`README.md` 第 5 行。
   - `explorer.js?v=` 由 build 自動帶入。
   - `results.html`、`districts.html`、`gazettes.html` 內的 `reader.css?v=`、`results.js?v=` 需手動遞增，以避免瀏覽器快取。
3. 新增或調整功能時同步增修 `tests/`：Python 單元測試與 `tests/browser_smoke.cjs`。瀏覽器測試會擋下所有外部連線。
4. 在手機寬度 360/390/430 與桌面 1280 截圖檢視，確認無橫向溢出、無主控台錯誤，並以 axe 檢測無障礙。
5. 提交訊息使用英文祈使句，說明原因；分支依專案設定（2026 年為 `claude/gallant-newton-t611xj`），CI 通過後才快轉 main。

## 6. 主要檔案地圖

| 區塊 | 檔案 |
|---|---|
| 首頁 | `scripts/template.html` → `index.html`；`scripts/app.js`（倒數、開票地圖、公投開票）、`scripts/explorer.js`（候選人、比較、公報）、`scripts/phrase.js`（依詞斷行）、`scripts/style.css` |
| 其他頁 | `results.html` + `scripts/results.js`（結果、議員選區地圖）、`districts.html`、`gazettes.html`、`assets/reader.css` |
| 候選人資料 | `data/published-roster.json`、`data/national-roster-supplement.json`、`data/county/*.json`（分片） |
| 政見 | `data/chief-bulletin-policies.json`、`data/council-bulletin-policies.json`、`data/reviewed-council-policies.json`；工具 `scripts/transcription/`；指令範本 `docs/playbook/transcription-prompt.md` |
| 公投 | `data/referendum.json`（`scripts/build.py` 的 `render_ref`）、`data/referendum-result.json` |
| 開票 | `scripts/adapt_cec_vote.py` → `scripts/build_results_snapshot.py` → `data/results-snapshot.json`；`scripts/build_results_map.py`；`scripts/ops/refresh_results.sh` |
| 地圖 | `scripts/build_map_geometry.py`、`scripts/build_council_maps.py`（圖資：taiwan-atlas，源自內政部國土測繪中心） |
| 預覽圖 | `assets/og-image.png`（1200×630，以 HTML 渲染產生；不含政黨顏色） |

## 7. 已知陷阱（摘要，詳見手冊第六節）

- **CID 字型**：poppler 會把部分 CID 字型渲染成空白，轉錄覆核必須以 pdfium 交叉比對。
- **計票網站解析**：
  - 表頭規則須寫 `<th\b`，避免誤抓 `<thead>`。
  - 最終階段時間標籤會從「資料更新時間」改為「資料時間」。
  - 「註記」欄：◎ 當選、● 婦女保障當選、- 排擠、? 同票待抽籤、＜ 未達最低當選票數。
- **地圖**：圖形須保留內環（例如新北市環繞臺北市），並以 evenodd 填色。
- **狀態用語**：瀏覽器測試的狀態判斷要涵蓋所有用語（開票中、投票所已全部送達、開票完成）。
- **圖片嵌入**：中選會登記照設有 `Cross-Origin-Resource-Policy: same-site`，其他網站無法嵌入，只能提供連結。
- **改列前查重**：把政見改列為「非政見」之前，先確認同一文字未在其他段落出現。

## 8. 交接時的待辦

- 中選會審定公告或選舉資料庫（db.cec.gov.tw）發布正式結果後，比對本站當選標記；若有差異，以正式公告更正並記錄。
- 2028 選舉前：依手冊第七節重新實測中選會各網站格式，擴充 adapter（總統、立委區域、原住民、不分區政黨票），並為立委選區地圖擴充村里切分處理。
- 每輪工作結束時，以正式臺灣正體中文回報：成果、驗證結果與限制。
