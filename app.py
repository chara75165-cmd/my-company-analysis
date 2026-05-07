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
    "自動車・輸送": {"トヨタ": "7203", "ホンダ": "7267", "日産": "7201", "デンソー": "6902", "マツダ": "7261", "スズキ": "7269", "いすゞ": "7202", "SUBARU": "7270"},
    "電機・精密・IT": {"ソニーG": "6758", "パナソニック": "6752", "任天堂": "7974", "キーエンス": "6861", "ソフトバンクG": "9984", "富士通": "6702", "日立": "6501", "キヤノン": "7751", "楽天G": "4755", "メルカリ": "4385", "東京エレクトロン": "8035", "村田製作所": "6981"},
    "金融・商社": {"三菱UFJ": "8306", "三井住友": "8316", "みずほ": "8411", "三菱商事": "8058", "三井物産": "8031", "伊藤忠": "8001", "住友商事": "8053", "丸紅": "8002", "野村HD": "8604"},
    "小売・サービス": {"ファストリ": "9983", "セブン＆アイ": "3382", "リクルート": "6098", "オリエンタルランド": "4661", "ニトリ": "9843", "イオン": "8267", "ANA": "9202", "JAL": "9201"},
    "化学・食品・医薬": {"武田薬品": "4502", "中外製薬": "4519", "信越化学": "4063", "花王": "4452", "アサヒ": "2502", "キリン": "2503", "資生堂": "4911", "味の素": "2802"}
}

# --- 共通関数 ---
@st.cache_data(ttl=3600)
def get_full_analysis(ticker_code):
    try:
        company = yf.Ticker(f"{ticker_code}.T")
        income = company.financials
        balance = company.balance_sheet
        cashflow = company.cashflow
        info = company.info
        
        if income.empty or balance.empty: return None

        def get_val(df, keys):
            for k in keys:
                if k in df.index: return df.loc[k]
            return pd.Series([np.nan] * len(df.columns), index=df.columns)

        # 基本データ抽出
        rev = get_val(income, ['Total Revenue', 'Operating Revenue'])
        op_inc = get_val(income, ['Operating Income', 'Pretax Income'])
        net_inc = get_val(income, ['Net Income Common Stockholders', 'Net Income'])
        equity = get_val(balance, ['Stockholders Equity', 'Total Equity'])
        assets = get_val(balance, ['Total Assets'])
        
        # 指標計算
        m = (op_inc.iloc[0] / rev.iloc[0] * 100)
        s = (equity.iloc[0] / assets.iloc[0] * 100)
        roe = (net_inc.iloc[0] / equity.iloc[0] * 100) if equity.iloc[0] != 0 else 0
        
        # 成長性トレンド（線形回帰）
        rev_s = rev.dropna().sort_index()
        X = np.arange(len(rev_s)).reshape(-1, 1)
        t = (LinearRegression().fit(X, rev_s.values).coef_[0] / rev_s.mean() * 100)

        # スコア化
        sc = [max(0, min(100, m * 5)), max(0, min(100, s * 2)), max(0, min(100, 50 + t * 5))]
        
        return {
            "scores": sc, "margin": m, "safety": s, "trend": t, "roe": roe,
            "info": info, "rev_history": rev_s, "op_inc_history": op_inc.sort_index(),
            "income_df": income, "balance_df": balance
        }
    except: return None

@st.cache_data
def get_industry_averages(ind_name):
    if ind_name == "直接入力": return None
    c_list = INDUSTRY_MAP[ind_name]
    m_l, s_l, t_l = [], [], []
    for code in list(c_list.values())[:3]: # 速度優先で上位3社
        res = get_full_analysis(code)
        if res:
            m_l.append(res['margin']); s_l.append(res['safety']); t_l.append(res['trend'])
    return (sum(m_l)/len(m_l), sum(s_l)/len(s_l), sum(t_l)/len(t_l)) if m_l else None

# --- UIパーツ ---
def draw_performance_chart(data):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=data['rev_history'].index.astype(str), y=data['rev_history'].values, name="売上高", marker_color='royalblue'), secondary_y=False)
    fig.add_trace(go.Scatter(x=data['op_inc_history'].index.astype(str), y=data['op_inc_history'].values, name="営業利益", line=dict(color='firebrick', width=3)), secondary_y=True)
    fig.update_layout(title_text="業績推移（売上・利益）", hovermode="x unified", height=350, margin=dict(l=20, r=20, t=50, b=20))
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
    st.subheader("⭐ お気に入り")
    if st.session_state.fav_list:
        fav_df = pd.DataFrame(st.session_state.fav_list)
        st.dataframe(fav_df[['企業名']], hide_index=True)
        if st.button("リスト消去"):
            st.session_state.fav_list = []; st.rerun()

