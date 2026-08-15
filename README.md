# 富信新零售 AI 電商活動策略決策助手
## 程式碼說明｜最新版

> 對應目前產品版入口：`product_app.py`  
> 本文件依目前最新專案結構整理，包含首頁「AI 今日洞察」、活動洞察、AI 策略中心、情境模擬、行動生成、主管報表、Session State、Gemini 與 Supabase 的主要程式邏輯。

---

# 1. 專案定位

本專案是一套以 **Streamlit + Pandas + Gemini** 建立的零售活動決策輔助平台。

系統核心不是單純把 Excel 轉成圖表，而是把既有銷量與活動資料串成：

```text
資料準備
→ 完整分析
→ 分析總覽
→ 活動洞察
→ AI 策略中心
→ 情境模擬
→ 行動生成
→ 主管報表
```

目前競賽展示的主流程可簡化理解為：

```text
What happened
→ Why
→ What next
→ Simulate
→ Act
```

也就是：

```text
分析總覽
→ 活動洞察
→ AI 策略中心
→ 情境模擬
→ 行動生成
```

---

# 2. 產品入口

## `product_app.py`

這是目前正式產品版的主要入口。

啟動方式：

```powershell
python -m streamlit run product_app.py
```

主要負責：

1. 設定 Streamlit 頁面
2. 初始化 Session State
3. 自動載入示範資料
4. 套用全站 UI 樣式
5. 建立側邊欄導覽
6. 顯示品牌 Logo
7. 控制側邊欄 icon-only / 收合狀態
8. 顯示浮動 AI 策略顧問

主要初始化：

```python
initialize_session_state()
ensure_default_demo_data_loaded()
```

因此使用者第一次打開系統時，即使沒有上傳自己的 Excel，也可以直接看到示範資料。

---

# 3. 最新側邊欄頁面結構

目前 `product_app.py` 中正式顯示的頁面如下：

```text
首頁
└─ 首頁

資料準備
├─ 01 銷量資料處理
└─ 02 活動資料處理

分析流程
└─ 03 執行完整分析

主決策引擎
├─ 分析總覽
├─ 活動洞察
├─ AI 策略中心
└─ 情境模擬

成果匯出
├─ 行動生成
└─ 主管報表中心
```

對應實際檔案：

| 顯示名稱 | 實際檔案 |
|---|---|
| 首頁 | `app_pages/0_首頁.py` |
| 01 銷量資料處理 | `app_pages/1_資料上傳.py` |
| 02 活動資料處理 | `app_pages/5_活動資料上傳.py` |
| 03 執行完整分析 | `app_pages/6_執行完整分析.py` |
| 分析總覽 | `app_pages/11_產品首頁.py` |
| 活動洞察 | `app_pages/12_活動洞察.py` |
| AI 策略中心 | `app_pages/13_策略中心.py` |
| 情境模擬 | `app_pages/17_情境模擬.py` |
| 行動生成 | `app_pages/18_行動生成.py` |
| 主管報表中心 | `app_pages/16_主管報表中心.py` |

---

# 4. 最新首頁：AI 今日洞察

## 檔案

```text
app_pages/0_首頁.py
```

這是目前首頁最重要的新增功能。

首頁不再只做產品介紹，而是加入：

```text
AI 今日發現 X 個值得注意的行銷機會
```

使用者不需要先輸入問題，也不需要點「AI 解讀」。

系統會自動從目前既有分析結果找出最值得注意的 3 個異常或機會。

---

## 4.1 AI 今日洞察的資料流程

目前流程刻意拆成：

```text
Pandas 計算
→ 找出異常 / 機會
→ 擷取歷史比較
→ 擷取類似活動證據
→ 將結構化事實交給 Gemini
→ Gemini 解釋原因與提出下一步
→ 首頁顯示 Evidence Card
```

重要原則：

> **Gemini 不負責算數字。**

所有下列數字都先由 Python / Pandas 計算：

