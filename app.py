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
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None

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
        op_margin = (op_inc_data.iloc[0] / rev_data.iloc[0] * 100)
        equity_ratio = (equity_data.iloc[0] / assets_data.iloc[0] * 100)
        rev_series = rev_data.sort_index(ascending=True)
        X = np.arange(len(rev_series)).reshape(-1, 1)
        y = rev_series.values
        trend = (LinearRegression().fit(X, y).coef_[0] / rev_series.mean() * 100)
        salary = info.get('averageWage') or info.get('averageSalary')
        scores = [max(0, min(100, op_margin * 5)), max(0, min(100, equity_ratio * 2)), max(0, min(100, 50 + trend * 5))]
        return scores, op_margin, equity_ratio, trend, salary
    except: return None

@st.cache_data
def get_industry_averages(industry_name):
    if industry_name not in INDUSTRY_MAP: return None
    comp_list = INDUSTRY_MAP[industry_name]
    m_list, s_list, t_list = [], [], []
    for code in list(comp_list.values())[:5]:
        res = get_analysis(code)
        if res: m_list.append(res[1]); s_list.append(res[2]); t_list.append(res[3])
    if not m_list: return None
    return sum(m_list)/len(m_list), sum(s_list)/len(s_list), sum(t_list)/len(t_list)

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
st.title("🚀 企業分析 & お気に入り機能")
tab1, tab2 = st.tabs(["🔍 1社分析", "⚔️ ライバル比較"])

with tab1:
    t_code, t_name, t_ind = select_company_ui("single")
    if st.button("🔥 分析を実行", key="s_btn"):
        res = get_analysis(t_code)
        if res:
            st.session_state.current_analysis = {'name': t_name, 'res': res, 'ind': t_ind}
        else:
            st.error("データが取得できませんでした。")

    # セッション内に分析結果がある場合のみ表示（これでお気に入りボタンを押しても消えない）
    if st.session_state.current_analysis:
        curr = st.session_state.current_analysis
        scores, margin, safety, trend, salary = curr['res']
        ind_avg = get_industry_averages(curr['ind'])
        
        col1, col2 = st.columns([1.5, 1])
        with col1:
            fig = go.Figure(data=go.Scatterpolar(r=scores + [scores[0]], theta=['収益性','安全性','成長性','収益性'], fill='toself'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.write(f"#### 📊 {curr['name']} の指標")
            st.metric("利益率", f"{margin:.1f}%")
            st.metric("安全性", f"{safety:.1f}%")
            if salary: st.metric("推定年収", f"約{salary:,.0f}円")
        
        if st.button("⭐ この企業をお気に入りに追加"):
            if not any(f['name'] == curr['name'] for f in st.session_state.fav_list):
                st.session_state.fav_list.append({'name': curr['name'], '利益率': f"{margin:.1f}%", '安全性': f"{safety:.1f}%"})
                st.toast(f"{curr['name']} を追加しました！")
            else:
                st.toast("既に追加されています。")

with tab2:
    st.write("比較モードは「1社分析」の安定後に再調整します")

# --- 4. 画面最下部：お気に入りリスト表示 ---
st.divider()
st.subheader("⭐ 検討中リスト")
if st.session_state.fav_list:
    st.dataframe(pd.DataFrame(st.session_state.fav_list), use_container_width=True)
    if st.button("リストをすべて消去"):
        st.session_state.fav_list = []
        st.rerun()
else:
    st.write("お気に入りはありません。分析結果から「追加」してください。")
