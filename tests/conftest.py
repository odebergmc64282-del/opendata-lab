"""让 tests 目录在未做 editable 安装时也能 import opendata（本地开发用）。"""
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
