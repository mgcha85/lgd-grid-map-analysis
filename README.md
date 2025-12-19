# 패널 Grid Map 분석 및 Gap 제거 도구

이 프로젝트는 제조 패널 데이터에서 패널 간의 Gap을 분석하고 제거하며, 패널 영역 밖의 이상치(Outlier) 데이터를 필터링하는 도구입니다. Polars 라이브러리를 사용하여 대용량 데이터에서도 효율적으로 작동하도록 설계되었습니다.

## 주요 기능 (Features)

1.  **Mock Data 생성**: 테스트를 위한 가상의 패널 배치 및 불량(Defect) 데이터를 생성합니다.
2.  **Outlier 필터링**: 패널의 사각 영역(Bounding Box)에 포함되지 않는 데이터를 제거합니다.
3.  **Gap 탐지 및 제거**: 패널 사이의 빈 공간(Gap)을 자동으로 계산하고, 좌표를 Shift하여 Gap을 제거합니다.
4.  **시각화**: 처리 전과 후의 데이터를 비교하는 Scatter Plot을 생성합니다.

## 설치 방법 (Installation)

```bash
pip install -r requirements.txt
```

주요 의존성:
- `polars`
- `numpy`
- `matplotlib`
- `pyarrow`

## 사용법 (Usage)

### 1. 데이터 생성 (Mock Data)
테스트용 데이터를 생성하려면 아래 스크립트를 실행하세요. `panels.parquet`와 `defects.parquet`가 생성됩니다.
```bash
python generate_mock_data.py
```

### 2. Gap 제거 검증 (Verification)
전체 로직이 정상 작동하는지 확인하려면 검증 스크립트를 실행하세요.
```bash
python verify_gaps.py
```

### 3. 시각화 (Visualization)
Gap 제거 전/후의 결과를 시각적으로 확인하려면 아래 명령어를 실행하세요. `gap_analysis_visualization.png` 파일이 저장됩니다.
```bash
python visualize_gaps.py
```

### 4. 라이브러리 사용 예시 (Python)

```python
import polars as pl
from gap_analysis import find_gaps, remove_gaps, filter_valid_points

# 데이터 로드
df_panels = pl.read_parquet("panels.parquet")
df_defects = pl.read_parquet("defects.parquet")

# 1. 이상치 제거 (패널 밖 데이터 삭제)
df_valid_defects = filter_valid_points(df_defects, df_panels)

# 2. Gap 탐지
shift_x, shift_y = find_gaps(df_panels)

# 3. Gap 제거 (데이터 및 패널 좌표 변환)
df_clean_defects = remove_gaps(df_valid_defects, shift_x, shift_y)
df_clean_panels = remove_gaps(df_panels, shift_x, shift_y)
```

## 파일 구조 (File Structure)

- `gap_analysis.py`: 핵심 분석 로직 (Gap 탐지, 제거, 필터링 함수)
- `generate_mock_data.py`: 테스트 데이터 생성 스크립트
- `verify_gaps.py`: 로직 검증 스크립트
- `visualize_gaps.py`: 시각화 스크립트
