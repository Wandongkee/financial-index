import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta

# 파일 경로 자동 인식 (향후 로컬 엑셀 연동 대비)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. 웹 화면 기본 설정 및 여백 압축
st.set_page_config(layout="wide", page_title="완동키 지표 대시보드")
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    h3 { padding-bottom: 0rem !important; margin-bottom: -0.5rem !important; }
    hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    div[data-testid="metric-container"] { margin-bottom: -0.5rem; }
</style>
""", unsafe_allow_html=True)

st.title("📊 완동키 실시간 금융 지표 대시보드")

# --- 데이터 수집 함수 모음 ---

def get_yf_data(ticker):
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="5d")
        if len(hist) >= 2:
            return hist['Close'].iloc[-1], hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
        return 0, 0
    except:
        return 0, 0

def get_fred_data(ticker):
    try:
        start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
        df = fdr.DataReader(f'FRED:{ticker}', start=start_date)
        df = df.dropna()
        if len(df) >= 2:
            curr = float(df.iloc[-1].values[0])
            prev = float(df.iloc[-2].values[0])
            return curr, curr - prev
        return 0, 0
    except:
        return 0, 0

def get_krx_gold():
    try:
        url = "https://finance.naver.com/marketindex/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        target = soup.select_one('.gold_domestic')
        price_str = target.select_one('.value').text
        price = float(price_str.replace(',', ''))
        
        change_str = target.select_one('.change').text
        change = float(change_str.replace(',', ''))
        
        blind_str = target.select_one('.blind').text
        if "하락" in blind_str:
            change = -change
            
        return price, change
    except:
        return 0, 0

def get_fear_and_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://edition.cnn.com/'
        }
        res = requests.get(url, headers=headers)
        data = res.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        return score, rating
    except:
        return 0, "조회불가"


st.write("---")

# --- 0. 주요 증시 지수 (새로 추가됨) ---
st.subheader("📈 주요 증시 지수")
idx1, idx2, idx3, idx4 = st.columns(4)

with idx1:
    sp500_curr, sp500_change = get_yf_data("^GSPC")
    st.metric("S&P 500", f"{sp500_curr:,.2f}" if sp500_curr else "-", f"{sp500_change:,.2f}" if sp500_change else "-")

with idx2:
    ndx_curr, ndx_change = get_yf_data("^IXIC")
    st.metric("NASDAQ", f"{ndx_curr:,.2f}" if ndx_curr else "-", f"{ndx_change:,.2f}" if ndx_change else "-")

with idx3:
    kospi_curr, kospi_change = get_yf_data("^KS11")
    st.metric("KOSPI", f"{kospi_curr:,.2f}" if kospi_curr else "-", f"{kospi_change:,.2f}" if kospi_change else "-")

with idx4:
    nikkei_curr, nikkei_change = get_yf_data("^N225")
    st.metric("Nikkei 225", f"{nikkei_curr:,.2f}" if nikkei_curr else "-", f"{nikkei_change:,.2f}" if nikkei_change else "-")

st.write("---")

# --- 1. 원/달러 환율 ---
st.subheader("💵 원/달러 환율")
krw_curr, krw_change = get_yf_data("KRW=X")
st.metric("환율", f"{krw_curr:,.2f} 원" if krw_curr else "-", f"{krw_change:,.2f} 원" if krw_change else "-")

st.write("---")

# --- 2. 미 국채 금리 ---
st.subheader("🇺🇸 미 국채 금리")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    irx_curr, irx_change = get_yf_data("^IRX")
    st.metric("3개월물", f"{irx_curr:.3f} %", f"{irx_change:.3f} %")
with c2:
    dgs1_curr, dgs1_change = get_fred_data("DGS1")
    st.metric("1년물", f"{dgs1_curr:.3f} %" if dgs1_curr else "-", f"{dgs1_change:.3f} %" if dgs1_curr else "-")
with c3:
    tnx_curr, tnx_change = get_yf_data("^TNX")
    st.metric("10년물", f"{tnx_curr:.3f} %", f"{tnx_change:.3f} %")
with c4:
    dgs20_curr, dgs20_change = get_fred_data("DGS20")
    st.metric("20년물", f"{dgs20_curr:.3f} %" if dgs20_curr else "-", f"{dgs20_change:.3f} %" if dgs20_curr else "-")
with c5:
    tyx_curr, tyx_change = get_yf_data("^TYX")
    st.metric("30년물", f"{tyx_curr:.3f} %", f"{tyx_change:.3f} %")

st.write("---")

# --- 3. 금 시세 및 김치프리미엄 ---
st.subheader("🥇 금 시세")
g1, g2, g3 = st.columns(3)

with g1:
    gold_curr, gold_change = get_yf_data("GC=F")
    st.metric("국제 금 (온스당)", f"$ {gold_curr:,.2f}" if gold_curr else "-", f"{gold_change:,.2f} $" if gold_change else "-")

with g2:
    krx_curr, krx_change = get_krx_gold()
    st.metric("국내 금 (1g/신한은행 고시)", f"{krx_curr:,.2f} 원" if krx_curr else "조회불가", f"{krx_change:,.2f} 원" if krx_curr else "-")

with g3:
    if gold_curr and krw_curr and krx_curr:
        intl_gold_krw_per_g = (gold_curr * krw_curr) / 31.1034768
        kimchi_premium = ((krx_curr / intl_gold_krw_per_g) - 1) * 100
        st.metric("김치 프리미엄", f"{kimchi_premium:.2f} %", "-")
    else:
        st.metric("김치 프리미엄", "계산 불가", "-")

st.write("---")

# --- 4. 시장 투자 심리 ---
st.subheader("😨 시장 투자 심리")
fg_score, fg_rating = get_fear_and_greed()
st.metric("Fear & Greed Index", f"{fg_score} 점", fg_rating)

st.write("---")

# --- 5. 국제 유가 ---
st.subheader("🛢️ 국제 유가")
o1, o2 = st.columns(2)
with o1:
    wti_curr, wti_change = get_yf_data("CL=F")
    st.metric("WTI (서부텍사스산 원유)", f"$ {wti_curr:,.2f}" if wti_curr else "-", f"{wti_change:,.2f} $" if wti_change else "-")
with o2:
    brent_curr, brent_change = get_yf_data("BZ=F")
    st.metric("브렌트유", f"$ {brent_curr:,.2f}" if brent_curr else "-", f"{brent_change:,.2f} $" if brent_change else "-")
