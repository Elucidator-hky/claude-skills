#!/usr/bin/env zsh
# gsearch —— Google 搜索 / 地图商户（Serper API）
# Usage:               gsearch.sh <query>              # 网页搜索，默认 10 条
#                      gsearch.sh -k 20 <query>        # 多结果 (1-100)
#                      gsearch.sh -m <query>           # 地图商户：店名/地址/评分/类别/电话/官网
#                      gsearch.sh -j <query>           # 原始 JSON
#
# 依赖：python3, curl, 环境变量 SERPER_API_KEY
# 与 osearch/bsearch 互补：那两个查中文，gsearch 查英文与海外公司
# 注意：serper.dev 在国外，国内网络要设 SEARCH_PROXY=http://127.0.0.1:<端口> 走本地代理

SCRIPT_DIR=${0:A:h}

gsearch() {
    emulate -L zsh
    local count=10 mode="search" raw=0
    while [[ "$1" == -* ]]; do
        case "$1" in
            -k|--count) count="$2"; shift 2 ;;
            -m|--maps|--places) mode="places"; shift ;;
            -n|--news) mode="news"; shift ;;
            -a|--scholar) mode="scholar"; shift ;;
            -j|--json) raw=1; shift ;;
            -h|--help)
                echo "Usage: gsearch [-k N] [-m|-n|-a] [-j] <query>"
                echo "  -k N   返回 N 条结果(1-100)，默认 10"
                echo "  -m     地图商户模式（判客户有无实体店用这个）"
                echo "  -n     新闻模式（海外时事，带来源和时间）"
                echo "  -a     学术模式（Google Scholar，带被引数和 PDF 链接）"
                echo "  -j     输出原始 JSON"
                return 0 ;;
            *) echo "未知参数: $1" >&2; return 2 ;;
        esac
    done
    if [[ -z "$SERPER_API_KEY" ]]; then
        echo "ERROR: SERPER_API_KEY 未设置" >&2
        return 1
    fi
    if [[ $# -eq 0 ]]; then
        echo "Usage: gsearch [-k N] [-m] [-j] <query>" >&2
        return 2
    fi
    local query="$*" body resp
    body=$(python3 -c "import json,sys; print(json.dumps({'q':sys.argv[1],'num':int(sys.argv[2])}))" "$query" "$count")
    local -a proxy
    [[ -n "$SEARCH_PROXY" ]] && proxy=(--proxy "$SEARCH_PROXY")
    resp=$(curl -sS --max-time 40 "${proxy[@]}" -X POST \
        "https://google.serper.dev/$mode" \
        -H "X-API-KEY: $SERPER_API_KEY" \
        -H 'Content-Type: application/json' \
        -d "$body")
    if (( raw )); then
        print -r -- "$resp" | python3 -m json.tool 2>/dev/null || print -r -- "$resp"
        return 0
    fi
    local formatted
    formatted=$(print -r -- "$resp" | python3 "$SCRIPT_DIR/serper_format.py" "$mode" "$count")
    print -r -- "$formatted"
}

gsearch "$@"
