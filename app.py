import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

# タイトル
st.title("就活・企業分析ダッシュボード")

# 入力欄
ticker_input = st.text_input("証券コードを入力（例: 6758）", "6758")
ticker = f"{ticker_input}.T"

if st.button("分析開始"):
    try:
        with st.spinner('データを取得中...'):
            company = yf.Ticker(ticker)
            
            # 【重要】期間を5年に指定して確実にデータを取る
            income_stmt = company.get_financials(period="5y")
            balance_sheet = company.get_balance_sheet(period="5y")
            
            # データが存在するかチェック
            if income_stmt is None or income_stmt.empty:
                st.error("財務データが見つかりませんでした。証券コードが正しいか確認してください。")
            else:
                # --- 指標計算（エラー回避用） ---
                # 収益性
                op_inc = income_stmt.loc['Operating Income'].iloc[0]
                rev = income_stmt.loc['Total Revenue'].iloc[0]
                op_margin = (op_inc / rev) * 100

                # 安全性
                equity = balance_sheet.loc['Stockholders Equity'].iloc[0]
                total_assets = balance_sheet.loc['Total Assets'].iloc[0]
                equity_ratio = (equity / total_assets) * 100

                # 成長性
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
                
                st.write(f"現在の営業利益率: {op_margin:.1f}%")

    except Exception as e:
        st.error(f"分析中にエラーが発生しました: {e}")
