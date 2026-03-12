import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta

# 파일 경로 자동 인식
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. 웹 화면 기본 설정 및 여백 압축
st.set_page_config(layout="wide", page_title="동연 지표 대시보드")
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    h3 { padding-bottom: 0rem !important; margin-bottom: -0.5rem !important; }
    hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    div[data-testid="metric-container"] { margin-bottom: -0.5rem; }
</style>
""", unsafe_allow_html=True)

st.title("📊 동연이의 금융 지표 대시보드")

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

# (수정됨) 네이버 금융 국내 금 시세 우회 크롤링
def get_krx_gold():
    try:
        url = "https://finance.naver.com/marketindex/"
        # 사람(웹 브라우저)이 접속하는 것처럼 헤더 추가
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 금융 메인 화면의 '국내 금' 클래스 좌표로 직접 탐색
        price = soup.select_one('.gold_domestic .value').text
        return price
    except:
        return "조회불가"

# (수정됨) CNN Fear & Greed API 우회
def get_fear_and_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        # CNN 서버가 봇을 차단하지 못하도록 Referer(이전 접속 주소) 위장 추가
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

# --- 3. 금 시세 ---
st.subheader("🥇 금 시세")
g1, g2 = st.columns(2)
with g1:
    gold_curr, gold_change = get_yf_data("GC=F")
    st.metric("국제 금 (온스당)", f"$ {gold_curr:,.2f}", f"$ {gold_change:,.2f}")
with g2:
    krx_price = get_krx_gold()
    st.metric("국내 금 (1g/신한은행 고시)", f"{krx_price} 원" if krx_price != "조회불가" else "조회불가", "-")

st.write("---")

# --- 4. 시장 투자 심리 ---
st.subheader("😨 시장 투자 심리")
fg_score, fg_rating = get_fear_and_greed()
st.metric("Fear & Greed Index", f"{fg_score} 점", fg_rating)

