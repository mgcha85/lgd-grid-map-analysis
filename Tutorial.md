# Grid Map Analysis 튜토리얼

이 문서는 Grid Map Analysis 프로젝트의 전체 과정에 대한 상세한 튜토리얼입니다. 데이터 생성부터 전처리, 분석, 그리고 최종 시각화까지의 단계를 설명합니다.

## 1. 프로젝트 개요 (Overview)

이 프로젝트의 목표는 제조 패널 데이터에서 불량(Defect) 패턴을 분석하고 시각화하는 것입니다. 특히, 물리적으로 떨어져 있는 패널들 사이의 간격(Gap)을 제거하여 논리적으로 연결된 상태에서 불량 밀집 지역(Region)을 탐지하는 것이 핵심입니다.

## 2. 데이터 생성 (Mock Data Generation)

`generate_mock_data.py` 스크립트를 사용하여 분석에 필요한 가상의 데이터를 생성합니다.

*   **패널 (Panels)**: 총 40개의 패널을 8열(Columns) x 5행(Rows) 그리드로 배치합니다.
    *   **좌표계**: 중심점 (0,0)을 기준으로 X: -800~800, Y: -600~600 범위를 가집니다.
    *   **간격 (Gaps)**: 패널 사이에는 물리적인 간격이 존재합니다.
    *   **ID 부여**:
        *   **Columns**: A, B, C, ..., H (왼쪽 -> 오른쪽)
        *   **Rows**: 1, 2, 3, ..., 5 (아래 -> 위)
        *   **Panel Label**: 예) A1, B3, H5
*   **불량 (Defects)**:
    *   **Cluster Defect**: 특정 패널에 밀집된 형태의 불량 (분석 대상).
    *   **Random Noise**: 전체 영역에 무작위로 분포하는 노이즈.
    *   **Outlier**: 패널 영역 밖이나 간격 사이에 존재하는 이상치.

## 3. 데이터 전처리 (Data Processing)

`run_simulation.py`와 `gap_analysis.py`에서 데이터를 로드하고 정제합니다.

1.  **이상치 제거 (Outlier Filtering)**: 패널의 물리적 영역(Bounding Box) 밖에 있는 불량 데이터를 제거합니다.
2.  **간격 제거 (Gap Removal)**:
    *   각 패널 사이의 간격(Gap)을 계산하여 제거합니다.
    *   모든 패널을 밀착시켜 논리적인 하나의 큰 그리드(Cleaned Coordinates)로 변환합니다.
    *   이때, 원본 좌표(`orig_x`, `orig_y`)는 시각화를 위해 보존합니다.

## 4. 그리드 매핑 (Grid Mapping)

`grid_mapping.py`를 통해 각 패널을 더 세밀한 단위인 **Sub-grid**로 나눕니다.

*   **분할**: 각 패널을 3x3의 Sub-grid로 분할합니다.
*   **Sub-grid ID**: `{Panel Label}-{Sub Row}{Sub Col}` 형식 (예: `A1-a1`, `B2-c3`).
    *   Sub Row: 1, 2, 3
    *   Sub Col: a, b, c
*   **Global Index**: 전체 40개 패널을 통합한 거대한 행렬에서의 위치(`global_row`, `global_col`)를 계산합니다. 이는 나중에 영역 탐지(Connected Components)에 사용됩니다.

## 5. 분석 (Analysis)

`analysis_utils.py`와 `run_simulation.py`에서 핵심 분석을 수행합니다.

1.  **Sub-grid 불량 카운팅**:
    *   각 Sub-grid 영역 내에 존재하는 불량의 개수를 셉니다.
2.  **노이즈 제거 (Noise Removal)**:
    *   배경 노이즈(Background Noise)를 추정하여 각 Sub-grid의 불량 수에서 차감합니다.
    *   **Cleaned Count** = Max(0, Raw Count - Estimated Noise)
3.  **영역 탐지 (Region Detection)**:
    *   **Cleaned Count**를 기반으로 분석을 수행합니다. (노이즈가 제거된 "진짜" 불량만 분석)
    *   **Connected Components Analysis (CCA)** 알고리즘을 사용합니다.
    *   **8-connectivity**: 상하좌우뿐만 아니라 **대각선**으로 인접한 Sub-grid도 같은 영역으로 간주합니다.
    *   패널 경계를 넘어서 인접한 경우도 연결된 것으로 판단합니다 (Gap이 제거된 논리적 공간 기준).

## 6. 시각화 (Visualization)

최종 결과는 두 개의 지도로 시각화됩니다 (`final_result.png`).

### 왼쪽: Original Map
*   **좌표계**: 물리적 좌표 (간격 존재).
*   **Heatmap**: **Raw Defect Count** (노이즈 포함)를 붉은색 농도로 표시.
*   **Grid**: 패널(실선)과 Sub-grid(점선) 경계 표시.
*   **Bounding Box**: 파란색 박스로 탐지된 불량 영역 표시.

### 오른쪽: Cleaned Map
*   **좌표계**: 논리적 좌표 (간격 제거, 패널 밀착).
*   **Heatmap**: **Cleaned Defect Count** (노이즈 제거됨)를 붉은색 농도로 표시.
*   **Grid**: 패널과 Sub-grid 경계가 연속적으로 이어짐.
*   **Bounding Box**: 파란색 박스로 탐지된 불량 영역 표시 (Original Map과 동일한 영역).

## 7. 결과 리포트 (Reporting)

`final_report.md`에 분석 결과가 요약됩니다.
*   탐지된 각 영역(Region)의 ID.
*   총 불량 수 (Cleaned).
*   포함된 Sub-grid의 개수 및 목록.
*   평균 불량 밀도.

---
이 튜토리얼을 통해 데이터 생성부터 최종 분석 결과 도출까지의 흐름을 이해할 수 있습니다.
