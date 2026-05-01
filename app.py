import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="企業分析ダッシュボード", layout="wide")

# --- 0. セッション状態の初期化 ---
if 'fav_list' not in st.session_state:
    st.session_state.fav_list = []
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None

# --- 名称の定義（統一） ---
LABEL_PROFIT = "収益性（利益率）"
LABEL_SAFETY = "安全性（資本比率）"
LABEL_GROWTH = "成長性（トレンド）"
LABELS = [LABEL_PROFIT, LABEL_SAFETY, LABEL_GROWTH]

# --- 1. 業種別・企業リスト ---
INDUSTRY_MAP = {
    "自動車・輸送": {"トヨタ": "7203", "ホンダ": "7267", "日産": "7201", "デンソー": "6902", "マツダ": "7261", "スズキ": "7269", "いすゞ": "7202", "SUBARU": "7270"},
    "電機・精密・IT": {"ソニーG": "6758", "パナソニック": "6752", "任天堂": "7974", "キーエンス": "6861", "ソフトバンクG": "9984", "富士通": "6702", "日立": "6501", "キヤノン": "7751", "楽天G": "4755", "メルカリ": "4385", "東京エレクトロン": "8035", "村田製作所": "6981"},
    "金融・商社": {"三菱UFJ": "8306", "三井住友": "8316", "みずほ": "8411", "三菱商事": "8058", "三井物産": "8031", "伊藤忠": "8001", "住友商事": "8053", "丸紅": "8002", "野村HD": "8604"},
    "小売・サービス": {"ファストリ": "9983", "セブン＆アイ": "3382", "リクルート": "6098", "オリエンタルランド": "4661", "ニトリ": "9843", "イオン": "8267", "ANA": "9202", "JAL": "9201"},
    "化学・食品・医薬": {"武田薬品": "4502", "中外製薬": "4519", "信越化学": "4063", "花王": "4452", "アサヒ": "2502", "キリン": "2503", "資生堂": "4911", "味の素": "2802"}
}

# --- 2. 共通関数 ---
@st.cache_data(ttl=3600)
def get_analysis(ticker_code):
    try:
        company = yf.Ticker(f"{ticker_code}.T")
        income = company.financials
        balance = company.balance_sheet
        info = company.info
        if income.empty or balance.empty: return None

        def get_val(df, keys):
            for k in keys:
                if k in df.index: return df.loc[k]
            return None

        rev_data = get_val(income, ['Total Revenue', 'Operating Revenue'])
        op_inc_data = get_val(income, ['Operating Income', 'Pretax Income'])
        equity_data = get_val(balance, ['Stockholders Equity', 'Total Equity'])
        assets_data = get_val(balance, ['Total Assets'])

        m = (op_inc_data.iloc[0] / rev_data.iloc[0] * 100)
        s = (equity_data.iloc[0] / assets_data.iloc[0] * 100)
        
        rev_series = rev_data.sort_index(ascending=True)
        X = np.arange(len(rev_series)).reshape(-1, 1)
        y = rev_series.values
        t = (LinearRegression().fit(X, y).coef_[0] / rev_series.mean() * 100)
        
        salary = info.get('averageWage') or info.get('averageSalary')
        sc = [max(0, min(100, m * 5)), max(0, min(100, s * 2)), max(0, min(100, 50 + t * 5))]
        return sc, m, s, t, salary
    except: return None

@st.cache_data
def get_industry_averages(ind_name):
    if ind_name not in INDUSTRY_MAP: return None
    c_list = INDUSTRY_MAP[ind_name]
    m_l, s_l, t_l = [], [], []
    for code in list(c_list.values())[:5]:
        res = get_analysis(code)
        if res:
            m_l.append(res[1]); s_l.append(res[2]); t_l.append(res[3])
    if not m_l: return None
    return sum(m_l)/len(m_l), sum(s_l)/len(s_l), sum(t_l)/len(t_l)

def select_company_ui(suffix):
    col_a, col_b = st.columns(2)
    with col_a: ind = st.selectbox("業種を選択", list(INDUSTRY_MAP.keys()) + ["直接入力"], key=f"ind_{suffix}")
    with col_b:
        if ind == "直接入力":
            code = st.text_input("証券コード", "6758", key=f"code_{suffix}")
            name = code
        else:
            name = st.selectbox("企業を選択", list(INDUSTRY_MAP[ind].keys()), key=f"name_{suffix}")
            code = INDUSTRY_MAP[ind][name]
    return code, name, ind

# --- 3. メインUI ---
st.title("🚀 企業分析ダッシュボード")
tab1, tab2 = st.tabs(["🔍 1社分析", "⚔️ ライバル比較"])

