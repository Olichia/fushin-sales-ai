import streamlit as st


st.set_page_config(
    page_title="富信新零售資料分析系統",
    page_icon="📊",
    layout="wide",
)

st.title("富信新零售資料分析系統")

st.write(
    """
    本系統用於上傳銷量與品牌活動資料，
    進行欄位辨識、資料標準化、品質檢查與後續分析。
    """
)

st.info(
    "目前階段：資料上傳與標準化後台"
)