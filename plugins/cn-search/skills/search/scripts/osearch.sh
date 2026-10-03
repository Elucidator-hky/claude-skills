#!/usr/bin/env zsh
# 阿里云 OpenSearch AI 搜索开放平台 — 联网搜索 API
# Usage:               osearch.sh <query>              # 默认 top_k=5, snippet
#                      osearch.sh -k 10 <query>        # 多结果
#                      osearch.sh -s <query>           # content_type=summary（大模型摘要）
#                      osearch.sh -j <query>           # 原始 JSON
#
# 依赖：python3, curl, 环境变量 ALIYUN_OPENSEARCH_API_KEY + ALIYUN_OPENSEARCH_ENDPOINT
#       ENDPOINT 是阿里云 AI 搜索开放平台控制台给的公网 API 地址，形如 https://xxx.platform-cn-shanghai.opensearch.aliyuncs.com
# 优于 qsearch（千问）：返回真实 URL，无幻觉

SCRIPT_DIR=${0:A:h}

osearch() {
    emulate -L zsh
    local top_k=5
    local content_type="snippet"
    local raw=0
    while [[ "$1" == -* ]]; do
        case "$1" in
            -k|--top) top_k="$2"; shift 2 ;;
            -j|--json) raw=1; shift ;;
            -s|--summary) content_type="summary"; shift ;;
            -h|--help)
                echo "Usage: osearch [-k N] [-j] [-s] <query>"
                echo "  -k N      返回 N 条结果，默认 5"
                echo "  -j        输出原始 JSON"
                echo "  -s        content_type=summary（大模型摘要，慢但更整理）"
                return 0 ;;
            *) echo "未知参数: $1" >&2; return 2 ;;
        esac
    done
    if [[ -z "$ALIYUN_OPENSEARCH_API_KEY" ]]; then
        echo "ERROR: ALIYUN_OPENSEARCH_API_KEY 未设置" >&2
        return 1
    fi
    if [[ -z "$ALIYUN_OPENSEARCH_ENDPOINT" ]]; then
        echo "ERROR: ALIYUN_OPENSEARCH_ENDPOINT 未设置" >&2
        return 1
    fi
    if [[ $# -eq 0 ]]; then
        echo "Usage: osearch [-k N] [-j] [-s] <query>" >&2
        return 2
    fi
    local query="$*"
    local body
    body=$(python3 -c "import json,sys; print(json.dumps({'query':sys.argv[1],'top_k':int(sys.argv[2]),'content_type':sys.argv[3],'query_rewrite':True}))" "$query" "$top_k" "$content_type")
    local resp
    resp=$(curl -sS --max-time 60 --noproxy 'aliyuncs.com,aliyun.com' -X POST \
        "${ALIYUN_OPENSEARCH_ENDPOINT%/}/v3/openapi/workspaces/default/web-search/ops-web-search-001" \
        -H "Authorization: Bearer $ALIYUN_OPENSEARCH_API_KEY" \
        -H 'Content-Type: application/json' \
        -d "$body")
    if (( raw )); then
        print -r -- "$resp" | python3 -m json.tool 2>/dev/null || print -r -- "$resp"
        return 0
    fi
    local formatted
    formatted=$(print -r -- "$resp" | python3 "$SCRIPT_DIR/opensearch_format.py")
    print -r -- "$formatted"
}

osearch "$@"
