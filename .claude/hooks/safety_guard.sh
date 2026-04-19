#!/bin/bash
# Safety guard hook — 프로젝트 외부 경로 및 위험 명령어 차단
#
# PreToolUse hook: Edit, Write, Bash 도구 사용 시 실행
# 환경변수: CLAUDE_TOOL_INPUT (도구 입력 JSON)
#
# CONFIGURATION: Set PROJECT_ROOT to your project's absolute path
PROJECT_ROOT=""  # e.g., "/home/user/my_project"

# If PROJECT_ROOT is not set, try to detect from script location
if [ -z "$PROJECT_ROOT" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# 1. Edit/Write: 프로젝트 외부 경로 차단
if echo "$CLAUDE_TOOL_INPUT" | grep -qE '"file_path"\s*:\s*"' 2>/dev/null; then
    FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | grep -oP '"file_path"\s*:\s*"\K[^"]+')
    if [ -n "$FILE_PATH" ]; then
        case "$FILE_PATH" in
            ${PROJECT_ROOT}/*)
                ;;
            *)
                echo "BLOCKED: 프로젝트 외부 경로 수정 차단됨: $FILE_PATH" >&2
                echo "허용 경로: ${PROJECT_ROOT}/ 내부만 가능합니다." >&2
                exit 2
                ;;
        esac

        case "$FILE_PATH" in
            */data_backup/*)
                echo "BLOCKED: 데이터 백업 디렉토리 수정 차단됨: $FILE_PATH" >&2
                exit 2
                ;;
        esac
    fi
fi

# 2. Bash: 위험 명령어 차단
if echo "$CLAUDE_TOOL_INPUT" | grep -qE '"command"\s*:\s*"' 2>/dev/null; then
    COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | grep -oP '"command"\s*:\s*"\K[^"]+')

    # rm -rf 차단
    if echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive.*--force|-[a-zA-Z]*f[a-zA-Z]*r)\s'; then
        echo "BLOCKED: rm -rf 명령어는 사용할 수 없습니다." >&2
        echo "파일 삭제가 필요하면 연구자에게 컨펌을 요청하세요." >&2
        exit 2
    fi

    # git push --force 차단
    if echo "$COMMAND" | grep -qE 'git\s+push\s+--force'; then
        echo "BLOCKED: git push --force는 사용할 수 없습니다." >&2
        exit 2
    fi

    # git reset --hard 차단
    if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
        echo "BLOCKED: git reset --hard는 사용할 수 없습니다." >&2
        exit 2
    fi
fi

exit 0
