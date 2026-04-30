import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="企業分析・比較ボード", layout="wide")

# カスタムCSS（ボタンの色などを調整）
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 企業分析ダッシュボード")

COMPANY_LIST = {
    "ソニーグループ": "6758", "トヨタ自動車": "7203", "任天堂": "7974",
    "ソフトバンクG": "9984", "キーエンス": "6861", "三菱UFJ": "8306", 
    "パナソニック": "6752", "ホンダ": "7267", "楽天グループ": "4755"
}

# --- 分析用共通関数 ---
def get_analysis(ticker_code):
    company = yf.Ticker(f"{ticker_code}.T")
    income = company.financials
    balance = company.balance_sheet
    if income.empty or balance.empty: return None
    
    def get_val(df, keys):
        for k in keys:
            if k in df.index: return df.loc[k]
        return None

    rev_data = get_val(income, ['Total Revenue', 'Operating Revenue'])
    op_inc_data = get_val(income, ['Operating Income', 'Pretax Income'])
    equity_data = get_val(balance, ['Stockholders Equity', 'Total Equity'])
    assets_data = get_val(balance, ['Total Assets'])

    op_margin = (op_inc_data.iloc[0] / rev_data.iloc[0] * 100)
    equity_ratio = (equity_data.iloc[0] / assets_data.iloc[0] * 100)
    rev_series = rev_data.sort_index(ascending=True)
    X = np.arange(len(rev_series)).reshape(-1, 1)
    y = rev_series.values
    trend = (LinearRegression().fit(X, y).coef_[0] / rev_series.mean() * 100)
    
    scores = [max(0, min(100, op_margin * 5)), max(0, min(100, equity_ratio * 2)), max(0, min(100, 50 + trend * 5))]
    return scores, op_margin, equity_ratio, trend

# --- メイン画面のタブ構成 ---
tab1, tab2 = st.tabs(["🔍 1社じっくり分析", "⚔️ ライバル比較"])

# --- Tab 1: 1社分析 ---
with tab1:
    c_single = st.selectbox("分析したい企業を選択", list(COMPANY_LIST.keys()), key="s_sel")
    if st.button("分析を実行", key="s_btn"):
        res = get_analysis(COMPANY_LIST[c_single])
        if res:
            scores, margin, safety, trend = res
            col1, col2 = st.columns([1.5, 1])
            with col1:
                fig = go.Figure(data=go.Scatterpolar(r=scores + [scores[0]], theta=['収益性','安全性','成長性'] + ['収益性'], fill='toself', line=dict(color='#0068c9')))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.metric("営業利益率", f"{margin:.1f}%")
                st.metric("自己資本比率", f"{safety:.1f}%")
                st.metric("成長トレンド", f"{trend:.1f}%")

# --- Tab 2: 2社比較 ---
with tab2:
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: c1 = st.selectbox("企業 1 (基準)", list(COMPANY_LIST.keys()), index=0)
    with col_sel2: c2 = st.selectbox("企業 2 (比較対象)", list(COMPANY_LIST.keys()), index=1)
    
    if st.button("比較を開始", key="c_btn"):
        res1 = get_analysis(COMPANY_LIST[c1])
        res2 = get_analysis(COMPANY_LIST[c2])
        
        if res1 and res2:
            scores1, m1, s1, t1 = res1
            scores2, m2, s2, t2 = res2
            
            col_g, col_m = st.columns([1.5, 1])
            with col_g:
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=scores1 + [scores1[0]], theta=['収益性','安全性','成長性'] + ['収益性'], fill='toself', name=c1, line=dict(color='#0068c9')))
                fig.add_trace(go.Scatterpolar(r=scores2 + [scores2[0]], theta=['収益性','安全性','成長性'] + ['収益性'], fill='toself', name=c2, line=dict(color='#e63946')))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450)
                st.plotly_chart(fig, use_container_width=True)
            
            with col_m:
                st.write(f"#### 📊 {c1} のスコア")
                st.caption(f"※ ( ) 内は {c2} との差分")
                st.metric("利益率", f"{m1:.1f}%", f"{m1-m2:.1f}%")
                st.metric("資本比率", f"{s1:.1f}%", f"{s1-s2:.1f}%")
                st.metric("成長率", f"{t1:.1f}%", f"{t1-t2:.1f}%")
