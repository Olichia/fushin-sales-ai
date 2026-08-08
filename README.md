# 富信新零售銷量與活動分析系統

本專案是一套以 Streamlit 建立的零售活動分析 MVP，用於整合銷量資料與促銷活動資料，完成欄位對應、資料品質檢查、活動前中後比較、策略分類、AI 顧問解讀與主管 PDF 報表匯出。

## 專案目標

原始銷量與活動 Excel 經常存在欄位名稱不一致、日期格式混雜、同日同商品多筆紀錄、活動期間難以直接與每日銷量對應等問題。本系統將這些步驟整合成單一操作流程，協助使用者快速完成資料整理與活動成效判讀。

> 本系統提供的是觀察性分析與決策輔助，不直接證明活動造成銷量變化，也不在缺少成本與毛利資料時判定活動是否獲利。

## 主要功能

### 資料管理

- 上傳銷量 Excel 並選擇工作表
- 將原始欄位對應至標準欄位
- 清理日期、商品編號、商品名稱與銷量
- 標記缺值、格式錯誤與疑似異常資料
- 上傳及標準化品牌活動資料
- 建立活動日曆與優惠內容資料

### 系統處理

- 依商品編號與日期整合每日銷量及活動資料
- 比較活動前、活動期間與活動後的日均銷量
- 計算活動提升率、活動後變化率與推估營收
- 標記觀察期間不完整、低基期及活動重疊
- 依規則產生「建議延續、建議優化、建議檢討」分類

### 決策分析

- 分析總覽與核心 KPI
- 活動成效排名與趨勢圖表
- AI 策略中心（策略摘要、決策佇列與 Gemini AI 對話）
- 主管 PDF 報表下載

## 分析流程

```text
銷量資料上傳
→ 欄位設定
→ 銷量資料品質
→ 活動資料上傳
→ 活動資料品質
→ 建立整合資料
→ 執行成效分析
→ 產生策略報告
→ 查看活動洞察／AI 顧問／主管報表
```

## 核心欄位

| 標準欄位 | 用途 |
|---|---|
| `sale_date` | 判斷每日銷量與活動前、中、後期間 |
| `product_id` | 連結銷量資料與活動資料的主要鍵 |
| `product_name` | 報表顯示與人工核對 |
| `quantity` | 計算每日銷量與活動成效 |
| `activity_start_date` | 活動開始日期 |
| `activity_end_date` | 活動結束日期 |

## 主要計算邏輯

### 每日商品銷量

同一天、同一商品的多筆交易，會依分析粒度彙總：

```text
每日商品銷量 = 同日期、同商品所有交易數量加總
```

### 活動提升率

```text
活動提升率
=（活動期間日均銷量－活動前日均銷量）÷ 活動前日均銷量
```

當活動前日均銷量為 0 時，不進行一般百分比計算，並應視為低基期或無基期情況。

### 推估營收

```text
推估營收 = 活動期間銷量 × 可用的活動價格
```

推估營收不等於實際營收或獲利，尚未完整納入折扣碼、退貨、平台幣、贈品、運費、廣告成本、平台抽成、商品成本與毛利。

## 圖表使用原則

- **KPI 卡片**：快速顯示活動數、總銷量、提升率中位數與待確認問題。
- **長條圖**：比較不同活動、商品或策略分類的相對表現與排名。
- **折線圖**：呈現每日銷量與活動前後的時間趨勢。
- **散點圖**：同時觀察提升率與活動規模，避免只看高百分比而忽略實際銷量。
- **資料表**：提供精確數值、商品編號、日期及資料信心，供人工查核。

## AI 顧問定位

核心數值由 Python 與既定規則計算，Gemini 僅負責解讀既有分析結果及提出下一步驗證建議。AI 回答必須：

- 區分資料觀察、推測與建議
- 不將相關性表述為因果
- 主動提醒期間不完整、低基期與活動重疊
- 不在缺少成本或毛利資料時宣稱活動獲利

## 技術架構

- Python
- Streamlit
- Pandas
- Plotly
- OpenPyXL
- Google Gen AI SDK
- ReportLab
- Supabase (Postgres)

## 本機安裝

建議使用 Python 3.12。

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

在專案根目錄建立 `.env`：

```env
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://postgres.xxxxxxxx:your_password@aws-0-xxxxx.pooler.supabase.com:6543/postgres
```

`DATABASE_URL` 是 Supabase 專案的 Postgres 連線字串，用來取代原本的本機 SQLite，讓分析快照可以跨部署／重啟保存。第一次連線時程式會自動建立所需的資料表，不用手動建 schema。

請用 **Transaction pooler**（Project Settings -> Database -> Connect -> Connection Method 選 "Transaction pooler"，port `6543`）的連線字串，不要用預設的 Direct connection（port `5432`）。程式每次讀寫都是開一條新連線、用完即關，符合 Transaction pooler「每次互動都短暫且獨立」的設計場景；Direct connection 是給長駐連線用的，多人同時操作時很快會撐爆 Supabase 免費方案的連線數上限。

啟動產品版：

```powershell
streamlit run product_app.py
```

開發版入口仍保留為：

```powershell
streamlit run app.py
```

## Streamlit Community Cloud 部署

部署設定：

```text
Branch: ui-redesign
Main file path: product_app.py
```

在 Streamlit App Secrets 中加入：

```toml
GEMINI_API_KEY = "your_gemini_api_key"
DATABASE_URL = "postgresql://postgres.xxxxxxxx:your_password@aws-0-xxxxx.pooler.supabase.com:6543/postgres"
# 連線字串請從 Connect -> Connection Method 選 "Transaction pooler" 取得
```

`packages.txt` 用於安裝 PDF 所需的 Linux 中文字型：

```text
fonts-noto-cjk
fontconfig
```

## 專案結構

```text
fushin-sales-ai/
├─ .streamlit/
│  └─ config.toml
├─ pages/
├─ src/
├─ app.py
├─ product_app.py
├─ requirements.txt
├─ packages.txt
├─ .env.example
└─ README.md
```

## 資料安全

請勿提交以下內容至 GitHub：

- `.env`
- `.streamlit/secrets.toml`
- Gemini API Key
- Supabase 連線字串（`DATABASE_URL`）
- 客戶姓名、電話、Email 等個資
- 公司成本、毛利與未公開營運資料
- 真實企業原始 Excel

展示與測試建議使用匿名或模擬資料。AI 顧問會將分析摘要送至外部 Gemini API，因此不應輸入未經授權的機密內容。

## 目前限制

- 使用 `st.session_state` 保存資料，重新整理、休眠或重新啟動後可能需要重新上傳。
- 尚未建立資料庫、登入、權限與永久儲存機制。
- 活動前後比較屬觀察性分析，不是隨機實驗或因果推論。
- 活動重疊時，無法將效果完整歸因於單一活動。
- 缺少成本、毛利、庫存、退貨、廣告支出及客群資料時，不能完整評估獲利。

## 版本狀態

目前為產品展示版 MVP，適合課程、團隊展示與匿名資料測試，不建議直接作為正式企業生產系統。
