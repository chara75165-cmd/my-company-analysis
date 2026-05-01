import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="企業分析・お気に入り機能版", layout="wide")

# --- 0. セッション状態（記憶）の初期化 ---
if 'fav_list' not in st.session_state:
    st.session_state.fav_list = []

# --- 1. 業種別・企業リスト ---
INDUSTRY_MAP = {
    "自動車・輸送": {"トヨタ": "7203", "ホンダ": "7267", "日産": "7201", "デンソー": "6902", "マツダ": "7261", "スズキ": "7269", "いすゞ": "7202", "SUBARU": "7270"},
    "電機・精密・IT": {"ソニーG": "6758", "パナソニック": "6752", "任天堂": "7974", "キーエンス": "6861", "ソフトバンクG": "9984", "富士通": "6702", "日立": "6501", "キヤノン": "7751", "楽天G": "4755", "メルカリ": "4385", "東京エレクトロン": "8035", "村田製作所": "6981"},
    "金融・商社": {"三菱UFJ": "8306", "三井住友": "8316", "みずほ": "8411", "三菱商事": "8058", "三井物産": "8031", "伊藤忠": "8001", "住友商事": "8053", "丸紅": "8002", "野村HD": "8604"},
    "小売・サービス": {"ファストリ": "9983", "セブン＆アイ": "3382", "リクルート": "6098", "オリエンタルランド": "4661", "ニトリ": "9843", "イオン": "8267", "ANA": "9202", "JAL": "9201"},
    "化学・食品・医薬": {"武田薬品": "4502", "中外製薬": "4519", "信越化学": "4063", "花王": "4452", "アサヒ": "2502", "キリン": "2503", "資生堂": "4911", "味の素": "2802"}
}

# --- 2. 共通関数（分析・UI） ---
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
        op_margin = (op_inc_data.iloc / rev_data.iloc * 100)
        equity_ratio = (equity_data.iloc / assets_data.iloc * 100)
        rev_series = rev_data.sort_index(ascending=True)
        X = np.arange(len(rev_series)).reshape(-1, 1)
        y = rev_series.values
        trend = (LinearRegression().fit(X, y).coef_ / rev_series.mean() * 100)
        salary = info.get('averageWage') or info.get('averageSalary')
        scores = [max(0, min(100, op_margin * 5)), max(0, min(100, equity_ratio * 2)), max(0, min(100, 50 + trend * 5))]
        return scores, op_margin, equity_ratio, trend, salary
    except: return None

@st.cache_data
def get_industry_averages(industry_name):
    if industry_name not in INDUSTRY_MAP: return None
    comp_list = INDUSTRY_MAP[industry_name]
    m_list, e_list, t_list = [], [], []
    for code in list(comp_list.values())[:5]:
        res = get_analysis(code)
        if res: m_list.append(res); e_list.append(res); t_list.append(res)
    if not m_list: return None
    return sum(m_list)/len(m_list), sum(e_list)/len(e_list), sum(t_list)/len(t_list)

def select_company_ui(key_suffix):
    col_a, col_b = st.columns(2)
    with col_a: industry = st.selectbox("業種を選択", list(INDUSTRY_MAP.keys()) + ["直接入力"], key=f"ind_{key_suffix}")
    with col_b:
        if industry == "直接入力":
            code = st.text_input("証券コードを入力", "6758", key=f"code_{key_suffix}")
            name = code
        else:
            name = st.selectbox("企業を選択", list(INDUSTRY_MAP[industry].keys()), key=f"name_{key_suffix}")
            code = INDUSTRY_MAP[industry][name]
    return code, name, industry

# --- 3. メインUI ---
st.title("🚀 企業分析 & お気に入りリスト")
tab1, tab2 = st.tabs(["🔍 1社分析", "⚔️ ライバル比較"])

with tab1:
    t_code, t_name, t_ind = select_company_ui("single")
    if st.button("🔥 分析を実行", key="s_btn"):
        res = get_analysis(t_code)
        ind_avg = get_industry_averages(t_ind)
        if res:
            scores, margin, safety, trend, salary = res
            col1, col2 = st.columns([1.5, 1])
            with col1:
                fig = go.Figure(data=go.Scatterpolar(r=scores + [scores], theta=['収益性','安全性','成長性','収益性'], fill='toself'))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.write(f"#### 📊 {t_ind}平均との比較")
                if ind_avg:
                    avg_m, avg_s, avg_t = ind_avg
                    st.metric("利益率", f"{margin:.1f}%", f"{margin - avg_m:.1f}%")
                    st.metric("安全性", f"{safety:.1f}%", f"{safety - avg_s:.1f}%")
                if salary: st.metric("推定年収", f"約{salary:,.0f}円")
            
            # お気に入り追加ボタン
            if st.button("⭐ この企業をお気に入りに追加"):
                if not any(f['name'] == t_name for f in st.session_state.fav_list):
                    st.session_state.fav_list.append({'name': t_name, 'margin': margin, 'safety': safety, 'trend': trend})
                    st.toast(f"{t_name} を追加しました！")

with tab2:
    c1_code, c1_name, _ = select_company_ui("c1"); c2_code, c2_name, _ = select_company_ui("c2")
    if st.button("⚔️ 比較を開始", key="c_btn"):
        res1, res2 = get_analysis(c1_code), get_analysis(c2_code)
        if res1 and res2:
            s1, m1, sa1, tr1, sal1 = res1; s2, m2, sa2, tr2, sal2 = res2
            col_g, col_m = st.columns([1.5, 1])
            with col_g:
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=s1+[s1], theta=['収益性','安全性','成長性','収益性'], fill='toself', name=c1_name))
                fig.add_trace(go.Scatterpolar(r=s2+[s2], theta=['収益性','安全性','成長性','収益性'], fill='toself', name=c2_name))
                st.plotly_chart(fig, use_container_width=True)
            with col_m:
                st.metric("利益率差", f"{m1:.1f}%", f"{m1-m2:.1f}%")

# --- 4. 画面最下部：お気に入りリスト表示 ---
st.divider()
st.subheader("⭐ 検討中リスト")
if st.session_state.fav_list:
    fav_df = pd.DataFrame(st.session_state.fav_list)
    st.table(fav_df)
    if st.button("リストをすべて消去"):
        st.session_state.fav_list = []
        st.rerun()
else:
    st.write("現在、お気に入りはありません。")
