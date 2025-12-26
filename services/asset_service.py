import os
import random
from typing import Tuple

from domain.type import AssetsConfig, DEFAULT_ASSETS_CONFIG


def _resolve_role_path(dir_path: str, role: str, config: AssetsConfig) -> str | None:
    for name in config.expected_names.get(role, []):
        p = os.path.join(dir_path, name)
        if os.path.isfile(p):
            return p
    return None


def detect_group_paths(
    dir_path: str, config: AssetsConfig = DEFAULT_ASSETS_CONFIG
) -> Tuple[str, str, str] | None:
    """dir_path内で期待される3画像（bg, mid, fg）を検出して返す。
    すべて揃っていない場合はNone。
    """
    bg = _resolve_role_path(dir_path, "bg", config)
    mid = _resolve_role_path(dir_path, "mid", config)
    fg = _resolve_role_path(dir_path, "fg", config)
    if bg and mid and fg:
        return bg, mid, fg
    return None


def get_default_assets_root(config: AssetsConfig = DEFAULT_ASSETS_CONFIG) -> str:
    """プロジェクト直下の既定assetsルートを返す。"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, config.root_dir_name)


def list_available_groups(
    assets_root: str | None = None, config: AssetsConfig = DEFAULT_ASSETS_CONFIG
) -> list[Tuple[str, str, str]]:
    if assets_root is None:
        assets_root = get_default_assets_root(config)
    groups: list[Tuple[str, str, str]] = []
    # サブディレクトリを探索
    try:
        for name in os.listdir(assets_root):
            sub = os.path.join(assets_root, name)
            if os.path.isdir(sub):
                tup = detect_group_paths(sub, config)
                if tup:
                    groups.append(tup)
    except Exception:
        pass
    # ルート直下にも3画像がある場合のフォールバック
    root_tup = detect_group_paths(assets_root, config)
    if root_tup:
        groups.append(root_tup)
    return groups


def pick_random_group(
    assets_root: str | None = None, config: AssetsConfig = DEFAULT_ASSETS_CONFIG
) -> Tuple[str, str, str]:
    groups = list_available_groups(assets_root, config)
    if not groups:
        if assets_root is None:
            assets_root = get_default_assets_root(config)
        raise FileNotFoundError(
            f"assetsルートに有効な画像グループが見つかりません: {assets_root}"
        )
    return random.choice(groups)
