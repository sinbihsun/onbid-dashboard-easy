# 공매 진행현황 대시보드 (온비드 기반) 

이 프로젝트는 **공공데이터포털의 온비드 공매정보**를 가정한 **샘플 데이터**로
웹 대시보드를 만들어 보는 미니 프로젝트의 쉬운 버전입니다.

> 처음엔 제공된 `data/sample_onbid.csv`로 실행하고,  
> 시간이 남으면 `src/fetch_onbid.py`의 가이드를 따라 실제 API 연동으로 확장하세요.

---

## 빠른 시작

```bash
# 1) 가상환경(선택)
python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)

# 2) 라이브러리 설치
pip install -r requirements.txt

# 3) 대시보드 실행
streamlit run app.py
```

브라우저에서 자동으로 열리지 않으면 주소창에 `http://localhost:8501`를 입력하세요.

---

## 폴더 구조

```
onbid_dashboard_easy/
├─ app.py                 # Streamlit 대시보드
├─ requirements.txt
├─ README.md
├─ data/
│  └─ sample_onbid.csv    # 샘플 데이터
└─ src/
   └─ fetch_onbid.py      # (선택) 온비드 API 연동 가이드
```

---

## 확장 아이디어

- (쉬움) 기간/지역/진행상태 필터 추가
- (중간) 주간/월간 추이 분석 추가
- (중간) 낙찰가율(최저가 대비 낙찰가) 계산/시각화
- (도전) 실제 온비드 Open API 연동 (키 발급 필요)
