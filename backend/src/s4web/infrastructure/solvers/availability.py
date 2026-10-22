"""S4 を読み込めるかの確認。

s4_solver は先頭で S4 を import するため、S4 がない環境では読み込んだ時点で失敗する。
起動時の確認にはこのモジュールを使い、s4_solver 自体は読み込まない。
"""

import importlib


def ensure_solver_available() -> None:
    """S4 を読み込めるかを確かめる。読み込めなければ RuntimeError。"""
    try:
        importlib.import_module("S4")
    except ImportError as e:
        raise RuntimeError("S4 を読み込めません") from e
