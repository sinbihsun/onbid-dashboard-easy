"""
(선택) 온비드 Open API 연동 가이드 (샘플)

1) 공공데이터포털에서 온비드 공매정보 Open API 키를 발급받습니다.
2) 아래 URL/파라미터를 참고하여 requests.get 으로 JSON을 호출합니다.
3) 응답 JSON을 pandas DataFrame으로 변환하고, app.py가 기대하는 컬럼으로 맞춥니다.

주의: 실제 엔드포인트/파라미터는 최신 문서를 참고하세요.

"""
from typing import Optional
import pandas as pd
import requests
from datetime import datetime, timedelta

def fetch_onbid_sample(token: str,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
    """
    실제 API 호출 대신, 현재는 data/sample_onbid.csv를 읽어서 반환합니다.
    추후 API 연동 시 이 함수를 수정하면 app.py가 자동으로 최신 데이터를 사용합니다.
    """
    return pd.read_csv("data/sample_onbid.csv")

# (참고용) 실제 호출 예시 스케치
def _example_real_call(token: str, page: int = 1) -> dict:
    """
    예시: 실제 온비드 API 호출 스케치 (작동 X)
    """
    url = "https://api.onbid.go.kr/example/endpoint"
    params = {
        "serviceKey": token,
        "pageNo": page,
        "numOfRows": 100,
        "type": "json",
        # "startDate": "20250101",
        # "endDate": "20250201",
    }
    # res = requests.get(url, params=params, timeout=30)
    # res.raise_for_status()
    # return res.json()
    return {"message": "This is a placeholder."}
