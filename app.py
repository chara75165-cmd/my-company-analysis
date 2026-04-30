import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

# アプリのタイトル
st.title("就活・企業分析ダッシュボード")
st.write("証券コードを入力すると、統計的に企業の『健康診断』を行います。")

# サイドバーで入力を受け取る
ticker_input = st.sidebar.text_input("証券コード（例: 6758）", "6758")
ticker = f"{ticker_input}.T"

if st.sidebar.button("分析開始"):
    try:
        with st.spinner('データを取得中...'):
            company = yf.Ticker(ticker)
            income_stmt = company.financials
            balance_sheet = company.balance_sheet
            
            # --- 統計・指標計算 ---
            # 収益性
            op_margin = (income_stmt.loc['Operating Income'].iloc[0] / income_stmt.loc['Total Revenue'].iloc[0]) * 100
            # 安全性
            equity_ratio = (balance_sheet.loc['Stockholders Equity'].iloc[0] / balance_sheet.loc['Total Assets'].iloc[0]) * 100
            # 成長性（回帰分析）
            rev_data = income_stmt.loc['Total Revenue'].sort_index()
            X = np.arange(len(rev_data)).reshape(-1, 1)
            y = rev_data.values
            model = LinearRegression().fit(X, y)
            trend_ratio = (model.coef_[0] / rev_data.mean()) * 100

            # スコア化
            scores = [
                max(0, min(100, op_margin * 5)),
                max(0, min(100, equity_ratio * 2)),
                max(0, min(100, 50 + trend_ratio * 5))
            ]
            categories = ['収益性 (利益率)', '安全性 (比率)', '成長性 (トレンド)']

            # --- 画面表示 ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"分析スコア: {company.info.get('longName', ticker)}")
                fig = go.Figure(data=go.Scatterpolar(
                    r=scores + [scores[0]],
                    theta=categories + [categories[0]],
                    fill='toself'
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
                st.plotly_chart(fig)

            with col2:
                st.metric("営業利益率", f"{op_margin:.1f}%")
                st.metric("自己資本比率", f"{equity_ratio:.1f}%")
                st.metric("成長トレンド", f"{trend_ratio:.1f}%")

            st.success("分析完了！")

    except Exception as e:
        st.error(f"エラーが発生しました。証券コードが正しいか確認してください: {e}")
