"""
正答率分析スクリプト
各ユーザーの課題モードごとの正答率を集計し、平均正答率を計算する
"""

import os
import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import statistics


def find_result_directories(base_dir: str = ".") -> list[Path]:
    """
    結果ディレクトリ（{username}_{date}形式）を検索

    Args:
        base_dir: 検索するベースディレクトリ

    Returns:
        結果ディレクトリのパスリスト
    """
    base_path = Path(base_dir)
    result_dirs = []

    for item in base_path.iterdir():
        if item.is_dir() and "_" in item.name:
            # {username}_{date}形式のディレクトリを検出
            parts = item.name.split("_")
            if len(parts) >= 2 and parts[-1].isdigit() and len(parts[-1]) == 8:
                result_dirs.append(item)

    return sorted(result_dirs)


def load_correct_from_csv(csv_path: Path) -> dict:
    """
    correct.csvからデータを読み込む

    Args:
        csv_path: CSVファイルのパス

    Returns:
        各タスクの正答数と正答率のディクショナリ
    """
    correct_data = {}

    if not csv_path.exists():
        return correct_data

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 空行をスキップ
                if not row.get("index"):
                    continue

                index = row.get("index", "")
                num = int(row.get("num", 0))

                # 正答率を計算（6問中何問正解したか）
                accuracy = num / 6.0 if num is not None else 0.0

                correct_data[f"task{index}"] = {
                    "correct_count": num,
                    "total_count": 6,
                    "accuracy": accuracy,
                }
    except Exception as e:
        print(f"Warning: Failed to read {csv_path}: {e}")

    return correct_data


def analyze_user_results(user_dir: Path) -> dict:
    """
    1人のユーザーの結果を分析

    Args:
        user_dir: ユーザーの結果ディレクトリ

    Returns:
        課題モードごとの正答率情報
    """
    correct_csv = user_dir / "correct.csv"

    if not correct_csv.exists():
        return {}

    # 正答データを読み込み
    correct_data = load_correct_from_csv(correct_csv)

    return correct_data


def aggregate_all_users(base_dir: str = ".") -> dict:
    """
    全ユーザーの結果を集計

    Args:
        base_dir: ベースディレクトリ

    Returns:
        ユーザーごとおよび全体の統計情報
    """
    result_dirs = find_result_directories(base_dir)

    if not result_dirs:
        print("結果ディレクトリが見つかりませんでした。")
        return {}

    all_results = {}

    # 課題モードごとに全ユーザーのデータを集計
    task_aggregation = defaultdict(lambda: {"accuracies": [], "correct_counts": []})

    for user_dir in result_dirs:
        username = user_dir.name
        print(f"\n分析中: {username}")

        user_stats = analyze_user_results(user_dir)
        all_results[username] = user_stats

        # 全ユーザー集計用にデータを追加
        for task_key, stats in user_stats.items():
            task_aggregation[task_key]["accuracies"].append(stats["accuracy"])
            task_aggregation[task_key]["correct_counts"].append(stats["correct_count"])

    # 全ユーザーの平均を計算
    all_users_stats = {}
    for task_key, data in task_aggregation.items():
        accuracies = data["accuracies"]
        correct_counts = data["correct_counts"]

        all_users_stats[task_key] = {
            "accuracy_mean": statistics.mean(accuracies) if accuracies else None,
            "accuracy_stdev": statistics.stdev(accuracies)
            if len(accuracies) > 1
            else None,
            "correct_count_mean": statistics.mean(correct_counts)
            if correct_counts
            else None,
            "user_count": len(accuracies),
        }

    all_results["__all_users__"] = all_users_stats

    return all_results


def print_results(results: dict):
    """
    結果を見やすく表示

    Args:
        results: 分析結果
    """
    print("\n" + "=" * 80)
    print("課題モード別 正答率の分析結果")
    print("=" * 80)

    # 全ユーザーの集計を表示
    if "__all_users__" in results:
        print("\n【全ユーザーの平均】")
        print("-" * 80)
        all_users = results["__all_users__"]

        for task_key in sorted([k for k in all_users.keys() if k.startswith("task")]):
            stats = all_users[task_key]
            print(f"\n{task_key.upper()}:")
            print(f"  参加ユーザー数: {stats['user_count']}")
            if stats["accuracy_mean"] is not None:
                print(f"  正答率（平均）: {stats['accuracy_mean'] * 100:.1f}%")
                print(f"  正答数（平均）: {stats['correct_count_mean']:.1f} / 6問")
                if stats["accuracy_stdev"] is not None:
                    print(f"  正答率（標準偏差）: {stats['accuracy_stdev'] * 100:.1f}%")
            else:
                print(f"  正答率（平均）: データなし")

    # 各ユーザーの詳細を表示
    print("\n" + "=" * 80)
    print("【ユーザー別の詳細】")
    print("=" * 80)

    for username, user_stats in results.items():
        if username == "__all_users__":
            continue

        print(f"\n{username}:")
        print("-" * 80)

        if not user_stats:
            print("  データなし")
            continue

        for task_key in sorted([k for k in user_stats.keys() if k.startswith("task")]):
            stats = user_stats[task_key]
            print(f"\n  {task_key.upper()}:")
            print(f"    正答数: {stats['correct_count']} / {stats['total_count']}問")
            print(f"    正答率: {stats['accuracy'] * 100:.1f}%")


def save_results_json(results: dict, output_path: str):
    """
    結果をJSONファイルに保存

    Args:
        results: 分析結果
        output_path: 出力ファイルパス
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n結果をJSONファイルに保存しました: {output_path}")


def main():
    """メイン関数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("正答率の分析を開始します...")

    results = aggregate_all_users(base_dir)

    if not results:
        print("分析する結果が見つかりませんでした。")
        return

    print_results(results)

    # 結果をJSONファイルに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(base_dir, f"accuracy_results_{timestamp}.json")
    save_results_json(results, json_path)

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