- 淨增益 / 日
- 量增效應 / 日
- 降價效應 / 日
- 折扣率
- 歷史平均
- 與歷史平均差異
- 相同活動組合案例

Gemini 只負責：

- 可能原因
- 下一步行動建議
- 文字解釋

---

## 4.2 `_build_home_history_context()`

主要用途：

```python
def _build_home_history_context(
    strategy: pd.DataFrame,
    row: pd.Series,
) -> tuple[str, str]:
```

負責計算：

### A. 同商品歷史平均

優先比較：

```text
同一商品
＋
其他活動單位
```

若沒有其他活動紀錄，才退回：

```text
其他活動單位平均
```

最後會產生：

```text
目前淨增益/日
vs
同商品其他活動平均
vs
差異
```

例如：

```text
目前淨增益/日 -259,567 元
相較同商品其他活動單位平均 -45,258 元
差異 -214,309 元
```

---

### B. 類似活動歷史證據

系統會依：

```python
corresponding_activities_label
```

尋找相同活動組合的歷史案例。

例如：

```text
全站活動＋平台日組合
```

若找到相同活動組合，會顯示：

```text
商品名稱
活動單位
淨增益/日
折扣率
```

若沒有完全相同案例，會明確寫：

```text
目前資料中沒有其他完全相同的活動組合可直接比較。
```

---

# 5. `_build_home_ai_insights()`

這是首頁「AI 今日洞察」最核心的函式。

```python
def _build_home_ai_insights() -> list[dict[str, str]]:
```

主要讀取：

```python
activity_unit_overview_dataframe
activity_waterfall_summary_dataframe
activity_unit_price_dataframe
```

接著先執行：

```python
strategy = prepare_ai_strategy_data(unit_overview)
queue = build_decision_queue(strategy, limit=3)
```

因此首頁的 3 張洞察不是 Gemini 隨機挑的。

而是：

```text
Python / Pandas
→ AI 策略中心既有決策邏輯
→ 挑出優先級最高的 3 筆
```

---

# 6. 首頁 Gemini 使用方式

首頁沿用既有：

```text
src/ai_advisor.py
```

主要使用：

```python
build_advisor_context()
get_structured_advisor_answer()
```

送給 Gemini 的 prompt 會先包含：

```text
發生什麼
KPI
歷史比較
歷史證據
商品編號
活動單位
```

並明確要求：

```text
禁止創造任何新數字
若資料不足請直接說明
```

因此 Gemini 的定位是：

```text
解釋器 + 決策建議助手
```

而不是：

```text
數據計算器
```

---

# 7. 首頁洞察 Card 最新版型

目前最新版已改成：

```text
一張洞察 = 一整列橫式 Card
```

不是原本的三張直式並排。

每張 Card 左到右分三區：

### 左側

```text
發生什麼
KPI 異常
```

### 中間

```text
歷史比較
AI 推測原因
```

### 右側

```text
歷史證據
建議下一步
AI 信心
```

下面再放兩個操作：

```text
[查看判斷依據]
[行動生成 →]
```

目標是讓評審可以從左到右快速理解：

```text
問題
→ 為什麼
→ 證據
→ 下一步
```

---

# 8. 查看判斷依據

每張首頁洞察 Card 都有：

```text
查看判斷依據
```

按下後會展開：

```text
目前活動證據
歷史 / 類似活動
資料限制
```

這個設計的目的，是避免 AI 看起來像黑箱。

使用者可以確認：

```text
AI 是根據哪些資料做判斷
```

而不是只看到一段建議。

---

# 9. 行動生成按鈕

最新版首頁按鈕名稱：

```text
行動生成 →
```

程式：

```python
st.session_state["home_ai_selected_insight"] = insight
st.switch_page("app_pages/18_行動生成.py")
```

用途：

1. 把目前選中的首頁洞察存進 Session State
2. 跳到「行動生成」頁
3. 讓後續行動內容可以承接前面的分析脈絡

這個流程代表：

