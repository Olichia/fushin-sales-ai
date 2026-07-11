# 富信新零售銷售分析與 AI 建議系統

本專案用於整理品牌活動資料與銷量資料，
建立銷售分析 Dashboard，並透過生成式 AI 產生分析摘要與建議。

## 第一階段功能

- 讀取多份 Excel
- 讀取所有工作表
- 顯示欄位名稱
- 統計資料筆數
- 統計缺值
- 統計完全重複資料
- 顯示資料型別與前五筆資料

## 技術

- Python
- Pandas
- OpenPyXL

## 執行方式

建立並啟用虛擬環境後：

```bash
pip install -r requirements.txt
python src/inspect_excel.py


---

# 步驟十五：初始化 Git

如果這個資料夾還沒有 Git，在終端機輸入：

```powershell
git init

## 第二階段功能

- 統一銷量資料欄位名稱
- 日期格式標準化
- 商品編號及商品名稱清理
- 銷量數值格式檢查
- 標記完全重複資料
- 標記同日同商品多筆資料
- 保留原始 Excel 列號
- 產生資料品質摘要
- 輸出清理後資料與問題資料

## 執行銷量清理

```bash
python src/clean_sales.py