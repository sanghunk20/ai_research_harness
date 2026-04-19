# ID 체계

| 유형 | 형식 | 예시 | 위치 |
|------|--------|---------|----------|
| 개념 | `CON-XXX` | `CON-001` | `notes/concepts/` |
| 연구 질문 | `RQ-XXX` | `RQ-001` | `notes/research_questions/` |
| 실험 | `EXP-YYYYMMDD-XX` | `EXP-20260307-01` | `experiments/logs/` |
| 결정 | `DEC-XXX` | `DEC-001` | `notes/decisions/` |
| 참고문헌 | `REF-[Name]` | `REF-ResNet` | `notes/references/` |
| 프로젝트 | `PROJ-XXX` | `PROJ-001` | `projects/` |

- ID는 한 번 부여되면 **변경 불가**
- 노트를 연결할 때 상대 마크다운 링크를 사용: `[RQ-001](../notes/research_questions/RQ-001.md)`

# 폴더별 기대사항

| 폴더 | 기대사항 |
|--------|-------------|
| `notes/thinking/` | 정리하지 마세요. 혼란, 가정, 열린 질문을 강조 |
| `notes/concepts/` 이후 | 더 높은 명확성 기준. 설명과 구조 정제 |
| `experiments/` | 학습 및 inference 결과 저장 |
| `src/` | 코딩 컨벤션 준수 |
| `data/` | **연구자가 명시적으로 요청할 때만 수정** |
| `data_backup/` | **어떤 상황에서도 절대 수정하지 않음** |