```text
AI 發現問題
→ 使用者選擇問題
→ 直接進入執行
```

---

# 10. 首頁 AI 快取

Streamlit 每次操作都可能重新執行整支 Python。

若每次 rerun 都重新叫 Gemini：

- 速度慢
- 浪費 API
- 結果可能每次微幅不同

因此首頁加入：

```python
_home_ai_signature()
```

會針對目前重要欄位建立資料 signature：

```text
product_id
unit_code
days
discount_rate
volume_effect_per_day
price_effect_per_day
net_revenue_effect_per_day
corresponding_activities_label
```

再利用：

```python
pd.util.hash_pandas_object()
```

判斷資料是否真的改變。

只有 signature 改變時才重新產生 AI 洞察。

---

# 11. 分析總覽

## 檔案

```text
app_pages/11_產品首頁.py
```

角色：

```text
What happened?
```

主要回答：

- 現在整體銷售狀況如何
- 有多少商品
- 有多少活動
- GMV / 銷量 / 趨勢如何
- 資料狀態是否完整

定位是：

```text
整體狀況總覽
```

而不是直接做策略決策。

---

# 12. 活動洞察

## 檔案

```text
app_pages/12_活動洞察.py
```

角色：

```text
Why?
```

主要用途：

- 商品比較
- 活動比較
- 折扣率分析
- 活動組合分析
- 淨營收效應
- 高低成效活動辨識
- 風險與異常探索

AI Insight Card 在這一頁主要應該做：

```text
發現
原因
資料證據
資料限制
```

而不是搶 AI 策略中心的工作。

---

# 13. AI 策略中心

## 頁面

```text
app_pages/13_策略中心.py
```

## 核心邏輯

```text
src/ai_strategy_center.py
```

主要函式：

```python
prepare_ai_strategy_data()
build_decision_queue()
build_executive_brief()
build_next_period_plan()
```

定位：

```text
What next?
```

也就是：

```text
現在最值得做什麼？
```

---

## 13.1 `prepare_ai_strategy_data()`

將活動單位分析資料整理成策略中心需要的格式。

主要目標：

- 清理欄位
- 統一資料型態
- 準備策略判斷所需 KPI

---

## 13.2 `build_decision_queue()`

建立決策優先清單。

首頁「AI 今日洞察」也直接沿用這個邏輯。

因此：

```text
首頁 Top 3
```

與：

```text
AI 策略中心 Decision Queue
```

使用的是一致的策略邏輯。

這樣可避免首頁和策略中心講不同故事。

---

## 13.3 `build_executive_brief()`

負責產生主管快速閱讀的摘要資訊。

用途是把大量分析壓縮成：

```text
風險
機會
需要優先處理的事項
```

---

## 13.4 `build_next_period_plan()`

根據目前活動表現整理下一期策略方向。

適合回答：

```text
下一檔活動應該延續什麼？
哪些活動應該調整？
哪些活動需要重新驗證？
```

---

# 14. 情境模擬

## 頁面

```text
app_pages/17_情境模擬.py
```

## 核心邏輯

```text
src/whatif_simulation.py
```

定位：

```text
What if?
```

主要功能：

```text
修改折扣條件
修改贈品條件
→
比較不同方案的預估結果
```

---

## 14.1 主要函式

```python
compute_whatif_scenario()
compute_whatif_scenarios()
select_best_scenario()
estimate_daily_sales_from_history()
estimate_avg_discount_rate_from_history()
estimate_sales_uplift_rate_from_history()
estimate_baseline_price_from_history()
```

重要原則：

情境模擬是：

```text
估算 / scenario
```

不是：

```text
實際營收預測保證
```

目前也不能把結果直接解釋成：

```text
實際淨利
```

因為資料沒有完整納入：

- 商品成本
- 毛利
- 平台抽成
- 退貨
- 廣告成本
- 完整贈品成本
- 完整平台活動歸因

因此頁面使用：

```text
簡化淨效益
```

而非：

```text
淨利
```

