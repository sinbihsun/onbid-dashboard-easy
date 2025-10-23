import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="🏦 부동산 공매 통합 대시보드", layout="wide")

@st.cache_data
def load():
    from pathlib import Path
    import pandas as pd

    # ✅ app.py가 리포지토리 루트에 있을 때
    base = Path(__file__).resolve().parent / "data"

    internal = pd.read_csv(base / "internal_export_sample.csv")
    auction  = pd.read_csv(base / "auction_list_sample.csv")
    return internal, auction


def street_no(addr: str):
    try:
        return int(str(addr).split("테스트로")[-1].strip())
    except Exception:
        return None

def preprocess(internal, auction):
    # 간이 주소 매칭용 street_no
    internal["street_no"] = internal["address"].apply(street_no)
    auction["street_no"]  = auction["property_address"].apply(street_no)

    merged = pd.merge(
        internal, auction,
        on=["region","district","street_no"],
        how="left", suffixes=("", "_auc")
    )

    # 파생 지표
    today = pd.Timestamp(datetime.today().date())
    merged["delinquent_since"] = pd.to_datetime(merged["delinquent_since"], errors="coerce")
    merged["days_delinquent"] = (today - merged["delinquent_since"]).dt.days
    merged["penalty_ratio"] = (merged["amount_penalty"] / merged["amount_total"]).round(4)

    merged["appraisal_price"] = pd.to_numeric(merged.get("appraisal_price"), errors="coerce")
    merged["min_bid_price"]   = pd.to_numeric(merged.get("min_bid_price"), errors="coerce")
    merged["min_ratio"] = (merged["min_bid_price"] / merged["appraisal_price"]).round(4)

    merged["bid_end"] = pd.to_datetime(merged.get("bid_end"), errors="coerce")
    merged["time_pressure"] = (merged["bid_end"] - today).dt.days
    merged["match_status"] = merged["item_id"].notna().map({True:"linked", False:"unlinked"})

    # 간이 우선순위
    stage_score = {"독촉":0.3,"최고":0.45,"압류":0.7,"공매신청":0.85,"공매진행":1.0}
    asset_score = {"부동산":1.0,"예금":0.8,"차량":0.6,"기타":0.4}
    merged["collectability_proxy"] = merged["stage"].map(stage_score).fillna(0.4) + \
                                     merged["asset_flag"].map(asset_score).fillna(0.3)
    amt_norm = (merged["amount_total"] / merged["amount_total"].max()).fillna(0)
    merged["priority_score"] = (
        0.6*amt_norm
        + 0.3*merged["collectability_proxy"]
        + 0.1*(-merged["time_pressure"].fillna(30).clip(-30,30)/30)
    ).round(4)
    try:
        merged["priority_tier"] = pd.qcut(merged["priority_score"], 3, labels=["C","B","A"])
    except Exception:
        merged["priority_tier"] = "B"

    return merged

# 데이터 로드 & 전처리
internal, auction = load()
df = preprocess(internal.copy(), auction.copy())

# =======================
#     사이드바 필터
# =======================
st.title("🏦 부동산 공매 통합 대시보드 (담당자 필터)")

st.sidebar.header("필터")
# ✅ 담당자 이름 기반 필터
my_name = st.sidebar.text_input("내 이름(담당자)", value="", help="예: 김주무 / '김' 처럼 부분 입력도 가능")
only_mine = st.sidebar.checkbox("내가 관리하는 케이스만 보기", value=True)

stages  = st.sidebar.multiselect("진행단계", sorted(df["stage"].dropna().unique()))
tiers   = st.sidebar.multiselect("우선순위", ["A","B","C"])
due_in  = st.sidebar.slider("공매 마감 D-일 이내", 0, 30, 7)

# 필터 적용
f = df.copy()

# ✅ 담당자 필터 (부분일치, 대소문자 무시)
if only_mine and my_name.strip():
    patt = my_name.strip()
    f = f[f["officer"].astype(str).str.contains(patt, case=False, na=False)]

if stages:
    f = f[f["stage"].isin(stages)]
if tiers:
    f = f[f["priority_tier"].isin(tiers)]

f["due_days"] = (f["bid_end"] - pd.Timestamp.today()).dt.days
f = f[(f["due_days"] <= due_in) | f["due_days"].isna()]

# =======================
#          KPI
# =======================
c1, c2, c3 = st.columns(3)
c1.metric("총 체납액(만원)", int(f["amount_total"].sum()/10000) if len(f) else 0)
c2.metric("공매 연계 건수", int((f["match_status"]=="linked").sum()) if len(f) else 0)
c3.metric("A등급 수", int((f["priority_tier"]=="A").sum()) if len(f) else 0)

# =======================
#        결과 테이블
# =======================
st.markdown("### 결과 목록")
cols = [
    "case_id","name_masked","officer","region","district","stage",
    "amount_total","priority_tier","min_ratio","bid_end","match_status","source_url"
]
show_cols = [c for c in cols if c in f.columns]
st.dataframe(f[show_cols], use_container_width=True)

st.download_button(
    "필터 결과 CSV 다운로드",
    f.to_csv(index=False).encode("utf-8-sig"),
    "auction_dashboard_filtered.csv",
    "text/csv"
)

st.caption("※ 주소 매칭은 데모용 규칙(‘테스트로 + 번지’)입니다. 실무 적용 시 정규화/유사도 매칭을 권장합니다.")
