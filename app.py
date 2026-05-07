import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from sklearn.linear_model import LinearRegression

# --- ページ設定 ---
st.set_page_config(page_title="プロフェッショナル企業分析ボード", layout="wide")

# --- 0. セッション状態の初期化 ---
if 'fav_list' not in st.session_state:
    st.session_state.fav_list = []

# --- 名称の定義 ---
LABEL_PROFIT = "収益性（営業利益率）"
LABEL_SAFETY = "安全性（自己資本比率）"
LABEL_GROWTH = "成長性（売上トレンド）"
LABELS = [LABEL_PROFIT, LABEL_SAFETY, LABEL_GROWTH]

INDUSTRY_MAP = {
    "自動車・輸送": {"トヨタ": "7203", "ホンダ": "7267", "日産": "7201", "デンソー": "6902"},
    "電機・精密・IT": {"ソニーG": "6758", "パナソニック": "6752", "任天堂": "7974", "キーエンス": "6861"},
    "金融・商社": {"三菱UFJ": "8306", "三井住友": "8316", "三菱商事": "8058", "伊藤忠": "8001"},
    "小売・サービス": {"ファストリ": "9983", "セブン＆アイ": "3382", "リクルート": "6098", "オリエンタルランド": "4661"},
    "化学・食品・医薬": {"武田薬品": "4502", "中外製薬": "4519", "信越化学": "4063", "花王": "4452"}
}

# --- 共通関数 ---
@st.cache_data(ttl=3600)
def get_full_analysis(ticker_code):
    try:
        # 日本株の場合は .T を付与
        full_code = f"{ticker_code}.T" if not ticker_code.endswith(".T") else ticker_code
        company = yf.Ticker(full_code)
        
        income = company.financials
        balance = company.balance_sheet
        info = company.info
        
        if income.empty or balance.empty:
            return None

        # データの欠損を0で埋める
        income = income.fillna(0)
        balance = balance.fillna(0)

        def get_val(df, keys):
            for k in keys:
                if k in df.index:
                    return df.loc[k]
            return pd.Series([0] * len(df.columns), index=df.columns)

        # 基本データ抽出
        rev = get_val(income, ['Total Revenue', 'Operating Revenue', 'Total Operating Profit'])
        op_inc = get_val(income, ['Operating Income', 'Pretax Income', 'Normalized Income'])
        net_inc = get_val(income, ['Net Income Common Stockholders', 'Net Income', 'Net Income From Continuing Operation Net Minority Interest'])
        equity = get_val(balance, ['Stockholders Equity', 'Total Equity', 'Common Stock Equity'])
        assets = get_val(balance, ['Total Assets'])
        
        if rev.iloc[0] == 0: return None

        # 指標計算
        m = (op_inc.iloc[0] / rev.iloc[0] * 100)
        s = (equity.iloc[0] / assets.iloc[0] * 100)
        roe = (net_inc.iloc[0] / equity.iloc[0] * 100) if equity.iloc[0] != 0 else 0
        
        # 成長性トレンド（線形回帰）
        rev_s = rev.replace(0, np.nan).dropna().sort_index()
        if len(rev_s) > 1:
            X = np.arange(len(rev_s)).reshape(-1, 1)
            t = (LinearRegression().fit(X, rev_s.values).coef_[0] / rev_s.mean() * 100)
        else:
            t = 0

        # スコア化 (0-100)
        sc = [
            max(0, min(100, m * 5)), 
            max(0, min(100, s * 2)), 
            max(0, min(100, 50 + t * 5))
        ]
        
        return {
            "scores": sc, "margin": m, "safety": s, "trend": t, "roe": roe,
            "info": info, "rev_history": rev_s, "op_inc_history": op_inc.sort_index(),
            "income_df": income, "balance_df": balance
        }
    except Exception as e:
        print(f"Error analyzing {ticker_code}: {e}")
        return None