---

# 15. 行動生成

## 頁面

```text
app_pages/18_行動生成.py
```

## 核心邏輯

```text
src/action_generator.py
```

角色：

```text
Act
```

也就是把前面分析轉成真正可以執行的內容。

---

## 15.1 支援的輸出格式

目前可以生成：

```text
電話話術
LINE / 簡訊
Email
拜訪提綱
```

並支援不同溝通情境。

---

## 15.2 B2B / B2C

行動生成已有區分：

```text
To B
To C
```

### B2B

可以引用較完整的內部活動分析與數據證據。

### B2C

不能直接把內部指標寫給消費者。

例如不應出現：

```text
淨增益
量增效應
毛利風險
內部活動成效
```

B2C 只應使用可公開的：

- 售價
- 折扣
- 贈品
- 優惠
- 活動期間
- 消費者利益點

---

# 16. 行動生成核心函式

`src/action_generator.py` 主要包含：

```python
build_platform_campaign_name_set()
classify_activity_type()
build_unit_activity_composition_note()
build_unit_action_evidence()
build_whatif_action_evidence()
build_consumer_offer_text()
build_action_generation_prompt()
ask_gemini_action_content()
validate_b2c_output()
build_b2c_fallback_content()
build_b2b_fallback_content()
generate_action_content()
```

其中：

```python
generate_action_content()
```

是主要入口。

Gemini API 無法使用時，程式仍準備 fallback 內容，避免競賽 Demo 因 API 暫時失效而完全中斷。

---

# 17. Evidence Card 共用元件

## 檔案

```text
src/insight_cards.py
```

主要函式：

```python
render_structured_advisor_card()
render_ai_insight_card()
render_discount_insight_card()
render_evidence_sections()
render_scenario_card()
```

目前：

```python
render_ai_insight_card()
```

支援：

```python
action_label
```

因此不同頁面可以根據語意顯示：

```text
建議
```

或：

```text
資料限制
```

而不是所有卡片都固定顯示「建議」。

---

# 18. Gemini AI 顧問

## 檔案

```text
src/ai_advisor.py
```

AI 顧問目前不應取代 Python 分析。

正確責任分工：

### Python / Pandas

負責：

```text
資料清理
統計
KPI
歷史比較
異常偵測
活動成效
情境試算
```

### Gemini

負責：

```text
解釋
推測可能原因
整理管理語言
提出下一步
生成溝通內容
```

這也是目前首頁 AI 今日洞察遵守的原則。

---

# 19. Session State

## 檔案

```text
src/session_helpers.py
```

Streamlit 沒有傳統前後端永久 state，因此跨頁資料主要靠：

```python
st.session_state
```

保存。

核心初始化：

```python
initialize_session_state()
```

主要 Session State 分類：

```text
銷量資料
活動資料
整合結果
活動成效
策略報告
活動單位分析
AI 顧問
情境模擬
行動生成
UI 狀態
```

---

# 20. 首頁新增的 Session State

AI 今日洞察目前會使用：

```text
home_ai_insights
home_ai_insights_signature
home_ai_selected_insight
home_ai_evidence_0
home_ai_evidence_1
home_ai_evidence_2
```

用途：

### `home_ai_insights`

保存已經產生好的 3 張 AI 洞察。

### `home_ai_insights_signature`

記錄目前分析資料版本。

資料沒變時不重新呼叫 Gemini。

### `home_ai_selected_insight`

當使用者按：

```text
行動生成 →
```

保存目前被選中的洞察，供後續頁面使用。

---

# 21. 示範資料

## 檔案

```text
src/demo_data.py
```

產品版進入時會執行：

```python
ensure_default_demo_data_loaded()
```

因此 Demo 不需要現場重新上傳資料。

首頁「開始探索」則使用：

```python
apply_full_demo_data_to_session()
```

一次把：

- 銷量
- 活動
- 完整分析
- 活動單位分析

放入 Session State，再直接跳到：