with tab1:
    t_code, t_name, t_ind = select_company_ui("single")
    if st.button("🔥 分析を実行", key="s_btn"):
        with st.spinner('データを取得中...'):
            res = get_analysis(t_code)
            if res: st.session_state.current_analysis = {'name': t_name, 'res': res, 'ind': t_ind}
            else: st.error("データを取得できませんでした。")

    if st.session_state.current_analysis:
        curr = st.session_state.current_analysis
        scores, margin, safety, trend, salary = curr['res']
        ind_avg = get_industry_averages(curr['ind'])

        col_g, col_v = st.columns([1.5, 1])
        with col_g:
            fig = go.Figure(data=go.Scatterpolar(r=scores + [scores[0]], theta=LABELS + [LABELS[0]], fill='toself'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col_v:
            st.write(f"#### 📊 {curr['ind']}平均との比較")
            if ind_avg:
                am, asf, at = ind_avg
                st.metric(LABEL_PROFIT, f"{margin:.1f}%", f"{margin - am:.1f}%")
                st.metric(LABEL_SAFETY, f"{safety:.1f}%", f"{safety - asf:.1f}%")
                st.metric(LABEL_GROWTH, f"{trend:.1f}%", f"{trend - at:.1f}%")
            
            with st.expander("📝 指標の解説"):
                st.caption(f"**{LABEL_PROFIT}**: 稼ぐ効率。10%超で優良。")
                st.caption(f"**{LABEL_SAFETY}**: 会社の安全性。40%以上で安定。")
                st.caption(f"**{LABEL_GROWTH}**: 売上の伸び。プラスなら拡大中。")

        st.divider()
        st.subheader("🧐 診断レポート")
        if margin > 15 and safety > 60: d_l, d_c = "💎 完璧モデル", "収益・安全性ともに業界トップクラスです。"
        elif trend > 10: d_l, d_c = "🚀 急成長株", "市場を拡大中の勢いがある企業です。"
        elif safety > 70: d_l, d_c = "🏯 超安定型", "財務基盤が盤石。長く働ける環境です。"
        else: d_l, d_c = "⚖️ バランス型", "堅実な経営。標準的な財務状況です。"
        
        st.info(f"**診断結果: {d_l}**")
        st.write(f"**アドバイス:** {d_c}")
        if salary: st.metric("推定平均年収", f"約{salary:,.0f}円")

        if st.button("⭐ お気に入りに追加"):
            if not any(f['企業名'] == curr['name'] for f in st.session_state.fav_list):
                st.session_state.fav_list.append({
                    '企業名': curr['name'], LABEL_PROFIT: f"{margin:.1f}%", LABEL_SAFETY: f"{safety:.1f}%", LABEL_GROWTH: f"{trend:.1f}%"
                })
                st.toast("追加しました！")

with tab2:
    st.subheader("ライバル比較")
    c1_c, c1_n, _ = select_company_ui("c1")
    c2_c, c2_n, _ = select_company_ui("c2")
    if st.button("⚔️ 比較を開始", key="c_btn"):
        with st.spinner('データを対照中...'):
            res1, res2 = get_analysis(c1_c), get_analysis(c2_c)
            if res1 and res2:
                s1, m1, sa1, tr1, _ = res1; s2, m2, sa2, tr2, _ = res2
                col_cg, col_cm = st.columns([1.5, 1])
                with col_cg:
                    fig_c = go.Figure()
                    fig_c.add_trace(go.Scatterpolar(r=s1+[s1[0]], theta=LABELS+[LABELS[0]], fill='toself', name=c1_n))
                    fig_c.add_trace(go.Scatterpolar(r=s2+[s2[0]], theta=LABELS+[LABELS[0]], fill='toself', name=c2_n))
                    fig_c.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450)
                    st.plotly_chart(fig_c, use_container_width=True)
                with col_cm:
                    st.caption(f"※ {c1_n} 基準の差分")
                    st.metric(f"{LABEL_PROFIT}差", f"{m1:.1f}%", f"{m1-m2:.1f}%")
                    st.metric(f"{LABEL_SAFETY}差", f"{sa1:.1f}%", f"{sa1-sa2:.1f}%")
                    st.metric(f"{LABEL_GROWTH}差", f"{tr1:.1f}%", f"{tr1-tr2:.1f}%")

st.divider()
st.subheader("⭐ 検討中リスト & ランキング")
if st.session_state.fav_list:
    df_fav = pd.DataFrame(st.session_state.fav_list)
    df_rank = df_fav.copy()
    for col in [LABEL_PROFIT, LABEL_SAFETY, LABEL_GROWTH]:
        df_rank[col] = df_rank[col].str.replace('%', '').astype(float)
    
    sort_key = st.radio("並び替え基準", ["登録順"] + LABELS, horizontal=True)
    if sort_key != "登録順":
        df_rank = df_rank.sort_values(by=sort_key, ascending=False)
    
    df_rank.index = np.arange(1, len(df_rank) + 1)
    st.table(df_rank)
    if st.button("リストを消去"):
        st.session_state.fav_list = []; st.rerun()
else:
    st.write("お気に入りはありません。")
