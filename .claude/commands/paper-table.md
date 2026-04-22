실험 결과를 논문용 LaTeX 테이블로 변환하라.

## 1. 데이터 소스 확인

인자가 주어지면 해당 데이터를 사용하고, 없으면 사용 가능한 평가 결과 목록을 보여주고 선택을 요청하라.

데이터를 찾을 수 있는 위치:
- experiments/ 또는 40_experiments/ 하위 eval 결과
- phase JSON의 completed eval step summary
- compare 결과 문서

## 2. 테이블 유형 확인

사용자에게 어떤 테이블을 원하는지 물어봐라:

- **A. 모델 비교표**: 전체 모델 성능 비교 (Table 1 형태)
- **B. Ablation 테이블**: 특정 component의 효과 분석 (baseline vs +component)
- **C. 세부 항목별 테이블**: landmark별, class별 등 세부 분석
- **D. Clinical metrics 테이블**: 도메인 특화 임상 메트릭

## 3. LaTeX 생성 규칙

- `booktabs` 패키지 사용 (`\toprule`, `\midrule`, `\bottomrule`)
- 최고 성능 값은 `\textbf{bold}` 처리
- N-fold: mean $\pm$ std 형식
- 소수점: 주요 메트릭 2자리, 비율 메트릭 1자리
- `\caption`, `\label` 포함
- 표 너비가 넓으면 `\resizebox{\textwidth}{!}{...}` 사용

## 4. 출력

- LaTeX 코드를 화면에 출력
- 사용자에게 저장 위치를 물어봐라
