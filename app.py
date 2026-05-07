import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from sklearn.linear_model import LinearRegression

# --- ページ設定 ---
st.set_page_config(page_title="プロフェッショナル企業分析ボード", layout="wide")

# --- 共通関数 ---
def get_safe_value(df, keywords):
    """データフレームのインデックスからキーワードに合致する行を抽出（大文字小文字無視）"""
    if df is None or df.empty:
        return pd.Series()
    
    # インデックスを小文字にして照合
    idx_lower = [str(i).lower().replace(" ", "") for i in df.index]
    for kw in keywords:
        kw_clean = kw.lower().replace(" ", "")
        if kw_clean in idx_lower:
            target_idx = idx_lower.index(kw_clean)
            return df.iloc[target_idx]
    return pd.Series()

@st.cache_data(ttl=3600)
def get_full_analysis(ticker_code):
    try:
        full_code = f"{ticker_code}.T" if not ticker_code.endswith(".T") else ticker_code
        company = yf.Ticker(full_code)
        
        # 通期データ取得を試みる
        income = company.financials
        balance = company.balance_sheet
        info = company.info
        
        # 通期が空なら四半期データを試す
        if income.empty:
            income = company.quarterly_financials
        if balance.empty:
            balance = company.quarterly_balance_sheet
            
        if income.empty or balance.empty:
            return {"error": "財務諸表データがサーバーから取得できませんでした。"}

        # 数値データのクレンジング
        income = income.fillna(0)
        balance = balance.fillna(0)

        # 柔軟なキーワード検索でデータを抽出
        rev = get_safe_value(income, ['Total Revenue', 'Operating Revenue', 'Revenue'])
        op_inc = get_safe_value(income, ['Operating Income', 'Operating Profit', 'Pretax Income'])
        net_inc = get_safe_value(income, ['Net Income', 'Net Income Common Stockholders'])
        equity = get_safe_value(balance, ['Stockholders Equity', 'Total Equity', 'Common Stock Equity'])
        assets = get_safe_value(balance, ['Total Assets'])
        
        if rev.empty or rev.iloc[0] == 0:
            return {"error": "売上高データが取得できません。"}

        # 指標計算
        margin = (op_inc.iloc[0] / rev.iloc[0] * 100) if not op_inc.empty else 0
        safety = (equity.iloc[0] / assets.iloc[0] * 100) if not equity.empty else 0
        roe = (net_inc.iloc[0] / equity.iloc[0] * 100) if (not net_inc.empty and not equity.empty and equity.iloc[0] != 0) else 0
        
        # 成長性（トレンド）
        rev_s = rev.sort_index()
        if len(rev_s) > 1:
            X = np.arange(len(rev_s)).reshape(-1, 1)
            trend = (LinearRegression().fit(X, rev_s.values).coef_[0] / rev_s.mean() * 100)
        else:
            trend = 0

        # スコア化 (0-100)
        scores = [
            max(0, min(100, margin * 5)), 
            max(0, min(100, safety * 2)), 
            max(0, min(100, 50 + trend * 5))
        ]
        
        return {
            "scores": scores, "margin": margin, "safety": safety, "trend": trend, "roe": roe,
            "info": info, "rev_history": rev_s, "op_inc_history": op_inc.sort_index(),
            "income_df": income, "balance_df": balance
        }
    except Exception as e:
        return {"error": f"システムエラー: {str(e)}"}

# --- メイン UI ---
st.sidebar.title("🔍 企業分析設定")
ind_list = {
    "自動車": "7203", "IT/電機": "6758", "商社": "8058", "小売": "9983", "ゲーム": "7974"
}
selected_ind = st.sidebar.selectbox("サンプル企業", list(ind_list.keys()))
t_code = st.sidebar.text_input("証券コード (日本株)", ind_list[selected_ind])

if st.sidebar.button("分析実行"):
    with st.spinner("データ取得中..."):
        res = get_full_analysis(t_code)
        
        if "error" in res:
            st.error(res["error"])
            st.info("Yahoo Financeのデータ制限により、一時的に取得できない場合があります。時間を置くか別のコードを試してください。")
        else:
            st.title(f"📊 {t_code} 分析レポート")
            
            # 指標の表示
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("営業利益率", f"{res['margin']:.1f}%")
            c2.metric("自己資本比率", f"{res['safety']:.1f}%")
            c3.metric("成長性トレンド", f"{res['trend']:.1f}%")
            c4.metric("ROE", f"{res['roe']:.1f}%")
            
            # チャート表示
            col_a, col_b = st.columns([1, 1])
            with col_a:
                labels = ["収益性", "安全性", "成長性"]
                fig = go.Figure(data=go.Scatterpolar(r=res['scores'] + [res['scores'][0]], theta=labels + [labels[0]], fill='toself'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="スコア分析")
                st.plotly_chart(fig, use_container_width=True)
            
            with col_b:
                fig2 = make_subplots(specs=[[{"secondary_y": True}]])
                fig2.add_trace(go.Bar(x=res['rev_history'].index.astype(str), y=res['rev_history'].values, name="売上"), secondary_y=False)
                fig2.add_trace(go.Scatter(x=res['op_inc_history'].index.astype(str), y=res['op_inc_history'].values, name="利益"), secondary_y=True)
                fig2.update_layout(title="業績推移")
                st.plotly_chart(fig2, use_container_width=True)
            
            with st.expander("財務諸表の生データを確認"):
                st.write("損益計算書")
                st.dataframe(res['income_df'])

else:
    st.write("左のサイドバーから「分析実行」を押してください。")
