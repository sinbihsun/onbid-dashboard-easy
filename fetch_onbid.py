from pathlib import Path
import pandas as pd

def fetch_onbid_sample(token: str, *args, **kwargs) -> pd.DataFrame:
    # 루트에 'sample_onbid.csv'가 있다고 가정 (당신 repo 구조와 일치)
    csv_path = Path(__file__).resolve().parent / "sample_onbid.csv"
    return pd.read_csv(csv_path)
