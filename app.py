import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

# ページ全体の設定（タイトルバーやレイアウト）
st.set_page_config(page_title="企業分析ボード", layout="wide")

# カスタムCSSでデザインをさらに凝る
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #0068c9; color: white; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 企業分析ダッシュボード")

# --- 入力セクション（メイン画面の上部に配置） ---
COMPANY_LIST = {
    "ソニーグループ": "6758", "トヨタ自動車": "7203", "任天堂": "7974",
    "ソフトバンクG": "9984", "キーエンス": "6861", "三菱UFJ": "8306"
}

col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    selected_company = st.selectbox("企業を選択", ["直接入力"] + list(COMPANY_LIST.keys()))
with col_in2:
    if selected_company == "直接入力":
        ticker_input = st.text_input("証券コード", "6758")
    else:
        ticker_input = COMPANY_LIST[selected_company]

# 分析開始ボタンを中央にドカンと配置
if st.button("🔥 分析を実行する"):
    ticker = f"{ticker_input}.T"
    try:
        with st.spinner('データを解析中...'):
            company = yf.Ticker(ticker)
            income_stmt = company.financials
            balance_sheet = company.balance_sheet
            
            # --- 指標計算（鉄壁版を凝縮） ---
            def get_val(df, keys):
                for k in keys:
                    if k in df.index: return df.loc[k]
                return None

            rev_data = get_val(income_stmt, ['Total Revenue', 'Operating Revenue'])
            op_inc_data = get_val(income_stmt, ['Operating Income', 'Pretax Income'])
            
            # 各種計算（エラー回避込）
            op_margin = (op_inc_data.iloc[0] / rev_data.iloc[0] * 100) if rev_data is not None else 0
            
            equity_data = get_val(balance_sheet, ['Stockholders Equity', 'Total Equity'])
            assets_data = get_val(balance_sheet, ['Total Assets'])
            equity_ratio = (equity_data.iloc[0] / assets_data.iloc[0] * 100) if equity_data is not None else 0
            
            rev_series = rev_data.sort_index(ascending=True)
            X = np.arange(len(rev_series)).reshape(-1, 1)
            y = rev_series.values
            trend_ratio = (LinearRegression().fit(X, y).coef_[0] / rev_series.mean() * 100)

            # --- メインレイアウト ---
            col_graph, col_stats = st.columns([1.5, 1])
            
            with col_graph:
                scores = [max(0, min(100, op_margin * 5)), max(0, min(100, equity_ratio * 2)), max(0, min(100, 50 + trend_ratio * 5))]
                categories = ['収益性', '安全性', '成長性']
                fig = go.Figure(data=go.Scatterpolar(r=scores + [scores[0]], theta=categories + [categories[0]], fill='toself', fillcolor='rgba(0, 104, 201, 0.2)', line=dict(color='#0068c9')))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400, margin=dict(l=40, r=40, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

            with col_stats:
                st.write("#### 📊 経営指標")
                st.metric("営業利益率", f"{op_margin:.1f}%")
                st.metric("自己資本比率", f"{equity_ratio:.1f}%")
                st.metric("成長トレンド", f"{trend_ratio:.1f}%")

            # --- 診断セクション ---
            st.divider()
            diag = "💎 高収益・盤石型" if op_margin > 20 and equity_ratio > 40 else "🚀 成長優先型" if trend_ratio > 10 else "⚖️ バランス型"
            st.info(f"### 総合診断: {diag}")
            st.write(f"**就活アドバイス:** この企業は業界内でも{diag}の特徴が強く出ています。自分のキャリア観と照らし合わせてみましょう。")

    except Exception as e:
        st.error(f"分析失敗: 証券コード {ticker_input} のデータを読み込めませんでした。({e})")
