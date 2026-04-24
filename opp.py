import os
from datetime import datetime, timedelta

import FinanceDataReader as fdr
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup

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

SECTION_KEYS = {
    "주요 증시": "indices",
    "환율": "fx",
    "미 국채": "treasury",
    "금": "gold",
    "투자 심리": "sentiment",
    "국제 유가": "oil",
}

# 1. 웹 화면 기본 설정 및 여백 압축
st.set_page_config(layout="wide", page_title="완동키 지표 대시보드")
st.markdown(
    """
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
    h3 { padding-bottom: 0rem !important; margin-bottom: -0.5rem !important; }
    hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    div[data-testid="metric-container"] { margin-bottom: -0.35rem; }
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
    .top-note {
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 12px;
        background: rgba(128,128,128,.07);
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- 데이터 수집 함수 모음 ---
@st.cache_data(ttl=300)
def get_yf_data(ticker):
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="5d")
        if len(hist) >= 2:
            curr = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            return curr, curr - prev
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=300)
def get_fred_data(ticker):
    try:
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        df = fdr.DataReader(f"FRED:{ticker}", start=start_date)
        df = df.dropna()
        if len(df) >= 2:
            curr = float(df.iloc[-1].values[0])
            prev = float(df.iloc[-2].values[0])
            return curr, curr - prev
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=300)
def get_krx_gold():
    try:
        url = "https://finance.naver.com/marketindex/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        target = soup.select_one(".gold_domestic")
        if target is None:
            return None, None

        price_str = target.select_one(".value").text
        price = float(price_str.replace(",", ""))

        change_str = target.select_one(".change").text
        change = float(change_str.replace(",", ""))

        blind_str = target.select_one(".blind").text
        if "하락" in blind_str:
            change = -change

        return price, change
    except Exception:
        return None, None


@st.cache_data(ttl=300)
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
        if previous_close is not None:
            try:
                score_change = score - int(float(previous_close))
            except (TypeError, ValueError):
                score_change = None

        return score, rating, score_change
    except Exception:
        return None, "조회불가", None


def render_metric_with_link(title, value, delta, source_url):
    st.markdown(
        f'<div class="metric-link"><a href="{source_url}" target="_blank">{title} 🔗</a></div>',
        unsafe_allow_html=True,
    )
    st.metric(label=" ", value=value, delta=delta)


def fmt(value, suffix="", digits=2, unavailable="-"):
    if value is None:
        return unavailable
    return f"{value:,.{digits}f}{suffix}"


def collect_all_data():
    sp500_curr, sp500_change = get_yf_data("^GSPC")
    ndx_curr, ndx_change = get_yf_data("^IXIC")
    kospi_curr, kospi_change = get_yf_data("^KS11")
    nikkei_curr, nikkei_change = get_yf_data("^N225")

    krw_curr, krw_change = get_yf_data("KRW=X")

    irx_curr, irx_change = get_yf_data("^IRX")
    dgs1_curr, dgs1_change = get_fred_data("DGS1")
    tnx_curr, tnx_change = get_yf_data("^TNX")
    dgs20_curr, dgs20_change = get_fred_data("DGS20")
    tyx_curr, tyx_change = get_yf_data("^TYX")

    gold_curr, gold_change = get_yf_data("GC=F")
    krx_curr, krx_change = get_krx_gold()

    fg_score, fg_rating, fg_score_change = get_fear_and_greed()

    wti_curr, wti_change = get_yf_data("CL=F")
    brent_curr, brent_change = get_yf_data("BZ=F")

    kimchi_premium = None
    if gold_curr is not None and krw_curr is not None and krx_curr is not None:
        intl_gold_krw_per_g = (gold_curr * krw_curr) / 31.1034768
        kimchi_premium = ((krx_curr / intl_gold_krw_per_g) - 1) * 100

    return {
        "indices": {
            "S&P 500": (sp500_curr, sp500_change),
            "NASDAQ": (ndx_curr, ndx_change),
            "KOSPI": (kospi_curr, kospi_change),
            "Nikkei 225": (nikkei_curr, nikkei_change),
        },
        "fx": {"환율": (krw_curr, krw_change)},
        "treasury": {
            "3개월물": (irx_curr, irx_change),
            "1년물": (dgs1_curr, dgs1_change),
            "10년물": (tnx_curr, tnx_change),
            "20년물": (dgs20_curr, dgs20_change),
            "30년물": (tyx_curr, tyx_change),
        },
        "gold": {
            "국제 금 (온스당)": (gold_curr, gold_change),
            "국내 금 (1g/신한은행 고시)": (krx_curr, krx_change),
            "김치 프리미엄": (kimchi_premium, None),
        },
        "sentiment": {"Fear & Greed Index": (fg_score, fg_rating, fg_score_change)},
        "oil": {
            "WTI (서부텍사스산 원유)": (wti_curr, wti_change),
            "브렌트유": (brent_curr, brent_change),
        },
    }


def get_data_health(all_data):
    total = 0
    ok = 0
    for section in all_data.values():
        for item in section.values():
            total += 1
            first = item[0]
            if first is not None:
                ok += 1
    return ok, total


def render_indices(data):
    st.subheader("📈 주요 증시 지수")
    idx1, idx2, idx3, idx4 = st.columns(4)
    with idx1:
        v, d = data["indices"]["S&P 500"]
        render_metric_with_link("S&P 500", fmt(v), fmt(d), SOURCE_URLS["S&P 500"])
    with idx2:
        v, d = data["indices"]["NASDAQ"]
        render_metric_with_link("NASDAQ", fmt(v), fmt(d), SOURCE_URLS["NASDAQ"])
    with idx3:
        v, d = data["indices"]["KOSPI"]
        render_metric_with_link("KOSPI", fmt(v), fmt(d), SOURCE_URLS["KOSPI"])
    with idx4:
        v, d = data["indices"]["Nikkei 225"]
        render_metric_with_link("Nikkei 225", fmt(v), fmt(d), SOURCE_URLS["Nikkei 225"])
    st.write("---")


def render_fx(data):
    st.subheader("💵 원/달러 환율")
    v, d = data["fx"]["환율"]
    render_metric_with_link("환율", fmt(v, " 원"), fmt(d, " 원"), SOURCE_URLS["환율"])
    st.write("---")


def render_treasury(data):
    st.subheader("🇺🇸 미 국채 금리")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        v, d = data["treasury"]["3개월물"]
        render_metric_with_link("3개월물", fmt(v, " %", 3), fmt(d, " %", 3), SOURCE_URLS["3개월물"])
    with c2:
        v, d = data["treasury"]["1년물"]
        render_metric_with_link("1년물", fmt(v, " %", 3), fmt(d, " %", 3), SOURCE_URLS["1년물"])
    with c3:
        v, d = data["treasury"]["10년물"]
        render_metric_with_link("10년물", fmt(v, " %", 3), fmt(d, " %", 3), SOURCE_URLS["10년물"])
    with c4:
        v, d = data["treasury"]["20년물"]
        render_metric_with_link("20년물", fmt(v, " %", 3), fmt(d, " %", 3), SOURCE_URLS["20년물"])
    with c5:
        v, d = data["treasury"]["30년물"]
        render_metric_with_link("30년물", fmt(v, " %", 3), fmt(d, " %", 3), SOURCE_URLS["30년물"])

    st.write("---")


def render_gold(data):
    st.subheader("🥇 금 시세")
    g1, g2, g3 = st.columns(3)

    with g1:
        v, d = data["gold"]["국제 금 (온스당)"]
        render_metric_with_link(
            "국제 금 (온스당)",
            f"$ {fmt(v)}" if v is not None else "-",
            f"{fmt(d)} $" if d is not None else "-",
            SOURCE_URLS["국제 금 (온스당)"],
        )

    with g2:
        v, d = data["gold"]["국내 금 (1g/신한은행 고시)"]
        render_metric_with_link(
            "국내 금 (1g/신한은행 고시)",
            fmt(v, " 원", unavailable="조회불가"),
            fmt(d, " 원"),
            SOURCE_URLS["국내 금 (1g/신한은행 고시)"],
        )

    with g3:
        v, _ = data["gold"]["김치 프리미엄"]
        render_metric_with_link(
            "김치 프리미엄",
            fmt(v, " %", unavailable="계산 불가"),
            "-",
            SOURCE_URLS["김치 프리미엄"],
        )

    st.write("---")


def render_sentiment(data):
    st.subheader("😨 시장 투자 심리")
    score, rating, score_change = data["sentiment"]["Fear & Greed Index"]
    render_metric_with_link(
        f"Fear & Greed Index · {rating}",
        f"{score} 점" if score is not None else "조회불가",
        f"{score_change:+} 점" if score_change is not None else "-",
        SOURCE_URLS["Fear & Greed Index"],
    )
    st.write("---")


def render_oil(data):
    st.subheader("🛢️ 국제 유가")
    o1, o2 = st.columns(2)

    with o1:
        v, d = data["oil"]["WTI (서부텍사스산 원유)"]
        render_metric_with_link(
            "WTI (서부텍사스산 원유)",
            f"$ {fmt(v)}" if v is not None else "-",
            f"{fmt(d)} $" if d is not None else "-",
            SOURCE_URLS["WTI (서부텍사스산 원유)"],
        )

    with o2:
        v, d = data["oil"]["브렌트유"]
        render_metric_with_link(
            "브렌트유",
            f"$ {fmt(v)}" if v is not None else "-",
            f"{fmt(d)} $" if d is not None else "-",
            SOURCE_URLS["브렌트유"],
        )

    st.write("---")


st.title("📊 완동키 실시간 금융 지표 대시보드")

with st.sidebar:
    st.header("⚙️ 보기 설정")
    view_mode = st.radio("대시보드 모드", ["핵심만", "전체"], horizontal=True)
    selected_sections = st.multiselect(
        "표시할 섹션",
        list(SECTION_KEYS.keys()),
        default=list(SECTION_KEYS.keys()),
        disabled=view_mode == "핵심만",
    )

    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("데이터는 기본적으로 5분 캐시됩니다.")

all_data = collect_all_data()
ok_count, total_count = get_data_health(all_data)
updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

st.markdown(
    f"<div class='top-note'>🕒 마지막 갱신: <b>{updated_at}</b> &nbsp;|&nbsp; ✅ 수집 성공: <b>{ok_count}/{total_count}</b></div>",
    unsafe_allow_html=True,
)

# 핵심 요약 (상단 고정)
st.subheader("🔥 핵심 요약")
k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    v, d = all_data["indices"]["S&P 500"]
    render_metric_with_link("S&P 500", fmt(v), fmt(d), SOURCE_URLS["S&P 500"])
with k2:
    v, d = all_data["fx"]["환율"]
    render_metric_with_link("환율", fmt(v, " 원"), fmt(d, " 원"), SOURCE_URLS["환율"])
with k3:
    v, d = all_data["treasury"]["10년물"]
    render_metric_with_link(
        "10년물", fmt(v, " %", 3), fmt(d, " %", 3), SOURCE_URLS["10년물"]
    )
with k4:
    v, d = all_data["gold"]["국제 금 (온스당)"]
    render_metric_with_link(
        "국제 금",
        f"$ {fmt(v)}" if v is not None else "-",
        f"{fmt(d)} $" if d is not None else "-",
        SOURCE_URLS["국제 금 (온스당)"],
    )
with k5:
    s, rating, diff = all_data["sentiment"]["Fear & Greed Index"]
    render_metric_with_link(
        f"F&G · {rating}",
        f"{s} 점" if s is not None else "조회불가",
        f"{diff:+} 점" if diff is not None else "-",
        SOURCE_URLS["Fear & Greed Index"],
    )
with k6:
    v, d = all_data["oil"]["WTI (서부텍사스산 원유)"]
    render_metric_with_link(
        "WTI",
        f"$ {fmt(v)}" if v is not None else "-",
        f"{fmt(d)} $" if d is not None else "-",
        SOURCE_URLS["WTI (서부텍사스산 원유)"],
    )

st.write("---")

if view_mode == "핵심만":
    st.info("핵심 지표만 표시 중입니다. 사이드바에서 '전체' 모드로 전환하면 전체 지표를 볼 수 있습니다.")
else:
    section_map = {
        "주요 증시": lambda: render_indices(all_data),
        "환율": lambda: render_fx(all_data),
        "미 국채": lambda: render_treasury(all_data),
        "금": lambda: render_gold(all_data),
        "투자 심리": lambda: render_sentiment(all_data),
        "국제 유가": lambda: render_oil(all_data),
    }
    for section_name in selected_sections:
        section_map[section_name]()
