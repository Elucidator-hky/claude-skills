#!/usr/bin/env zsh
# ghsearch —— GitHub 搜索（仓库 / 代码 / issue / PR），底层是已登录的 gh CLI
# Usage:               ghsearch.sh <query>              # 搜仓库，默认 10 条
#                      ghsearch.sh -c <query>           # 搜代码（找具体实现怎么写）
#                      ghsearch.sh -i <query>           # 搜 issue（找报错怎么解）
#                      ghsearch.sh -p <query>           # 搜 PR
#                      ghsearch.sh -k 20 <query>        # 条数 (1-100)
#                      ghsearch.sh -l python <query>    # 限语言
#                      ghsearch.sh -s <query>           # 按 star 排序（默认按相关度）
#                      ghsearch.sh -j <query>           # 原始 JSON
#
# 依赖：gh（已 brew 安装并登录），python3
# 找开源实现 / 报错解法用这个，比 WebSearch 直达

SCRIPT_DIR=${0:A:h}

ghsearch() {
    emulate -L zsh
    local count=10 mode="repos" raw=0 lang="" sort=""
    while [[ "$1" == -* ]]; do
        case "$1" in
            -k|--limit) count="$2"; shift 2 ;;
            -l|--language) lang="$2"; shift 2 ;;
            -c|--code) mode="code"; shift ;;
            -i|--issues) mode="issues"; shift ;;
            -p|--prs) mode="prs"; shift ;;
            -s|--stars) sort="stars"; shift ;;
            -j|--json) raw=1; shift ;;
            -h|--help)
                echo "Usage: ghsearch [-c|-i|-p] [-k N] [-l LANG] [-s] [-j] <query>"
                echo "  (默认)  搜仓库"
                echo "  -c      搜代码（找具体实现怎么写）"
                echo "  -i      搜 issue（找报错怎么解）"
                echo "  -p      搜 PR"
                echo "  -k N    返回 N 条 (1-100)，默认 10"
                echo "  -l LANG 限语言，如 python / go / rust"
                echo "  -s      按 star 排序（仅 repos 有效）"
                echo "  -j      输出原始 JSON"
                return 0 ;;
            *) echo "未知参数: $1" >&2; return 2 ;;
        esac
    done
    if ! command -v gh >/dev/null 2>&1; then
        echo "ERROR: 未安装 gh（brew install gh）" >&2
        return 1
    fi
    if [[ $# -eq 0 ]]; then
        echo "Usage: ghsearch [-c|-i|-p] [-k N] [-l LANG] [-s] [-j] <query>" >&2
        return 2
    fi

    local fields
    case "$mode" in
        repos)  fields="fullName,description,stargazersCount,updatedAt,language,url,isArchived" ;;
        code)   fields="path,repository,url,textMatches" ;;
        *)      fields="title,repository,state,createdAt,url,number,labels" ;;
    esac

    local -a args
    args=(search "$mode" "$@" --limit "$count" --json "$fields")
    [[ -n "$lang" ]] && args+=(--language "$lang")
    [[ -n "$sort" && "$mode" == "repos" ]] && args+=(--sort "$sort")

    local resp
    # 用 print -r 而非 echo：zsh 的 echo 会解释 \n \t 转义，破坏 JSON 里的代码片段
    resp=$(gh "${args[@]}" 2>&1) || { print -r -- "$resp" >&2; return 1; }

    if (( raw )); then
        print -r -- "$resp" | python3 -m json.tool 2>/dev/null || print -r -- "$resp"
        return 0
    fi
    local formatted
    formatted=$(print -r -- "$resp" | python3 "$SCRIPT_DIR/gh_format.py" "$mode")
    print -r -- "$formatted"
}

ghsearch "$@"
