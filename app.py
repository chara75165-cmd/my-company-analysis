import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="ライバル比較ボード", layout="wide")

# カスタムCSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #e63946; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚔️ ライバル企業・比較ダッシュボード")

COMPANY_LIST = {
    "ソニーグループ": "6758", "トヨタ自動車": "7203", "任天堂": "7974",
    "ソフトバンクG": "9984", "キーエンス": "6861", "三菱UFJ": "8306", "パナソニック": "6752", "ホンダ": "7267"
}

# --- 入力セクション（2社選択） ---
col_in1, col_in2 = st.columns(2)
with col_in1:
    c1 = st.selectbox("比較企業 1", list(COMPANY_LIST.keys()), index=0)
with col_in2:
    c2 = st.selectbox("比較企業 2", list(COMPANY_LIST.keys()), index=1)

if st.button("📊 2社を比較分析する"):
    try:
        def get_analysis(ticker_code):
            company = yf.Ticker(f"{ticker_code}.T")
            income = company.financials
            balance = company.balance_sheet
            
            def get_val(df, keys):
                for k in keys:
                    if k in df.index: return df.loc[k]
                return None

            rev_data = get_val(income, ['Total Revenue', 'Operating Revenue'])
            op_inc_data = get_val(income, ['Operating Income', 'Pretax Income'])
            equity_data = get_val(balance, ['Stockholders Equity', 'Total Equity'])
            assets_data = get_val(balance, ['Total Assets'])

            # 指標計算
            op_margin = (op_inc_data.iloc[0] / rev_data.iloc[0] * 100)
            equity_ratio = (equity_data.iloc[0] / assets_data.iloc[0] * 100)
            
            rev_series = rev_data.sort_index(ascending=True)
            X = np.arange(len(rev_series)).reshape(-1, 1)
            y = rev_series.values
            trend = (LinearRegression().fit(X, y).coef_[0] / rev_series.mean() * 100)
            
            return [max(0, min(100, op_margin * 5)), max(0, min(100, equity_ratio * 2)), max(0, min(100, 50 + trend * 5))], op_margin, equity_ratio, trend

        with st.spinner('データを対照中...'):
            scores1, margin1, safety1, trend1 = get_analysis(COMPANY_LIST[c1])
            scores2, margin2, safety2, trend2 = get_analysis(COMPANY_LIST[c2])

            # --- メインレイアウト ---
            col_graph, col_stats = st.columns([1.5, 1])
            
            categories = ['収益性', '安全性', '成長性']
            
            with col_graph:
                fig = go.Figure()
                # 企業1のグラフ
                fig.add_trace(go.Scatterpolar(r=scores1 + [scores1[0]], theta=categories + [categories[0]], fill='toself', name=c1, line=dict(color='#0068c9')))
                # 企業2のグラフ（色を変えて重ねる）
                fig.add_trace(go.Scatterpolar(r=scores2 + [scores2[0]], theta=categories + [categories[0]], fill='toself', name=c2, line=dict(color='#e63946')))
                
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450, margin=dict(l=50, r=50, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

            with col_stats:
                st.write(f"#### 📈 数値比較")
                # 2社の数値を並べて表示
                st.write(f"**【{c1}】** vs **【{c2}】**")
                st.metric(f"利益率", f"{margin1:.1f}%", f"{margin1-margin2:.1f}%" if margin1-margin2 > 0 else f"{margin1-margin2:.1f}%")
                st.metric(f"資本比率", f"{safety1:.1f}%", f"{safety1-safety2:.1f}%")
                st.metric(f"成長率", f"{trend1:.1f}%", f"{trend1-trend2:.1f}%")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
