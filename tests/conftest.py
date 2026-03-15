"""
tests/conftest.py
-----------------
确保项目根目录（main.py 所在目录）在 sys.path 中，
让 `from main import app` 在任意工作目录下都能正常导入。
"""
import sys
import os

# 把 backend/ 根目录插入 sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
