import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from dateutil.parser import parse
from fetch_onbid import fetch_onbid_sample  # ← 루트의 fetch_onbid.py에서 임포트

st.set_page_config(page_title="공매 진행현황 대시보드", layout="wide")

st.title("📊 공매 진행현황 대시보드")
st.caption("샘플 데이터를 사용합니다. 실제 API 연동은 fetch_onbid.py를 참고하세요.")

@st.cache_data
def load_data():
    df = fetch_onbid_sample(token="SAMPLE_TOKEN")
    for col in ["start_date", "end_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

df = load_data()

st.sidebar.header("필터")
regions = ["전체"] + sorted(df["region"].dropna().unique().tolist())
region_sel = st.sidebar.selectbox("지역", regions)

types = ["전체"] + sorted(df["auction_type"].dropna().unique().tolist())
type_sel = st.sidebar.selectbox("공매종류", types)

statuses = ["전체"] + sorted(df["status"].dropna().unique().tolist())
status_sel = st.sidebar.selectbox("진행상태", statuses)

min_date = pd.to_datetime(df["start_date"].min())
max_date = pd.to_datetime(df["end_date"].max())
if pd.isna(min_date) or pd.isna(max_date):
    min_date = pd.to_datetime("2025-01-01")
    max_date = pd.to_datetime(datetime.today().date())
date_range = st.sidebar.date_input("기간 (시작/종료)", value=(min_date.date(), max_date.date()))

filtered = df.copy()
if region_sel != "전체":
    filtered = filtered[filtered["region"] == region_sel]
if type_sel != "전체":
    filtered = filtered[filtered["auction_type"] == type_sel]
if status_sel != "전체":
    filtered = filtered[filtered["status"] == status_sel]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered = filtered[(filtered["start_date"] >= start_d) & (filtered["end_date"] <= end_d)]

st.markdown(f"**총 {len(filtered):,}건**이 필터에 해당합니다.")

col1, col2, col3 = st.columns(3)
with col1:
    by_status = filtered["status"].value_counts().reset_index()
    by_status.columns = ["status", "count"]
    fig = px.pie(by_status, names="status", values="count", title="진행상태 비율")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    by_region = (
        filtered.groupby("region").size().reset_index(name="count")
        .sort_values("count", ascending=False).head(10)
    )
    fig2 = px.bar(by_region, x="region", y="count", title="상위 지역별 공매 건수 (Top10)")
    st.plotly_chart(fig2, use_container_width=True)

with col3:
    tmp = filtered.copy()
    tmp["week"] = tmp["start_date"].dt.to_period("W").astype(str)
    by_week = tmp.groupby("week").size().reset_index(name="count")
    fig3 = px.line(by_week, x="week", y="count", markers=True, title="주간 공매 건수 추이")
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("지도 (선택)")
if st.checkbox("지역 분포 지도 보기", value=False):
    map_df = filtered.dropna(subset=["lat", "lon"])[["lat", "lon"]]
    st.map(map_df)

st.subheader("공매 물건 목록")
st.dataframe(
    filtered[
        ["item_id","region","auction_type","status","start_date","end_date","min_price","appraised_price","address"]
    ].sort_values("start_date", ascending=False).reset_index(drop=True),
    use_container_width=True
)