```text
分析總覽
```

這個設計主要是確保競賽現場操作穩定。

---

# 22. Supabase / PostgreSQL

## 檔案

```text
src/persistence.py
```

主要函式：

```python
_get_database_url()
_get_connection()
save_state()
load_state()
load_states()
save_states()
delete_state()
```

資料庫透過：

```text
DATABASE_URL
```

連線。

---

## 22.1 Secrets

本機 `.env`：

```env
GEMINI_API_KEY=...
DATABASE_URL=...
```

Streamlit Cloud：

```toml
GEMINI_API_KEY = "..."
DATABASE_URL = "..."
```

不要把真實 Key 或資料庫密碼 push 到 GitHub。

---

# 23. 目前資料與資料庫的角色

目前系統仍大量使用：

```python
st.session_state
```

做即時頁面狀態。

Supabase 主要負責需要跨執行環境保存的 state / snapshot。

因此不要自行把所有 Session State 全部搬成資料庫資料表。

目前開發原則仍是：

```text
不要重建資料庫架構
不要為單一新功能新增大型 persistence 架構
```

---

# 24. 主管報表

## 頁面

```text
app_pages/16_主管報表中心.py
```

## 報表產生

```text
src/report_generator.py
```

主要負責將分析結果輸出成 PDF。

Linux / Streamlit Cloud 為了中文字型，使用：

```text
packages.txt
```

安裝：

```text
fonts-noto-cjk
fontconfig
```

---

# 25. UI 系統

主要共用 UI：

```text
src/ui_style.py
src/chart_theme.py
src/kpi_cards.py
src/insight_cards.py
```

---

## `src/ui_style.py`

負責：

- 全站字型
- 背景
- 側邊欄
- 深色 / 淺色模式
- 品牌樣式
- icon-only sidebar
- 首頁側欄狀態

---

## `src/chart_theme.py`

統一 Plotly 圖表的：

- 字型
- 背景
- 軸線
- tooltip
- 配色邏輯

---

# 26. 專案最新主要結構

```text
fushin-sales-ai/
│
├─ product_app.py
├─ app.py
├─ requirements.txt
├─ packages.txt
├─ README.md
├─ .env.example
│
├─ .streamlit/
│  └─ config.toml
│
├─ app_pages/
│  ├─ 0_首頁.py
│  ├─ 1_資料上傳.py
│  ├─ 5_活動資料上傳.py
│  ├─ 6_執行完整分析.py
│  ├─ 7_銷量活動整合.py
│  ├─ 8_活動成效分析.py
│  ├─ 9_策略建議報表.py
│  ├─ 10_AI行銷策略顧問.py
│  ├─ 11_產品首頁.py
│  ├─ 12_活動洞察.py
│  ├─ 13_策略中心.py
│  ├─ 16_主管報表中心.py
│  ├─ 17_情境模擬.py
│  ├─ 18_行動生成.py
│  └─ templates/
│     └─ home_hero.html
│
├─ src/
│  ├─ action_generator.py
│  ├─ activity_date_utils.py
│  ├─ activity_processing.py
│  ├─ activity_unit_analysis.py
│  ├─ ai_advisor.py
│  ├─ ai_strategy_center.py
│  ├─ analysis_pipeline.py
│  ├─ chart_theme.py
│  ├─ demo_data.py
│  ├─ executive_summary.py
│  ├─ floating_chatbot.py
│  ├─ insight_cards.py
│  ├─ kpi_cards.py
│  ├─ persistence.py
│  ├─ report_generator.py
│  ├─ sales_processing.py
│  ├─ session_helpers.py
│  ├─ ui_style.py
│  ├─ unit_overview_helpers.py
│  ├─ unit_recommendation_notes.py
│  └─ whatif_simulation.py
│
├─ assets/
│  ├─ logo-white.png
│  └─ 品牌圖片
│
├─ tests/
│  ├─ test_action_generator.py
│  ├─ test_action_generator_b2b_b2c.py
│  ├─ test_activity_input_compatibility.py
│  ├─ test_activity_unit_analysis.py
│  ├─ test_ai_advisor_structured.py
│  ├─ test_ai_strategy_center.py
│  ├─ test_run_activity_unit_analysis_integration.py
│  ├─ test_unit_recommendation_notes.py
│  └─ test_whatif_simulation.py
│
└─ data/
   ├─ raw/
   └─ processed/
```

