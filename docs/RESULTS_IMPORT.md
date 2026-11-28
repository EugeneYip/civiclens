# 結果資料匯入（V0.1.23）

> 2026-11-28 開票夜實際採用之作法（中選會計票網站 vote.cec.gov.tw 自動匯入、檢核、定時更新與部署）見 [ELECTION_PLAYBOOK.md](ELECTION_PLAYBOOK.md) 第五節；本文以下之人工 CSV 流程（scripts/stage_results.py）保留為備援。
官方入口：https://www.cec.gov.tw/ 、https://vote.cec.gov.tw/zh-TW/index.html 、https://db.cec.gov.tw/ 、https://data.cec.gov.tw/ 。
2026 原生資料格式、即時介接及權限未確認；不得假設歷屆網址或將媒體預測列入。
1. 開票後取得具明確發布時間的官方原件，保存於本機，不將原件中的不必要資料上傳。
2. 人工逐選區核對並轉成本站 UTF-8 CSV，表頭依序：county,office,district,number,name,votes,elected,valid_votes。縣市碼01–22採本站編碼；office chief/council；首長 district 留白，議員填數字；姓名保留原樣；票數純數字。preliminary 的 elected 留白；final 須為官方公告 true/false。valid_votes 為官方有效票總數，未取得可留白（final 不可）。
3. 執行：
```sh
python3 scripts/stage_results.py reviewed.csv --source-file official-original.pdf --source-url 'https://web.cec.gov.tw/...' --published-at '2026-11-28T20:00:00+08:00' --status preliminary --reviewed-transcription --output /tmp/results-review.json
```
上例為操作示意，不是實際來源或票數。原件雜湊僅供追溯，不能證明轉錄正確或來源真實。
4. 人工獨立核對原件、快照差異及發布資格後，才可另行提交 data/results-snapshot.json。若名冊衝突、補選、同時間不同值、正式結果更正或席次異常，停止並另行核對，禁止猜測。

正式快照由 CI 重建逐筆檢驗；不再將空快照當作永久斷言。開票後頁面每分鐘（可見頁面）重新讀取本站已發布快照，並提供手動更新；保留先前有效資料，並非直接輪詢中選會。
## 前屆正式結果（V0.1.25）
`scripts/import_historical_results.py --cache DIR` 自中選會選舉資料庫靜態 JSON（`https://db.cec.gov.tw/static/elections/data/`）下載111年直轄市長、縣市長、嘉義市長重行選舉及直轄市／縣市議員（區域、平地及山地原住民）結果，產生 `data/historical-results-2022.json`；`--offline` 僅使用快取重建。每個原始檔保留網址及 SHA-256，並核對首長得票加總等於有效票、議員各選區當選人數與候選人數。資料庫當選標記「*」與「!」均以當選計。

中選會說明選舉資料庫於投票後7日內更新。本屆正式結果上架後，可依相同資料結構另行確認115年主題代碼，再經人工核對才能轉入 `results-snapshot.json`；不得在主題代碼或欄位未經確認前自動匯入。

## 11/28 開票夜作業（V0.1.48）
- `scripts/build_results_snapshot.py INPUT.json`：輸入為標準化 JSON（來源網址、發布時間、preliminary／final 及各選區逐候選人票數）；逐筆比對本站名冊縣市、職務、選區、號次與姓名，final 須列全部候選人、當選人數等於應選名額且得票合計等於有效票，否則拒絕。結果頁另以 `validateRace` 重複檢查。合併時正式結果不會被開票中資料覆蓋。
- 瀏覽器測試以攔截載入的測試快照演練11/28 20:00 的正式結果畫面，並確認投票截止前同一快照不顯示；正式快照檔不受影響。
- 連線限制（2026-11-26 實測，本站建置環境）：www.cec.gov.tw、vote.cec.gov.tw 於 TLS 交握時遭重設，vote2026.cec.gov.tw 尚無法解析；info.cec.gov.tw、web.cec.gov.tw、db.cec.gov.tw、bulletin.cec.gov.tw 可連線。若開票資料僅發布於無法連線之網域，本站僅提供官方入口連結，待中選會選舉資料庫（投票後7日內）或可連線之官方來源發布後再匯入；不以媒體或第三方數據替代。
