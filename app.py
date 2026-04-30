import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

st.title("就活・企業分析ダッシュボード")

# --- 企業名とコードの対応リスト（主要企業の例） ---
# ここに自分の気になる企業をどんどん足していけます！
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

# 企業名を選択するか、直接コードを打てるようにする
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
            
            # 財務データを取得
            income_stmt = company.financials
            balance_sheet = company.balance_sheet
            
            if income_stmt is None or income_stmt.empty or balance_sheet is None or balance_sheet.empty:
                st.error("財務データが取得できませんでした。時間をおいて試すか、別のコードを入力してください。")
            else:
                # --- 指標計算（項目名を柔軟に取得） ---
                # 収益性：営業利益 / 売上高
                op_inc = income_stmt.loc['Operating Income'].iloc[0]
                rev = income_stmt.loc['Total Revenue'].iloc[0]
                op_margin = (op_inc / rev) * 100

                # 安全性：自己資本 / 総資産
                # 項目名が微妙に違う場合があるため、キーワードで探す工夫
                equity_key = [k for k in balance_sheet.index if 'Stockholders Equity' in k][0]
                assets_key = [k for k in balance_sheet.index if 'Total Assets' in k][0]
                
                equity = balance_sheet.loc[equity_key].iloc[0]
                total_assets = balance_sheet.loc[assets_key].iloc[0]
                equity_ratio = (equity / total_assets) * 100

                # 成長性：売上の回帰分析
                rev_series = income_stmt.loc['Total Revenue'].sort_index(ascending=True)
                X = np.arange(len(rev_series)).reshape(-1, 1)
                y = rev_series.values
                model = LinearRegression().fit(X, y)
                trend_ratio = (model.coef_[0] / rev_series.mean()) * 100

                # スコア化
                scores = [
                    max(0, min(100, op_margin * 5)),
                    max(0, min(100, equity_ratio * 2)),
                    max(0, min(100, 50 + trend_ratio * 5))
                ]
                categories = ['収益性 (利益率)', '安全性 (比率)', '成長性 (トレンド)']

                # --- グラフ表示 ---
                fig = go.Figure(data=go.Scatterpolar(
                    r=scores + [scores[0]],
                    theta=categories + [categories[0]],
                    fill='toself'
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
                st.plotly_chart(fig)
                
                st.success(f"分析完了: {ticker_input}")
                st.write(f"現在の営業利益率: {op_margin:.1f}%")
                st.write(f"自己資本比率: {equity_ratio:.1f}%")

    except Exception as e:
        st.error(f"分析中にエラーが発生しました: {e}")
