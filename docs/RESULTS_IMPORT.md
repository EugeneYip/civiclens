# 結果資料匯入（V0.1.23）
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