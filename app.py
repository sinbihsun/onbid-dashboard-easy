import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="🏦 온비드 공매 대시보드 (담당자 필터)", layout="wide")

# -----------------------------
# 1) 로더: 다양한 파일명/위치를 탐색
# -----------------------------
@st.cache_data(show_spinner=False)
def load_df():
    here = Path(__file__).resolve().parent
    cwd  = Path.cwd()

    # 가능한 파일 후보 (당신의 리포 구조에 맞춰 sample_onbid.csv가 최우선)
    candidate_files = [
        here / "sample_onbid.csv",
        cwd / "sample_onbid.csv",
        here / "data" / "sample_onbid.csv",
        here / "data" / "cases_enriched_sample.csv",
        here / "data" / "internal_export_sample.csv",  # 있으면 단일 파일로 간주
    ]

    looked = []
    for p in candidate_files:
        looked.append(str(p))
        if p.exists():
            return pd.read_csv(p)

    # 못 찾으면 업로드 유도
    st.error(
        "데이터 CSV 파일을 찾지 못했습니다.\n"
        "다음 경로들에서 찾았습니다:\n- " + "\n- ".join(looked) +
        "\n\n리포 루트에 sample_onbid.csv를 두거나, 아래에서 CSV를 업로드하세요."
    )
    uploaded = st.file_uploader("CSV 업로드", type=["csv"])
    if uploaded is not None:
        return pd.read_csv(uploaded)
    st.stop()

# -----------------------------------
# 2) 전처리: 컬럼이 부족해도 안전하게 채우기
# -----------------------------------
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 필요한 대표 컬럼들(없으면 기본값 생성)
    if "case_id" not in df.columns:
        df["case_id"] = [f"C{i:04d}" for i in range(1, len(df)+1)]
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
    if "amount_total" not in df.columns:
        # 금액 관련 컬럼이 있으면 합쳐서 추정
        cand = [c for c in df.columns if "amount" in c or "금액" in c]
        if cand:
            df["amount_total"] = df[cand].select_dtypes("number").sum(axis=1)
        else:
            df["amount_total"] = 0

    # 공매 관련 값
    if "appraisal_price" not in df.columns:
        df["appraisal_price"] = pd.NA
    if "min_bid_price" not in df.columns:
        df["min_bid_price"] = pd.NA
    if "bid_end" not in df.columns:
        df["bid_end"] = pd.NA
    if "source_url" not in df.columns:
        df["source_url"] = ""

    # 타입/파생
    today = pd.Timestamp(datetime.today().date())
    df["delinquent_since"] = pd.to_datetime(df.get("delinquent_since"), errors="coerce")
    df["days_delinquent"] = (today - df["delinquent_since"]).dt.days

    df["appraisal_price"] = pd.to_numeric(df["appraisal_price"], errors="coerce")
    df["min_bid_price"]   = pd.to_numeric(df["min_bid_price"], errors="coerce")
    df["min_ratio"] = (df["min_bid_price"] / df["appraisal_price"]).round(4)

    df["bid_end"] = pd.to_datetime(df["bid_end"], errors="coerce")
    df["due_days"] = (df["bid_end"] - today).dt.days

    # 간이 우선순위 (금액 기준)
    try:
        q = pd.qcut(df["amount_total"].fillna(0), 3, labels=["C","B","A"])
        df["priority_tier"] = q
    except Exception:
        df["priority_tier"] = "B"

    # 매칭 여부가 없으면 기본 "unlinked"
    if "match_status" not in df.columns:
        df["match_status"] = "unlinked"

    return df

# 데이터 로드 & 정리
raw = load_df()
df = ensure_columns(raw)

# -----------------------------------
# 3) 사이드바 필터 (A 방식: 담당자)
# -----------------------------------
st.title("🏦 온비드 공매 대시보드 (담당자 필터)")

st.sidebar.header("필터")
my_name = st.sidebar.text_input("내 이름(담당자)", value="", help="예: 김주무 (부분 입력 가능)")
only_mine = st.sidebar.checkbox("내가 관리하는 케이스만 보기", value=True)

stages = sorted(df["stage"].dropna().unique().tolist())
tiers  = ["A","B","C"]
sel_stages = st.sidebar.multiselect("진행단계", stages)
sel_tiers  = st.sidebar.multiselect("우선순위", tiers)
due_in     = st.sidebar.slider("공매 마감 D-일 이내", 0, 60, 7)

f = df.copy()
if only_mine and my_name.strip():
    patt = my_name.strip()
    f = f[f["officer"].astype(str).str.contains(patt, case=False, na=False)]
if sel_stages:
    f = f[f["stage"].isin(sel_stages)]
if sel_tiers:
    f = f[f["priority_tier"].isin(sel_tiers)]
f = f[(f["due_days"] <= due_in) | f["due_days"].isna()]

# -----------------------------------
# 4) KPI + 테이블
# -----------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("총 체납액(만원)", int(f["amount_total"].fillna(0).sum()/10000) if len(f) else 0)
c2.metric("공매 연계 건수", int((f["match_status"]=="linked").sum()) if len(f) else 0)
c3.metric("A등급 수", int((f["priority_tier"]=="A").sum()) if len(f) else 0)

st.markdown("### 결과 목록")
cols = [
    "case_id","name_masked","officer","region","district","stage",
    "amount_total","min_ratio","bid_end","priority_tier","match_status","source_url"
]
show_cols = [c for c in cols if c in f.columns]
st.dataframe(f[show_cols], use_container_width=True)

st.download_button(
    "필터 결과 CSV 다운로드",
    f.to_csv(index=False).encode("utf-8-sig"),
    "auction_dashboard_filtered.csv",
    "text/csv"
)

st.caption("※ 현재는 루트의 sample_onbid.csv 하나만으로 동작합니다. 실무 적용 시 컬럼명을 표준화하고 주소 매칭/지표 계산을 강화하세요.")
