연구 계획 변경사항을 영향받는 모든 문서에 반영하라. 인자로 전달된 자연어 설명을 분석해서 어떤 문서를 어떻게 수정할지 먼저 제시하고, 연구자 확인 후 적용하라.

## 실행 절차

### 1. 변경 유형 분류 (인자 파싱)

인자가 없으면: "어떤 계획 변경을 반영할까요? 자연어로 설명해 주세요." 라고 묻고 중단.

변경을 다음 3단계로 분류:

- **경량 변경**: 우선순위 변경, 진행률 업데이트, Task 순서 변경
  - 영향: 활성 PROJ 문서만
- **중간 변경**: Phase 추가/제거, Step 추가/수정, Phase 순서 변경
  - 영향: PROJ 문서 + `projects/phases/index.json` + `projects/phases/<phase-id>/index.json`
- **중대 변경**: RQ 추가/제거/수정, 연구 기여(contribution) 재프레이밍, Phase 병합, 기존 DEC와 충돌하는 결정
  - 영향: 위 전체 + 관련 `notes/concepts/CON-XXX.md` + `notes/research_questions/RQ-XXX.md` + `notes/decisions/DEC-XXX.md` 자동 생성

분류가 모호하면 AskUserQuestion으로 연구자에게 확인.

### 2. 대상 문서 탐색

**PROJ 문서 탐색**: `ls projects/PROJ-*.md` (glob)
- 0개: "PROJ 문서가 없습니다. 먼저 `/setup`을 실행하여 프로젝트 로드맵을 생성해 주세요." 로 중단
- 1개: 자동 선택
- 2개 이상: AskUserQuestion으로 대상 선택

**중간 이상 추가 로드**:
- `projects/phases/index.json`
- 관련 `projects/phases/<phase-id>/index.json`

**중대 추가 로드**:
- 변경 대상 RQ: `notes/research_questions/RQ-*.md`에서 관련 파일
- 관련 CON (**하이브리드 매칭**):
  1. `notes/concepts/CON-*.md`의 frontmatter `related_rqs: [...]`를 읽어 대상 RQ가 포함된 CON을 찾는다
  2. 정확히 1개 매칭 → 자동 선택, Preview에 "자동 매칭: CON-XXX (RQ-YYY 기반)" 로 표시
  3. 0개 또는 2개 이상 매칭 → AskUserQuestion으로 선택 (선택지에 "CON 없이 진행" 포함)
  4. frontmatter에 `related_rqs` 필드가 없는 CON은 매칭 후보에서 제외
- 다음 DEC 번호: `ls notes/decisions/DEC-*.md`에서 최대 번호 +1 (없으면 `DEC-001`)

### 3. 변경 Preview 제시

다음 형식으로 출력:

```
## 변경 유형: <경량/중간/중대>

## 수정 대상 파일 (N개)
- [PROJ-XXX] <수정 섹션 요약>
- [CON-XXX] <수정 섹션 요약> (자동 매칭: RQ-YYY 기반 | 사용자 선택)
- [projects/phases/index.json] <엔트리 추가/수정/삭제>
- [projects/phases/<phase-id>/index.json] <steps 수정 요약>
- ... (해당되는 것만)

## 신규 생성 (중대 변경 시만)
- [DEC-XXX] <제목 초안>
- [projects/phases/<new-phase-id>/index.json] (신규 Phase 시)
- [notes/research_questions/RQ-XXX.md] (신규 RQ 시)

## 변경 이력 엔트리 (자동 생성 예정)
- PROJ-XXX v<N+1>.0 — <요약>
- CON-XXX v<major>.<minor+1> — <요약> (중대 변경 시)
```

각 "수정 섹션 요약"은 before/after 핵심 차이만 한 줄로. 긴 diff는 보여주지 말 것.

### 4. 연구자 확인 (필수)

AskUserQuestion 도구로 물어봐라:

1. "이대로 진행할까요?" — 진행 / 수정 / 취소
2. 미확정 사항 (아래 중 해당되는 것만):
   - 새 Phase ID (예: `phase-ablation`, `phase-extension`)
   - 새 RQ 번호 (기존 RQ 번호는 **절대 변경하지 말 것**, 다음 사용 가능한 번호로만 부여)
   - DEC 제목 (중대 변경 시)
   - **DEC 배경/근거** (중대 변경 시 필수) — 연구자 설명을 그대로 DEC 본문에 넣음

취소 선택 시 어떤 파일도 수정하지 말고 중단.

### 5. 적용

#### 문서 업데이트 원칙
- **ID 불변**: 기존 RQ-XXX, DEC-XXX, CON-XXX, phase-<id> 번호는 절대 변경 금지
- **추가만 허용**: 새 RQ/DEC/CON/Phase는 기존 최대 번호 +1
- **삭제 시**: 문서에서 제거하지 말고 "폐기됨 (YYYY-MM-DD, 이유)" 표시 후 취소선/음영 처리

#### PROJ-XXX 업데이트
1. 진행률 요약 테이블: 해당 RQ/Phase 행 상태/진행률 수정 또는 행 추가
2. Phase별 체크리스트 섹션: 해당 Phase 위치에 항목 추가/수정
3. 주요 리스크 및 이슈: 관련 이슈 추가 또는 해결된 이슈 삭제
4. 변경 이력 테이블 맨 아래에 엔트리 추가:
   ```
   | YYYY-MM-DD | v<N+1>.0 — <변경 내용 요약> |
   ```

#### projects/phases/index.json 업데이트 (execute.py 스키마 준수)

전체 스키마는 `docs/phase_schema.md` 참조. 요약:

