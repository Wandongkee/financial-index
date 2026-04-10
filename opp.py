import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta

# 파일 경로 자동 인식 (향후 로컬 엑셀 연동 대비)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 출처 URL 매핑
SOURCE_URLS = {
    "S&P 500": "https://finance.yahoo.com/quote/%5EGSPC",
    "NASDAQ": "https://finance.yahoo.com/quote/%5EIXIC",
    "KOSPI": "https://finance.yahoo.com/quote/%5EKS11",
    "Nikkei 225": "https://finance.yahoo.com/quote/%5EN225",
    "환율": "https://finance.yahoo.com/quote/KRW%3DX",
    "3개월물": "https://finance.yahoo.com/quote/%5EIRX",
    "1년물": "https://fred.stlouisfed.org/series/DGS1",
    "10년물": "https://finance.yahoo.com/quote/%5ETNX",
    "20년물": "https://fred.stlouisfed.org/series/DGS20",
    "30년물": "https://finance.yahoo.com/quote/%5ETYX",
    "국제 금 (온스당)": "https://finance.yahoo.com/quote/GC%3DF",
    "국내 금 (1g/신한은행 고시)": "https://finance.naver.com/marketindex/",
    "김치 프리미엄": "https://finance.naver.com/marketindex/",
    "Fear & Greed Index": "https://edition.cnn.com/markets/fear-and-greed",
    "WTI (서부텍사스산 원유)": "https://finance.yahoo.com/quote/CL%3DF",
    "브렌트유": "https://finance.yahoo.com/quote/BZ%3DF",
}