---

# 27. requirements

目前主要依賴：

```text
streamlit
pandas
numpy
openpyxl
plotly
google-genai
python-dotenv
reportlab
psycopg2-binary
```

建議 Python：

```text
Python 3.12
```

---

# 28. 本機測試

切到專案目錄後：

```powershell
.venv\Scripts\activate
python -m streamlit run product_app.py
```

單一 Python 檔案語法檢查：

```powershell
python -m py_compile "app_pages/0_首頁.py"
```

完整測試：

```powershell
pytest
```

或：

```powershell
python -m pytest
```

---

# 29. Git 開發流程

每次修改前：

```powershell
git switch main
git pull --ff-only origin main
```

建立 branch：

```powershell
git switch -c feature/your-feature-name
```

開發完成：

```powershell
git status
git add .
git commit -m "feat: description"
git push -u origin feature/your-feature-name
```

再到 GitHub 建立 Pull Request：

```text
base: main
compare: feature/your-feature-name
```

---

# 30. AI 今日洞察目前 branch

本次首頁功能建議 branch：

```text
feature/ai-daily-insights-home
```

主要修改：

```text
app_pages/0_首頁.py
```

最新 UI：

```text
三張直式卡
→
三張橫式、一張一列
```

最新按鈕：

```text
產生完整行銷方案
→
行動生成 →
```

---

# 31. 目前最重要的產品原則

## 原則 1：數字由 Python 算

禁止：

```text
Gemini 自行創造 KPI
Gemini 自行估平均
Gemini 自行生成不存在的營收
```

應該：

```text
Pandas 算數字
Gemini 解釋數字
```

---

## 原則 2：不要把觀察性結果說成因果

可以：

```text
活動期間觀察到銷量提升
```

不要直接說：

```text
這個活動造成銷量提升
```

---

## 原則 3：淨增益不等於淨利

目前：

```text
net_revenue_effect_per_day
```

是分析指標。

沒有完整：

- 成本
- 毛利
- 退貨
- 平台抽成
- 行銷費
- 贈品完整成本

因此不能直接稱：

```text
實際淨利
```

---

## 原則 4：資料信心必須被看見

AI 結果應呈現：

```text
高
中
低
```

若：

- 樣本天數少
- 對照期間不足
- 活動重疊
- 價格為代理估算

就必須在資料限制中說明。

---

# 32. 競賽 Demo 建議理解方式

評審不需要理解每一支 Python 函式。

他們應該在很短時間看懂：

```text
AI 先主動發現問題
↓
告訴我哪些 KPI 不對
↓
拿歷史資料證明
↓
解釋可能原因
↓
提出下一步
↓
讓我先模擬
↓
最後直接生成可以執行的內容
```

因此首頁「AI 今日洞察」的作用非常重要：

> **讓使用者一進系統就先看到 AI 發現了什麼，而不是先要求使用者自己找問題。**

---

# 33. 最新版本摘要

目前最新產品核心可以濃縮為：

```text
首頁
AI 主動找出 Top 3 風險 / 機會

↓

分析總覽
快速掌握整體 KPI

↓

活動洞察
找到問題與活動表現差異

↓

AI 策略中心
解釋原因、證據、信心與下一步

↓

情境模擬
比較折扣 / 贈品等不同方案

↓

行動生成
轉成 To B / To C 的電話、LINE、簡訊、Email、拜訪內容

↓

主管報表
輸出管理者可閱讀成果
```

最終產品定位：

> **不是只有「看報表」，而是讓資料一路走到決策與行動。**