- `phases` 배열에 새 엔트리 추가 또는 기존 엔트리 수정
- **필드**:
  - `dir` (필수, unique): phase 디렉토리 이름 (= execute.py 호출 인자). 예 `phase-baseline`
  - `name` (필수): human-readable
  - `rq` (선택, null 허용): 관련 RQ ID — 커맨드 전용 필드, execute.py는 무시
  - `status` (필수): `pending` | `in_progress` | `training` | `completed` | `blocked` | `error`
  - `progress` (선택): 문자열 `"0%"` 형태
  - 타임스탬프 필드(`completed_at`, `failed_at`, `blocked_at`)는 execute.py가 자동 기록 — 직접 쓰지 말 것

#### Phase 신설 시 phase index.json 생성
경로: `projects/phases/<dir>/index.json`

```json
{
  "project": "<PROJECT_NAME>",
  "phase": "<dir>",
  "rq": "<RQ 번호 or null>",
  "status": "pending",
  "steps": []
}
```

**Step 필드 (execute.py 스키마)**:
- `step` (필수, 정수): 0부터 시작, phase 내 unique
- `name` (필수): 예 `config-and-dryrun`
- `type` (필수): `code` | `train` | `eval` | `analyze`
- `status` (필수): `pending` | `completed` | `error` | `blocked` | `training` | `in_progress`
- `summary` / `error_message` / `blocked_reason` (상황별)
- `tmux_session` / `completion_check` (train step 전용)
- 타임스탬프 필드는 execute.py가 자동 기록

Step 추가 시 해당 step의 지시사항을 `projects/phases/<dir>/step<N>.md` 파일에도 작성한다 (execute.py가 이 파일을 읽어 Claude에게 전달).

#### CON-XXX 업데이트 (중대만)
- 해당 섹션 수정 (스토리라인/기여 구조 유지)
- frontmatter `related_rqs`가 바뀌면 함께 업데이트 (추가만 허용, 기존 RQ ID는 유지)
- 변경 이력 테이블에 엔트리 추가 (minor 증가: v1.0 → v1.1)

#### RQ 문서 업데이트 (중대만)
- 새 RQ 추가: `notes/research_questions/RQ-XXX.md` 생성 (다음 사용 가능 번호)
- 폐기: "폐기됨 (YYYY-MM-DD, 이유)" 표시, 파일 삭제 금지

#### DEC 초안 생성 (중대만)
경로: `notes/decisions/DEC-XXX_<snake_case_title>.md`

템플릿:
```markdown
---
id: DEC-XXX
title: <제목>
date: <YYYY-MM-DD>
status: 초안 (연구자 검토 필요)
related_proj: PROJ-XXX
related_con: [CON-XXX]
related_rq: [RQ-XXX]
---

# DEC-XXX: <제목>

## 배경

<Step 4에서 연구자가 입력한 배경/근거를 그대로 기록>

## 결정

<변경 내용 요약 — 자연어 설명을 다듬어서>

## 영향 문서

- PROJ-XXX v<N+1>.0 변경 이력 참조
- CON-XXX v<major>.<minor+1> 변경 이력 참조
- projects/phases/index.json (관련 엔트리)

## 검증 계획

(연구자 수동 보완 필요)

## 변경 이력

| 날짜 | 내용 |
|------|------|
| <YYYY-MM-DD> | v1.0 초안 (자동 생성 by /update-plan) |
```

### 6. 적용 검증

적용 직후 다음을 확인:
1. 수정한 각 파일의 변경 이력 테이블에 새 엔트리가 있는가
2. `projects/phases/index.json`이 유효한 JSON인가
   ```bash
   python -c "import json; json.load(open('projects/phases/index.json'))"
   ```
3. 수정/생성한 각 phase별 `index.json`도 유효한 JSON인가
4. 기존 RQ/DEC/Phase/CON ID가 그대로 보존되어 있는가 (grep으로 변경 전후 ID 개수 비교)

검증 실패 시 연구자에게 즉시 보고하고 rollback 여부 확인 (`git checkout -- <file>` 제안).

### 7. 결과 보고

```
## 수정 완료

**수정된 파일**:
- PROJ-XXX (v<N> → v<N+1>)
- CON-XXX (v<major>.<minor> → v<major>.<minor+1>)
- projects/phases/index.json (phase-<id> 추가)

**생성된 파일**:
- projects/phases/<phase-id>/index.json
- notes/decisions/DEC-XXX_<title>.md
- notes/research_questions/RQ-XXX.md (신규 RQ 시)

**다음 할 일**:
- DEC-XXX 본문 (배경 외 검증 계획) 연구자 검토 및 보완
- Phase <id>의 첫 번째 step을 `/train`으로 시작 가능
```

## 에러 처리

- **존재하지 않는 Phase/RQ 수정 요청**: "지정한 <X>는 존재하지 않습니다. 기존 목록: ..." 로 중단
- **ID 변경 요청** (예: "RQ-004를 RQ-004a로"): "CLAUDE.md ID 불변 규칙에 따라 기존 ID는 변경할 수 없습니다. 폐기 후 신규 RQ 추가로 대체하시겠습니까?" 로 거부/대체 제안
- **JSON 파싱 실패**: 이미 수정한 파일들 rollback 제안 (`git checkout -- <file>`)
- **PROJ 문서 부재**: "`/setup`을 먼저 실행해서 프로젝트 로드맵을 생성해 주세요." 로 중단
- **모호한 요청**: Step 4에서 AskUserQuestion으로 재확인

## 준수 규칙

- `.claude/rules/common/safety_constraints.md` (프로젝트 외부 경로 수정 금지)
- `.claude/rules/common/experiment_lifecycle.md`
- CLAUDE.md의 ID 불변 원칙
- 보고 언어: 한국어, 존댓말
