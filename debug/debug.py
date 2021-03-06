import os,sys,inspect
from pathlib import Path, PurePath

TEXT_COLOR_MAGENTA="\033[35;1m"
TEXT_COLOR_DEFAULT="\033[0m"
TEXT_COLOR_YELLOW="\033[33m"
TEXT_COLOR_YELLOW_BOLD="\033[33;1m"
TEXT_COLOR_BG_Y_FG_M="\033[35;1;43;1m"

def get_calling_script():
    return inspect.stack()[1][1]

def dlog(msg, debug_level=1, color=TEXT_COLOR_MAGENTA, addline=False):
    msg = str(msg)
    def _get_calling_script():
        path_string = inspect.stack()[2][1]
        parts = PurePath(path_string).parts
        if len(parts) > 2:
            path_string='/'.join(parts[-2:])
        else:
            path_string='/'.join(parts)
        # home_path_string = str(Path.home())
        # return path_string.replace(home_path_string, "")
        return path_string

    def _get_calling_script_function():
        return inspect.stack()[2][3]

    def _get_calling_script_lineno():
        return inspect.stack()[2][2]


    _DEBUGLEVEL = int(os.environ['PYTHONDEBUGLEVEL']) if 'PYTHONDEBUGLEVEL' in os.environ else 0

    if debug_level <= _DEBUGLEVEL:
        if addline:
            print("\n")
        print(f"{TEXT_COLOR_YELLOW_BOLD}[{_get_calling_script()}::{_get_calling_script_function()}:{_get_calling_script_lineno()}]{TEXT_COLOR_DEFAULT}")
        # print(f"\n{TEXT_COLOR_BG_Y_FG_M}[{_get_calling_script()}::{_get_calling_script_function()}:{_get_calling_script_lineno()}]{TEXT_COLOR_DEFAULT}")
        for line in msg.splitlines():
            print(f">{color}{line}{TEXT_COLOR_DEFAULT}", file=sys.stderr)
        # print(f"\n[model.py] {utils.TEXT_COLOR_MAGENTA}{msg}{utils.TEXT_COLOR_DEFAULT}\n", file=sys.stderr)
