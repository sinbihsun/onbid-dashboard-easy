# app.py — 온비드 공매 대시보드 (담당자 필터 / 단일 CSV 지원 / 견고한 전처리)
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np

st.set_page_config(page_title="🏦 온비드 공매 대시보드 (담당자 필터)", layout="wide")

# -----------------------------
# 0) 유틸: CSV 안전 로더
# -----------------------------
def read_csv_robust(src):
    """
    utf-8-sig, utf-8, cp949 순으로 시도.
    업로드 파일(파일 객체)일 경우엔 먼저 인코딩 옵션 없이 시도.
    """
    # UploadedFile 같은 파일 객체 처리
    if hasattr(src, "read"):
        try:
            return pd.read_csv(src)
        except Exception:
            src.seek(0)  # 파일 포인터 복구
            # 파일 객체에 인코딩 지정은 드뭄. 실패 시 한 번 더 기본으로 시도.
            return pd.read_csv(src)

    # 경로(str/Path) 처리
    encodings = ["utf-8-sig", "utf-8", "cp949"]
    last_err = None
    for enc in encodings:
        try:
            return pd.read_csv(src, encoding=enc)
        except Exception as e:
            last_err = e
            continue
    raise last_err

# -----------------------------
# 1) 로더: 다양한 파일명/위치를 탐색
# -----------------------------
@st.cache_data(show_spinner=False)
def load_df():
    here = Path(__file__).resolve().parent
    cwd  = Path.cwd()

    # 가능한 파일 후보 (리포 루트의 sample_onbid.csv가 최우선)
    candidate_files = [
        here / "sample_onbid.csv",
        cwd / "sample_onbid.csv",
        here / "data" / "sample_onbid.csv",
        here / "data" / "cases_enriched_sample.csv",
        here / "data" / "internal_export_sample.csv",
        here.parent / "data" / "sample_onbid.csv",
    ]

    searched = []
    for p in candidate_files:
        searched.append(str(p))
        if p.exists():
            return read_csv_robust(p)

    # 못 찾으면 업로드 유도
    st.warning(
        "데이터 CSV 파일을 찾지 못했습니다. 아래 경로에서 탐색했습니다:\n\n- "
        + "\n- ".join(searched)
        + "\n\n리포 루트에 sample_onbid.csv를 두거나, 아래에서 CSV를 업로드하세요."
    )
    uploaded = st.file_uploader("CSV 업로드", type=["csv"])
    if uploaded is not None:
        return read_csv_robust(uploaded)
    st.stop()

# -----------------------------------
# 2) 전처리: 컬럼이 부족해도 안전하게 채우기
# -----------------------------------
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ---------- 기본 컬럼 보강 ----------
    if "case_id" not in df.columns:
        df["case_id"] = [f"C{i:04d}" for i in range(1, len(df) + 1)]
    if "name_masked" not in df.columns:
        df["name_masked"] = "가*"
    if "officer" not in df.columns:
        df["officer"] = "미지정"
    if "region" not in df.columns:
        df["region"] = "미정"
    if "district" not in df.columns:
        df["district"] = "미정"
    if "stage" not in df.columns:
        df["stage"] = "미정"

    # amount_total 없으면 추정(숫자형 'amount/금액' 컬럼 합)
    if "amount_total" not in df.columns:
        cand = [c for c in df.columns if ("amount" in c.lower()) or ("금액" in c)]
        if cand:
            df["amount_total"] = (
                df[cand].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
            )
        else:
            df["amount_total"] = 0

    # ---------- 날짜 컬럼 안전 처리 ----------
    def pick_date(colnames):
        for c in colnames:
            if c in df.columns:
                return c
        return None

    # 체납 기준일 후보(필요 시 컬럼명 추가)
    delinquent_col = pick_date(
        ["delinquent_since", "체납일자", "체납일", "arrears_since", "delinquentDate"]
    )
    # 공매 마감일 후보
    bid_end_col = pick_date(["bid_end", "매각기일", "입찰마감", "end_date", "bidEnd"])

    # to_datetime (없으면 NaT)
    dser = (
        pd.to_datetime(df[delinquent_col], errors="coerce")
        if delinquent_col
        else pd.Series(pd.NaT, index=df.index)
    )
    bend = (
        pd.to_datetime(df[bid_end_col], errors="coerce")
        if bid_end_col
        else pd.Series(pd.NaT, index=df.index)
    )

    today = pd.Timestamp(datetime.today().date())
    df["delinquent_since"] = dser
    df["days_delinquent"] = (today - dser).dt.days

    df["bid_end"] = bend
    df["due_days"] = (bend - today).dt.days

    # ---------- 공매 금액/비율 ----------
    df["appraisal_price"] = pd.to_numeric(df.get("appraisal_price"), errors="coerce")
    df["min_bid_price"]   = pd.to_numeric(df.get("min_bid_price"), errors="coerce")
    with np.errstate(invalid="ignore", divide="ignore"):
        df["min_ratio"] = (df["min_bid_price"] / df["appraisal_price"]).round(4)

    # ---------- 우선순위(간이) ----------
    try:
        df["priority_tier"] = pd.qcut(
            df["amount_total"].fillna(0), 3, labels=["C", "B", "A"]
        )
    except Exception:
        df["priority_tier"] = "B"

    # 매칭 상태 기본값
    if "match_status" not in df.columns:
        df["match_status"] = "unlinked"

    # 링크 기본값
    if "source_url" not in df.columns:
        df["source_url"] = ""

    return df

