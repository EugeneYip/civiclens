# 2026 公報批次覆核管線

資料來源：正至 · 台灣選舉資訊平台（[資料方法與引用](https://taiwan-election-web.vercel.app/data/downloads)、[固定提交](https://github.com/Yaochieh/taiwan-election/tree/e2791191fdd52681703dde9b6a5486b5e0ceca45)）。其公開網站聲稱已整理 1,555 位首長與議員的公報內容；此數不是 CivicLens 已驗證的數量。原始來源為中選會選舉公報，OCR 仍可能有錯。

`python3 scripts/stage_bulletin.py --output /tmp/bulletin-review.json` 下載固定版本 SQLite，以唯讀模式查詢。可指定 `--db` 使用本機快照。僅以職務、縣市／選區、號次及完整姓名一致配對，拒收既有姓名歧異、無原件 PDF 或頁碼者。只保留與原始 OCR 欄一致且有公報轉錄註記的政見，學經歷與政黨保留公報原文供覆核。

GitHub Actions 只建立覆核用暫存產物，不寫入 main 或正式網站；不收出生日期、出生地或圖片。取得候選人政見全文的重製權利及原件核對完成前，不能以轉錄結果直接發布。若來源結構變更或少於 1,000 筆精確配對，工作失敗而非默默降低門檻。需確認缺漏、核對抽樣及各選區一致性後，再另行整合前端。
