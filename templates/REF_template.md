---
id: REF-<Name>
title: <논문 제목>
authors: <저자>
venue: <학회/저널 이름 + 연도>
year: <YYYY>
url: <DOI 또는 arxiv URL>
source_verified: false   # 원본 논문 읽었으면 true. false면 본문 상단에 경고 표시 필수
related_rqs: [RQ-XXX]
---

# REF-<Name>: <논문 제목>

<!-- source_verified: false 인 경우 아래 경고 유지 -->
> **경고: 출처 미검증.** 이 노트는 2차 자료에 기반하며 부정확할 수 있습니다. 원본 논문과 대조 검증이 필요합니다.

## 1. 한 줄 요약
<이 논문의 핵심 기여 한 문장>

## 2. 문제 및 동기
- **해결하려는 문제**:
- **기존 방법의 한계**:
- **저자의 접근 방식 요지**:

## 3. 방법
### 아키텍처
<구조 요약, 필요 시 다이어그램 설명>

### 학습 설정
- Loss:
- Optimizer:
- LR schedule:
- Augmentation:
- Batch size:
- Epochs:
- Precision:

### 데이터셋
- Train / Val / Test split:
- 전처리:

## 4. 결과
| Metric | 저자 보고값 | 재현 가능성 메모 |
|--------|-----------|----------------|
| | | |

## 5. 우리 연구와의 관련성
- **사용 용도**: Baseline / 비교 대상 / 아이디어 차용 / 배경 문헌
- **우리 환경과의 차이**: <데이터, 해상도, domain 차이 등>
- **주의할 점**: <재현 시 함정, 저자 코드의 미스매치 등>

## 6. 재현 자료
- 공식 코드: <URL>
- 라이선스: <MIT / Apache / CC-BY / 비공개 등>
- 우리 저장소 반영 경로: `src/models/<name>.py` (baseline 구현 시)

## 7. Questions & Open Issues
- <읽으면서 생긴 의문>
- <저자가 명시하지 않은 구현 디테일>

## 8. 변경 이력
| 날짜 | 내용 |
|------|------|
| <YYYY-MM-DD> | v1.0 — draft (source_verified: false) |
