# Source this helper in Bash or Zsh: source /path/to/opsfeast/tools/activate.sh
# It activates the checkout's existing .venv without changing the working directory.
if [ -n "${ZSH_VERSION:-}" ] && [ -n "${ZSH_EVAL_CONTEXT:-}" ]; then
    case $ZSH_EVAL_CONTEXT in
        *:file) eval '_opsfeast_activate_file=${(%):-%x}' ;;
        *) printf '%s\n' 'Use "source tools/activate.sh" in Bash or Zsh.' >&2; exit 1 ;;
    esac
elif [ -n "${BASH_VERSION:-}" ]; then
    if [ "${BASH_SOURCE[0]}" = "$0" ]; then
        printf '%s\n' 'Use "source tools/activate.sh" in Bash or Zsh.' >&2
        exit 1
    fi
    _opsfeast_activate_file=${BASH_SOURCE[0]}
else
    printf '%s\n' 'Use "source tools/activate.sh" in Bash or Zsh; use the interpreter directly in other shells.' >&2
    return 1 2>/dev/null || exit 1
fi
_opsfeast_activate_root=$(CDPATH= builtin cd -- "$(command dirname -- "$_opsfeast_activate_file")/.." >/dev/null && builtin pwd -P)
if [ -z "$_opsfeast_activate_root" ] || [ ! -f "$_opsfeast_activate_root/.venv/bin/activate" ]; then
    printf '%s\n' 'No .venv/bin/activate found in this checkout. Reuse your selected interpreter or authorize environment setup first.' >&2
    printf 'Expected activation file: %s/.venv/bin/activate\n' "$_opsfeast_activate_root" >&2
    unset _opsfeast_activate_file _opsfeast_activate_root
    return 1
fi
. "$_opsfeast_activate_root/.venv/bin/activate"
_opsfeast_activate_status=$?
if [ "$_opsfeast_activate_status" -ne 0 ]; then
    unset _opsfeast_activate_file _opsfeast_activate_root _opsfeast_activate_status
    return 1
fi
export PYTHONDONTWRITEBYTECODE=1
unset _opsfeast_activate_file _opsfeast_activate_root _opsfeast_activate_status
