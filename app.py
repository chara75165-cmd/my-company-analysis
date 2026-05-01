import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="企業分析・精密診断ボード", layout="wide")

# --- 1. 業種別・企業リスト ---
INDUSTRY_MAP = {
    "自動車・輸送機器": {"トヨタ自動車": "7203", "ホンダ": "7267", "日産自動車": "7201", "デンソー": "6902"},
    "電機・精密・IT": {"ソニーグループ": "6758", "パナソニック": "6752", "任天堂": "7974", "キーエンス": "6861", "ソフトバンクG": "9984", "富士通": "6702", "日立製作所": "6501", "キヤノン": "7751"},
    "金融・保険": {"三菱UFJ": "8306", "三井住友FG": "8316", "みずほFG": "8411", "東京海上HD": "8766"},
    "小売・サービス・飲食": {"ファーストリテイリング": "9983", "セブン＆アイ": "3382", "リクルートHD": "6098", "オリエンタルランド": "4661"},
    "化学・医薬品": {"武田薬品": "4502", "中外製薬": "4519", "信越化学": "4063", "花王": "4452"}
}

# --- 2. 共通関数（分析ロジック） ---
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
        employees = info.get('fullTimeEmployees')

        scores = [max(0, min(100, op_margin * 5)), max(0, min(100, equity_ratio * 2)), max(0, min(100, 50 + trend * 5))]
        return scores, op_margin, equity_ratio, trend, salary, employees
    except:
        return None

@st.cache_data
def get_industry_averages(industry_name):
    if industry_name not in INDUSTRY_MAP: return None
    comp_list = INDUSTRY_MAP[industry_name]
    m_list, e_list, t_list = [], [], []
    for name, code in comp_list.items():
        res = get_analysis(code)
        if res:
            m_list.append(res[1]); e_list.append(res[2]); t_list.append(res[3])
    if not m_list: return None
    return sum(m_list)/len(m_list), sum(e_list)/len(e_list), sum(t_list)/len(t_list)

def select_company_ui(key_suffix):
    col_a, col_b = st.columns(2)
    with col_a:
        industry = st.selectbox("業種を選択", list(INDUSTRY_MAP.keys()) + ["直接入力"], key=f"ind_{key_suffix}")
    with col_b:
        if industry == "直接入力":
            code = st.text_input("証券コードを入力", "6758", key=f"code_{key_suffix}")
            name = code
        else:
            name = st.selectbox("企業を選択", list(INDUSTRY_MAP[industry].keys()), key=f"name_{key_suffix}")
            code = INDUSTRY_MAP[industry][name]
    return code, name, industry

# --- 3. メインUI ---
st.title("🚀 企業分析 & 精密診断ダッシュボード")
tab1, tab2 = st.tabs(["🔍 1社じっくり分析", "⚔️ ライバル比較"])

with tab1:
    t_code, t_name, t_ind = select_company_ui("single")
    if st.button("🔥 分析を実行", key="s_btn"):
        res = get_analysis(t_code)
        ind_avg = get_industry_averages(t_ind)
        if res:
            scores, margin, safety, trend, salary, emp = res
            col1, col2 = st.columns([1.5, 1])
            with col1:
                fig = go.Figure(data=go.Scatterpolar(r=scores + [scores[0]], theta=['収益性','安全性','成長性','収益性'], fill='toself'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.write(f"#### 📊 {t_ind}平均との比較")
                if ind_avg:
                    avg_m, avg_s, avg_t = ind_avg
                    st.metric("営業利益率", f"{margin:.1f}%", f"{margin - avg_m:.1f}%")
                    st.metric("自己資本比率", f"{safety:.1f}%", f"{safety - avg_s:.1f}%")
                    st.metric("成長トレンド", f"{trend:.1f}%", f"{trend - avg_t:.1f}%")
                
                with st.expander("📝 指標の解説を見る"):
                    st.caption("**収益性**: 本業で稼ぐ効率。10%超で優良。")
                    st.caption("**安全性**: 倒産リスク。40%以上で安定。")
                    st.caption("**成長性**: 将来の勢い。プラスなら拡大中。")

            st.divider()
            # --- 精密診断ロジック ---
            st.subheader("🧐 独自診断レポート")
            diag_label, diag_comment = "分析中", ""
            
            if margin > 15 and safety > 60:
                diag_label = "💎 ダイヤモンド・キャッシュカウ"
                diag_comment = "極めて高い収益性と鉄壁の財務を両立。業界の支配者的な存在です。"
            elif trend > 15 and margin > 5:
                diag_label = "🚀 ライジング・スター"
                diag_comment = "驚異的なスピードで急成長中。市場シェアを急速に奪っています。"
            elif safety > 70 and trend < 0:
                diag_label = "🏯 老舗の守護神"
                diag_comment = "成長は落ち着いていますが、資産が豊富で非常に潰れにくい安定企業です。"
            elif margin < 5 and trend > 10:
                diag_label = "🏃 先行投資型スピードランナー"
                diag_comment = "利益を削ってでも成長を優先。将来の化け方に期待のフェーズです。"
            else:
                diag_label = "⚖️ 堅実なバランスプレイヤー"
                diag_comment = "業界標準を維持しつつ、着実に事業を継続している健康的な企業です。"

            st.info(f"**診断タイプ: {diag_label}**")
            st.write(f"**アドバイス:** {diag_comment}")

            if salary: st.metric("推定平均年収", f"約{salary:,.0f}円")

with tab2:
    c1_code, c1_name, _ = select_company_ui("c1")
    c2_code, c2_name, _ = select_company_ui("c2")
    if st.button("⚔️ 比較を開始", key="c_btn"):
        res1, res2 = get_analysis(c1_code), get_analysis(c2_code)
        if res1 and res2:
            s1, m1, sa1, tr1, sal1, e1 = res1
            s2, m2, sa2, tr2, sal2, e2 = res2
            col_g, col_m = st.columns([1.5, 1])
            with col_g:
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=s1+[s1[0]], theta=['収益性','安全性','成長性','収益性'], fill='toself', name=c1_name))
                fig.add_trace(go.Scatterpolar(r=s2+[s2[0]], theta=['収益性','安全性','成長性','収益性'], fill='toself', name=c2_name))
                st.plotly_chart(fig, use_container_width=True)
            with col_m:
                st.caption(f"※ {c1_name} を基準とした比較")
                st.metric("利益率", f"{m1:.1f}%", f"{m1-m2:.1f}%")
                st.metric("資本比率", f"{sa1:.1f}%", f"{sa1-sa2:.1f}%")
                if sal1 and sal2: st.metric("推定年収差", f"約{sal1:,.0f}円", f"{sal1-sal2:,.0f}円")
