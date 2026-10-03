#!/usr/bin/env zsh
# 博查 Bocha 中文搜索 —— 比 osearch 覆盖更全（公众号 / 知乎 / 全网）
# Usage:               bsearch.sh <query>                 # 默认 count=10, 不限时间
#                      bsearch.sh -k 20 <query>           # 多结果(1-50)
#                      bsearch.sh -f oneWeek <query>      # 限时间: noLimit/oneYear/oneMonth/oneWeek/oneDay
#                      bsearch.sh -j <query>              # 原始 JSON
#
# 依赖：python3, curl, 环境变量 BOCHA_API_KEY
# 与 osearch（阿里云 OpenSearch）互补：osearch 偏权威站点，bsearch 全网覆盖更广

SCRIPT_DIR=${0:A:h}

bsearch() {
    emulate -L zsh
    local count=10 freshness="noLimit" raw=0
    while [[ "$1" == -* ]]; do
        case "$1" in
            -k|--count) count="$2"; shift 2 ;;
            -f|--freshness) freshness="$2"; shift 2 ;;
            -j|--json) raw=1; shift ;;
            -h|--help)
                echo "Usage: bsearch [-k N] [-f noLimit|oneYear|oneMonth|oneWeek|oneDay] [-j] <query>"
                echo "  -k N      返回 N 条结果(1-50)，默认 10"
                echo "  -f RANGE  时间范围，默认 noLimit"
                echo "  -j        输出原始 JSON"
                return 0 ;;
            *) echo "未知参数: $1" >&2; return 2 ;;
        esac
    done
    if [[ -z "$BOCHA_API_KEY" ]]; then
        echo "ERROR: BOCHA_API_KEY 未设置" >&2
        return 1
    fi
    if [[ $# -eq 0 ]]; then
        echo "Usage: bsearch [-k N] [-f RANGE] [-j] <query>" >&2
        return 2
    fi
    local query="$*" body resp
    body=$(python3 -c "import json,sys; print(json.dumps({'query':sys.argv[1],'summary':True,'freshness':sys.argv[2],'count':int(sys.argv[3])}))" "$query" "$freshness" "$count")
    resp=$(curl -sS --max-time 40 --noproxy 'bochaai.com' -X POST \
        'https://api.bochaai.com/v1/web-search' \
        -H "Authorization: Bearer $BOCHA_API_KEY" \
        -H 'Content-Type: application/json' \
        -d "$body")
    if (( raw )); then
        print -r -- "$resp" | python3 -m json.tool 2>/dev/null || print -r -- "$resp"
        return 0
    fi
    local formatted
    formatted=$(print -r -- "$resp" | python3 "$SCRIPT_DIR/bocha_format.py")
    print -r -- "$formatted"
}

bsearch "$@"