# ===================================
# 3) 메인: 데이터 로드 & 전처리
# ===================================
raw = load_df()
df = ensure_columns(raw)

st.title("🏦 온비드 공매 대시보드 (담당자 필터)")

# ===================================
# 4) 사이드바 필터 (A 방식: 담당자)
# ===================================
st.sidebar.header("필터")
my_name = st.sidebar.text_input(
    "내 이름(담당자)", value="", help="예: 김주무 (부분 입력 가능)"
)
only_mine = st.sidebar.checkbox("내가 관리하는 케이스만 보기", value=True)

sel_stages = st.sidebar.multiselect(
    "진행단계", sorted(df["stage"].dropna().astype(str).unique().tolist())
)
sel_tiers = st.sidebar.multiselect("우선순위", ["A", "B", "C"])
due_in = st.sidebar.slider("공매 마감 D-일 이내", 0, 60, 7)

f = df.copy()
if only_mine and my_name.strip():
    patt = my_name.strip()
    f = f[f["officer"].astype(str).str.contains(patt, case=False, na=False)]
if sel_stages:
    f = f[f["stage"].isin(sel_stages)]
if sel_tiers:
    f = f[f["priority_tier"].isin(sel_tiers)]
f = f[(f["due_days"] <= due_in) | f["due_days"].isna()]

# ===================================
# 5) KPI + 테이블
# ===================================
c1, c2, c3 = st.columns(3)
c1.metric("총 체납액(만원)", int(f["amount_total"].fillna(0).sum() / 10000) if len(f) else 0)
c2.metric("공매 연계 건수", int((f["match_status"] == "linked").sum()) if len(f) else 0)
c3.metric("A등급 수", int((f["priority_tier"] == "A").sum()) if len(f) else 0)

st.markdown("### 결과 목록")
cols = [
    "case_id",
    "name_masked",
    "officer",
    "region",
    "district",
    "stage",
    "amount_total",
    "min_ratio",
    "bid_end",
    "priority_tier",
    "match_status",
    "source_url",
]
show_cols = [c for c in cols if c in f.columns]
st.dataframe(f[show_cols], use_container_width=True)

st.download_button(
    "필터 결과 CSV 다운로드",
    f.to_csv(index=False).encode("utf-8-sig"),
    "auction_dashboard_filtered.csv",
    "text/csv",
)

st.caption(
    "※ 루트의 sample_onbid.csv 하나로도 동작합니다. "
    "실무 적용 시 컬럼 표준화 및 주소 매칭/지표 계산을 강화하세요."
)