# --- メインコンテンツ ---
st.title("📊 企業分析ダッシュボード Pro")

if analyze_btn or 'last_analysis' in st.session_state:
    target_code = t_code if analyze_btn else st.session_state.get('last_code')
    with st.spinner('財務データを解析中...'):
        res = get_full_analysis(target_code)
        if res:
            st.session_state.last_analysis = res
            st.session_state.last_code = target_code
            st.session_state.last_name = t_name
            
            tab1, tab2, tab3 = st.tabs(["🧐 総合診断", "📈 財務推移", "📋 財務諸表"])
            
            with tab1:
                col1, col2 = st.columns([1, 1])
                with col1:
                    # レーダーチャート
                    fig_radar = go.Figure(data=go.Scatterpolar(r=res['scores'] + [res['scores'][0]], theta=LABELS + [LABELS[0]], fill='toself', name=t_name))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400, margin=dict(l=50, r=50, t=50, b=50))
                    st.plotly_chart(fig_radar, use_container_width=True)
                
                with col2:
                    st.subheader(f"✨ {t_name} の主要指標")
                    i_avg = get_industry_averages(ind)
                    m_val = f"{res['margin']:.1f}%"
                    s_val = f"{res['safety']:.1f}%"
                    t_val = f"{res['trend']:.1f}%"
                    
                    c1, c2 = st.columns(2)
                    c1.metric(LABEL_PROFIT, m_val, f"{res['margin']-(i_avg[0] if i_avg else 0):.1f}%")
                    c2.metric(LABEL_SAFETY, s_val, f"{res['safety']-(i_avg[1] if i_avg else 0):.1f}%")
                    c1.metric(LABEL_GROWTH, t_val, f"{res['trend']-(i_avg[2] if i_avg else 0):.1f}%")
                    c2.metric("効率性 (ROE)", f"{res['roe']:.1f}%")
                    
                    st.divider()
                    st.write("**💰 市場評価 (バリュエーション)**")
                    v1, v2, v3 = st.columns(3)
                    v1.metric("PER", f"{res['info'].get('trailingPE', '-')[:4] if isinstance(res['info'].get('trailingPE'), str) else res['info'].get('trailingPE', '-')}倍")
                    v2.metric("PBR", f"{res['info'].get('priceToBook', '-')}倍")
                    v3.metric("配当利回り", f"{(res['info'].get('dividendYield', 0) or 0)*100:.2f}%")

                st.divider()
                # 診断ロジック
                if res['margin'] > 12 and res['safety'] > 50: 
                    st.success(f"💎 **診断結果: 筋肉質経営の優良企業**\n\n高い収益性と強固な財務基盤を両立しています。業界内でも競争優位性が高い状態です。")
                elif res['trend'] > 10:
                    st.info(f"🚀 **診断結果: 高成長フェーズ**\n\n売上の伸びが著しく、市場シェアを拡大しています。今後の利益転換に注目です。")
                else:
                    st.warning(f"⚖️ **診断結果: 安定志向/成熟フェーズ**\n\n堅実な経営ですが、新たな成長エンジンの模索が必要な時期かもしれません。")

                if st.button("⭐ この企業をお気に入りに追加"):
                    if not any(f['企業名'] == t_name for f in st.session_state.fav_list):
                        st.session_state.fav_list.append({'企業名': t_name, '利益率': m_val, '安全性': s_val})
                        st.toast(f"{t_name}を保存しました")

            with tab2:
                st.subheader("📊 過去数年間の業績パフォーマンス")
                draw_performance_chart(res)
                st.info("💡 棒グラフが売上、折れ線が利益です。両方が右肩上がりなら理想的な成長です。")

            with tab3:
                st.subheader("📑 財務諸表詳細 (Raw Data)")
                show_df = st.checkbox("データフレームを表示")
                if show_df:
                    st.write("### 損益計算書")
                    st.dataframe(res['income_df'])
                    st.write("### 貸借対照表")
                    st.dataframe(res['balance_df'])

        else:
            st.error("データの取得に失敗しました。証券コードが正しいか確認してください。")
else:
    st.info("左側のサイドバーから企業を選択して「分析を実行」をクリックしてください。")
