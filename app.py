import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

st.title("就活・企業分析ダッシュボード")

# --- 企業名とコードの対応リスト ---
COMPANY_LIST = {
    "ソニーグループ": "6758",
    "トヨタ自動車": "7203",
    "任天堂": "7974",
    "ソフトバンクグループ": "9984",
    "キーエンス": "6861",
    "ファーストリテイリング": "9983",
    "リクルートHD": "6098",
    "三菱UFJフィナンシャルG": "8306"
}

st.sidebar.header("企業選択")
selected_company = st.sidebar.selectbox("主要企業から選ぶ", ["直接入力"] + list(COMPANY_LIST.keys()))

if selected_company == "直接入力":
    ticker_input = st.sidebar.text_input("証券コードを入力（4桁）", "6758")
else:
    ticker_input = COMPANY_LIST[selected_company]

ticker = f"{ticker_input}.T"

if st.button("分析開始"):
    try:
        with st.spinner('データを取得中...'):
            company = yf.Ticker(ticker)
            income_stmt = company.financials
            balance_sheet = company.balance_sheet
            
            if income_stmt is None or income_stmt.empty or balance_sheet is None or balance_sheet.empty:
                st.error("財務データが取得できませんでした。")
            else:
                # --- 指標計算（鉄壁バージョン） ---
                def get_val(df, keys):
                    for k in keys:
                        if k in df.index:
                            return df.loc[k]
                    return None

                rev_data = get_val(income_stmt, ['Total Revenue', 'Operating Revenue'])
                op_inc_data = get_val(income_stmt, ['Operating Income', 'Pretax Income'])

                if rev_data is not None and op_inc_data is not None:
                    rev = rev_data.iloc[0]
                    op_inc = op_inc_data.iloc[0]
                    op_margin = (op_inc / rev) * 100
                else:
                    op_margin = 0

                equity_data = get_val(balance_sheet, ['Stockholders Equity', 'Total Equity'])
                assets_data = get_val(balance_sheet, ['Total Assets'])

                if equity_data is not None and assets_data is not None:
                    equity = equity_data.iloc[0]
                    total_assets = assets_data.iloc[0]
                    equity_ratio = (equity / total_assets) * 100
                else:
                    equity_ratio = 0

                if rev_data is not None:
                    rev_series = rev_data.sort_index(ascending=True)
                    X = np.arange(len(rev_series)).reshape(-1, 1)
                    y = rev_series.values
                    model = LinearRegression().fit(X, y)
                    trend_ratio = (model.coef_[0] / rev_series.mean()) * 100
                else:
                    trend_ratio = 0

                # --- グラフ表示 ---
                scores = [max(0, min(100, op_margin * 5)), max(0, min(100, equity_ratio * 2)), max(0, min(100, 50 + trend_ratio * 5))]
                categories = ['収益性 (利益率)', '安全性 (比率)', '成長性 (トレンド)']
                fig = go.Figure(data=go.Scatterpolar(r=scores + [scores[0]], theta=categories + [categories[0]], fill='toself'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
                st.plotly_chart(fig)
                
                # --- 🔍 追加した解説と診断セクション ---
                st.divider()
                st.subheader("🔍 指標の解説と診断結果")

                with st.expander("各評価軸の概要を確認する"):
                    st.write("""
                    - **収益性**: 効率よく稼げているか。10%超で優良。
                    - **安全性**: 倒産しにくさ。40%以上で安定。
                    - **成長性**: 売上の伸び。プラスなら拡大中。
                    """)

                diagnosis = ""
                advice = ""
                if op_margin > 20 and equity_ratio > 40:
                    diagnosis = "💎 高収益・盤石モデル"
                    advice = "独自の強みがある超優良企業です。"
                elif trend_ratio > 10:
                    diagnosis = "🚀 積極成長型"
                    advice = "勢いがあります。変化を楽しめる人向け。"
                elif equity_ratio > 70:
                    diagnosis = "🛡️ 鉄壁・超安定型"
                    advice = "財務が非常に健全で、長く働ける環境です。"
                else:
                    diagnosis = "⚖️ バランス型"
                    advice = "標準的な状況です。社風などを深掘りしましょう。"

                st.info(f"**【総合診断】 {diagnosis}**")
                st.success(f"**💡 就活アドバイス:** {advice}")

    except Exception as e:
        st.error(f"分析中にエラーが発生しました: {e}")