# 1. 웹 화면 기본 설정 및 여백 압축
st.set_page_config(layout="wide", page_title="완동키 지표 대시보드")
st.markdown(
    """
<style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    h3 { padding-bottom: 0rem !important; margin-bottom: -0.5rem !important; }
    hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    div[data-testid="metric-container"] { margin-bottom: -0.5rem; }
    .metric-link {
        font-size: 0.95rem;
        margin-bottom: -0.35rem;
        font-weight: 600;
    }
    .metric-link a {
        text-decoration: none;
        color: inherit;
    }
    .metric-link a:hover {
        text-decoration: underline;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📊 완동키 실시간 금융 지표 대시보드")


# --- 데이터 수집 함수 모음 ---
def get_yf_data(ticker):
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="5d")
        if len(hist) >= 2:
            curr = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            return curr, curr - prev
        return 0, 0
    except Exception:
        return 0, 0


def get_fred_data(ticker):
    try:
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        df = fdr.DataReader(f"FRED:{ticker}", start=start_date)
        df = df.dropna()
        if len(df) >= 2:
            curr = float(df.iloc[-1].values[0])
            prev = float(df.iloc[-2].values[0])
            return curr, curr - prev
        return 0, 0
    except Exception:
        return 0, 0


def get_krx_gold():
    try:
        url = "https://finance.naver.com/marketindex/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        target = soup.select_one(".gold_domestic")
        if target is None:
            return 0, 0

        price_str = target.select_one(".value").text
        price = float(price_str.replace(",", ""))

        change_str = target.select_one(".change").text
        change = float(change_str.replace(",", ""))

        blind_str = target.select_one(".blind").text
        if "하락" in blind_str:
            change = -change

        return price, change
    except Exception:
        return 0, 0


def get_fear_and_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://edition.cnn.com/",
        }
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        fg = data.get("fear_and_greed", {})
        score = int(fg.get("score", 0))
        rating = str(fg.get("rating", "조회불가")).upper()

        previous_close = fg.get("previous_close")
        score_change = None
        try:
            if previous_close is not None:
                score_change = score - int(float(previous_close))
        except (TypeError, ValueError):
            score_change = None

        return score, rating, score_change
    except Exception:
        return 0, "조회불가", None


def render_metric_with_link(title, value, delta, source_url):
    st.markdown(
        f'<div class="metric-link"><a href="{source_url}" target="_blank">{title} 🔗</a></div>',
        unsafe_allow_html=True,
    )
    st.metric(label=" ", value=value, delta=delta)


st.write("---")

# --- 0. 주요 증시 지수 ---
st.subheader("📈 주요 증시 지수")
idx1, idx2, idx3, idx4 = st.columns(4)

with idx1:
    sp500_curr, sp500_change = get_yf_data("^GSPC")
    render_metric_with_link(
        "S&P 500",
        f"{sp500_curr:,.2f}" if sp500_curr else "-",
        f"{sp500_change:,.2f}" if sp500_curr else "-",
        SOURCE_URLS["S&P 500"],
    )

with idx2:
    ndx_curr, ndx_change = get_yf_data("^IXIC")
    render_metric_with_link(
        "NASDAQ",
        f"{ndx_curr:,.2f}" if ndx_curr else "-",
        f"{ndx_change:,.2f}" if ndx_curr else "-",
        SOURCE_URLS["NASDAQ"],
    )

with idx3:
    kospi_curr, kospi_change = get_yf_data("^KS11")
    render_metric_with_link(
        "KOSPI",
        f"{kospi_curr:,.2f}" if kospi_curr else "-",
        f"{kospi_change:,.2f}" if kospi_curr else "-",
        SOURCE_URLS["KOSPI"],
    )

with idx4:
    nikkei_curr, nikkei_change = get_yf_data("^N225")
    render_metric_with_link(
        "Nikkei 225",
        f"{nikkei_curr:,.2f}" if nikkei_curr else "-",
        f"{nikkei_change:,.2f}" if nikkei_curr else "-",
        SOURCE_URLS["Nikkei 225"],
    )

st.write("---")

# --- 1. 원/달러 환율 ---
st.subheader("💵 원/달러 환율")
krw_curr, krw_change = get_yf_data("KRW=X")
render_metric_with_link(
    "환율",
    f"{krw_curr:,.2f} 원" if krw_curr else "-",
    f"{krw_change:,.2f} 원" if krw_curr else "-",
    SOURCE_URLS["환율"],
)

st.write("---")

# --- 2. 미 국채 금리 ---
st.subheader("🇺🇸 미 국채 금리")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    irx_curr, irx_change = get_yf_data("^IRX")
    render_metric_with_link(
        "3개월물",
        f"{irx_curr:.3f} %" if irx_curr else "-",
        f"{irx_change:.3f} %" if irx_curr else "-",
        SOURCE_URLS["3개월물"],
    )

with c2:
    dgs1_curr, dgs1_change = get_fred_data("DGS1")
    render_metric_with_link(
        "1년물",
        f"{dgs1_curr:.3f} %" if dgs1_curr else "-",
        f"{dgs1_change:.3f} %" if dgs1_curr else "-",
        SOURCE_URLS["1년물"],
    )

with c3:
    tnx_curr, tnx_change = get_yf_data("^TNX")
    render_metric_with_link(
        "10년물",
        f"{tnx_curr:.3f} %" if tnx_curr else "-",
        f"{tnx_change:.3f} %" if tnx_curr else "-",
        SOURCE_URLS["10년물"],
    )

with c4:
    dgs20_curr, dgs20_change = get_fred_data("DGS20")
    render_metric_with_link(
        "20년물",
        f"{dgs20_curr:.3f} %" if dgs20_curr else "-",
        f"{dgs20_change:.3f} %" if dgs20_curr else "-",
        SOURCE_URLS["20년물"],
    )

with c5:
    tyx_curr, tyx_change = get_yf_data("^TYX")
    render_metric_with_link(
        "30년물",
        f"{tyx_curr:.3f} %" if tyx_curr else "-",
        f"{tyx_change:.3f} %" if tyx_curr else "-",
        SOURCE_URLS["30년물"],
    )

st.write("---")

# --- 3. 금 시세 및 김치프리미엄 ---
st.subheader("🥇 금 시세")
g1, g2, g3 = st.columns(3)

with g1:
    gold_curr, gold_change = get_yf_data("GC=F")
    render_metric_with_link(
        "국제 금 (온스당)",
        f"$ {gold_curr:,.2f}" if gold_curr else "-",
        f"{gold_change:,.2f} $" if gold_curr else "-",
        SOURCE_URLS["국제 금 (온스당)"],
    )

with g2:
    krx_curr, krx_change = get_krx_gold()
    render_metric_with_link(
        "국내 금 (1g/신한은행 고시)",
        f"{krx_curr:,.2f} 원" if krx_curr else "조회불가",
        f"{krx_change:,.2f} 원" if krx_curr else "-",
        SOURCE_URLS["국내 금 (1g/신한은행 고시)"],
    )

with g3:
    if gold_curr and krw_curr and krx_curr:
        intl_gold_krw_per_g = (gold_curr * krw_curr) / 31.1034768
        kimchi_premium = ((krx_curr / intl_gold_krw_per_g) - 1) * 100
        render_metric_with_link(
            "김치 프리미엄",
            f"{kimchi_premium:.2f} %",
            "-",
            SOURCE_URLS["김치 프리미엄"],
        )
    else:
        render_metric_with_link(
            "김치 프리미엄",
            "계산 불가",
            "-",
            SOURCE_URLS["김치 프리미엄"],
        )

st.write("---")

# --- 4. 시장 투자 심리 ---
st.subheader("😨 시장 투자 심리")
fg_score, fg_rating, fg_score_change = get_fear_and_greed()
render_metric_with_link(
    f"Fear & Greed Index · {fg_rating}",
    f"{fg_score} 점" if fg_score else "조회불가",
    f"{fg_score_change:+} 점" if fg_score_change is not None else "-",
    SOURCE_URLS["Fear & Greed Index"],
)

st.write("---")

# --- 5. 국제 유가 ---
st.subheader("🛢️ 국제 유가")
o1, o2 = st.columns(2)

with o1:
    wti_curr, wti_change = get_yf_data("CL=F")
    render_metric_with_link(
        "WTI (서부텍사스산 원유)",
        f"$ {wti_curr:,.2f}" if wti_curr else "-",
        f"{wti_change:,.2f} $" if wti_curr else "-",
        SOURCE_URLS["WTI (서부텍사스산 원유)"],
    )

with o2:
    brent_curr, brent_change = get_yf_data("BZ=F")
    render_metric_with_link(
        "브렌트유",
        f"$ {brent_curr:,.2f}" if brent_curr else "-",
        f"{brent_change:,.2f} $" if brent_curr else "-",
        SOURCE_URLS["브렌트유"],
    )
