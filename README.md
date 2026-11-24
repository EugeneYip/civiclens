# CivicLens 公民鏡

獨立選舉資訊與公共治理專案。讓事實透明，讓判斷自主。

**V0.1.0 / 2026-11-24：官方資料入口與統計基礎版，尚非完整候選人資料庫。**

- 22 縣市官方電子公報目錄，逐一查閱確認；地理分類僅供瀏覽。
- 中選會公布的九種職務統計，非即時數據或民調。
- 手機優先、鍵盤可操作、無第三方分析或追蹤、無外部程式依賴。
- 尚無候選人個人紀錄；不提供投票推薦或綜合排名。

## 使用與部署

直接開啟 `index.html` 即可瀏覽。完整資料及文件需保留相對路徑。亦可用 `python3 -m http.server 8000` 在本機測試。

1. 目前使用 `EugeneYip/civiclens` 公開儲存庫，預設分支 `main`；公開原始碼不代表正式網站已通過發布審查。
2. 複製儲存庫至本機。
3. 執行 `python3 scripts/build.py` 與 `python3 -m unittest discover -s tests -v`。
4. 審查法律、授權、編輯規範、完整性及公開資金／利益關係揭露後，再開啟 GitHub Pages：Settings → Pages → Deploy from a branch → main → / (root)。若方案不支援私人儲存庫 Pages，先保持不公開，完成審查後切換公開。

正式網址：[civiclens.eugeneyip.net](https://civiclens.eugeneyip.net/)（網域與 GitHub Pages 已由維護者設定；外部連線尚待獨立驗證）。

## 維護

`data/election.json` 是本版官方統計與目錄的來源清冊。更新資料後重建 `index.html`，並通過測試。候選人資料 schema 僅為後續規格，尚未啟用匯入或發布。現階段不宣稱已完成獨立政治中立性、無障礙或法律稽核。

- [研究方法](docs/METHODOLOGY.md)
- [編輯規範](docs/EDITORIAL.md)
- [開發路線](docs/ROADMAP.md)
- [版本紀錄](CHANGELOG.md)

本專案原創程式碼採 [MIT 授權](LICENSE)；政府文件、候選人自述及其他第三方資料各自適用其原有權利與使用條件，不因程式碼授權而改變。本版未重製公報 PDF、候選人相片或個人資料。

## V0.2.0-alpha.1 開發分支

本分支新增六筆臺北市市長名冊試作及逐欄證據。僅供開發與審查；正式站仍為 V0.1.0。執行 `python3 -m http.server 8000` 後瀏覽 `/preview/roster.html`，不要直接以 file:// 開啟。詳見 [名冊查核計畫](docs/ROSTER-AUDIT.md)。獨立人工覆核、全國名冊對帳、資料授權及法律審查尚未完成，不得合併部署。