# --- UIパーツ ---
def draw_performance_chart(data):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # 日付形式をきれいに
    x_axis = [d.strftime('%Y-%m') if hasattr(d, 'strftime') else str(d) for d in data['rev_history'].index]
    
    fig.add_trace(go.Bar(x=x_axis, y=data['rev_history'].values, name="売上高", marker_color='royalblue'), secondary_y=False)
    fig.add_trace(go.Scatter(x=x_axis, y=data['op_inc_history'].values, name="営業利益", line=dict(color='firebrick', width=3)), secondary_y=True)
    fig.update_layout(title_text="業績推移（売上・利益）", hovermode="x unified", height=350)
    st.plotly_chart(fig, use_container_width=True)

# --- サイドバー ---
with st.sidebar:
    st.title("⚙️ 設定・銘柄選択")
    ind = st.selectbox("業種を選択", list(INDUSTRY_MAP.keys()) + ["直接入力"])
    if ind == "直接入力":
        t_code = st.text_input("証券コード (例: 7203)", "6758")
        t_name = t_code
    else:
        t_name = st.selectbox("企業を選択", list(INDUSTRY_MAP[ind].keys()))
        t_code = INDUSTRY_MAP[ind][t_name]
    
    analyze_btn = st.button("🚀 分析を実行", use_container_width=True)
    
    st.divider()
    if st.session_state.fav_list:
        st.subheader("⭐ お気に入り")
        fav_df = pd.DataFrame(st.session_state.fav_list)
        st.dataframe(fav_df[['企業名']], hide_index=True)
        if st.button("リスト消去"):
            st.session_state.fav_list = []; st.rerun()

# --- メインコンテンツ ---
st.title("📊 企業分析ダッシュボード Pro")

# 分析実行
res = None
if analyze_btn:
    with st.spinner(f'{t_name} のデータを取得中...'):
        res = get_full_analysis(t_code)
        if res:
            st.session_state.last_analysis = res
            st.session_state.last_name = t_name
        else:
            st.error("データの取得に失敗しました。証券コードが正しいか、または財務データが公開されているか確認してください。")

# 結果表示
if 'last_analysis' in st.session_state:
    res = st.session_state.last_analysis
    t_name = st.session_state.last_name
    
    tab1, tab2, tab3 = st.tabs(["🧐 総合診断", "📈 財務推移", "📋 財務諸表"])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            fig_radar = go.Figure(data=go.Scatterpolar(r=res['scores'] + [res['scores'][0]], theta=LABELS + [LABELS[0]], fill='toself'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
            st.plotly_chart(fig_radar, use_container_width=True)
        
        with col2:
            st.subheader(f"✨ {t_name} の主要指標")
            c1, c2 = st.columns(2)
            c1.metric(LABEL_PROFIT, f"{res['margin']:.1f}%")
            c2.metric(LABEL_SAFETY, f"{res['safety']:.1f}%")
            c1.metric(LABEL_GROWTH, f"{res['trend']:.1f}%")
            c2.metric("効率性 (ROE)", f"{res['roe']:.1f}%")
            
            st.divider()
            st.write("**💰 市場評価 (バリュエーション)**")
            v1, v2, v3 = st.columns(3)
            # infoから取得する際の安全な取り方
            per = res['info'].get('trailingPE')
            pbr = res['info'].get('priceToBook')
            div = res['info'].get('dividendYield', 0)
            
            v1.metric("PER", f"{per:.1f}倍" if per else "-")
            v2.metric("PBR", f"{pbr:.1f}倍" if pbr else "-")
            v3.metric("配当利回り", f"{div*100:.2f}%" if div else "0.00%")

        st.divider()
        if res['margin'] > 12:
            st.success("**診断: 💎 高収益企業** - 効率的に利益を生み出せています。")
        else:
            st.info("**診断: ⚖️ 標準的経営** - 安定した財務状況です。")

        if st.button("⭐ お気に入りに追加"):
            if not any(f['企業名'] == t_name for f in st.session_state.fav_list):
                st.session_state.fav_list.append({'企業名': t_name, '利益率': f"{res['margin']:.1f}%"})
                st.toast(f"{t_name}を保存しました")

    with tab2:
        draw_performance_chart(res)

    with tab3:
        st.write("### 損益計算書")
        st.dataframe(res['income_df'])
        st.write("### 貸借対照表")
        st.dataframe(res['balance_df'])
else:
    st.write("左側のメニューから企業を選んで「分析を実行」を押してください。")
