import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="企業分析テスト", layout="wide")

st.title("🔍 企業分析デバッグモード")
st.write("まずはデータが届いているか確認しましょう。")

# 銘柄入力
t_code = st.text_input("証券コードを入力（例: 7203）", "7203")

if st.button("データ取得テスト"):
    try:
        full_code = f"{t_code}.T"
        company = yf.Ticker(full_code)
        
        # 1. 基本情報の取得テスト
        info = company.info
        st.success(f"接続成功: {info.get('longName', '名前不明')}")
        
        # 2. 財務データの取得テスト
        income = company.get_financials()
        if income.empty:
            income = company.get_quarterly_financials()
            
        if not income.empty:
            st.write("### 取得できた財務項目一覧")
            st.write(income.index.tolist()) # どんな項目名で届いているか表示
            
            st.write("### 損益計算書（生データ）")
            st.dataframe(income)
        else:
            st.error("財務データが空です。Yahoo Finance側の制限の可能性があります。")
            
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

st.info("これが動けば、ここから少しずつ元のデザイン（グラフなど）に戻していけます。")
