학습 상태를 확인하라. 아래 절차를 순서대로 수행:

## 1. GPU 사용 현황 (공유 서버 — 다른 사용자 프로세스 확인 필수)

```bash
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "GPU 정보를 가져올 수 없음"
```

각 GPU에서 돌고 있는 프로세스를 확인하라:

```bash
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory,name --format=csv,noheader 2>/dev/null
```

**중요**: 다른 사용자의 프로세스가 GPU를 점유하고 있으면:
- 해당 GPU의 점유 VRAM 양을 표시하라
- 남은 VRAM이 학습에 충분한지 계산하라
- **사용자에게 "다른 프로세스가 GPU를 사용 중입니다. 학습을 시작할까요?"라고 반드시 컨펌을 받아라**

## 2. tmux 세션 확인

```bash
tmux list-sessions 2>/dev/null || echo "활성 tmux 세션 없음"
```

`harness-` 로 시작하는 세션이 학습 관련 세션이다.

## 3. Phase 상태 확인

`projects/phases/index.json`을 읽고 현재 진행 중인 phase 목록을 표시하라.

## 4. 출력 형식

```
=== 학습 상태 ===

GPU 현황:
  GPU 0: H100 80GB | 사용률: 95% | VRAM: 72000/81920 MB
    다른 프로세스: PID 12345 (python) — 70000 MB 사용 중
  GPU 1: H100 80GB | 사용률: 0%  | VRAM: 0/81920 MB (여유)

활성 학습 세션:
  harness-phase-exp1-train (tmux)

Phase 진행 현황:
  [done] phase-exp1: 모델 학습
  [ .. ] phase-exp2: 평가 (60%)
  [    ] phase-exp3: 미시작
```
