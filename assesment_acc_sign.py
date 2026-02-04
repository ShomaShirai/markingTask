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
from scipy import stats
import numpy as np


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


def perform_statistical_tests(results: dict) -> dict:
    """
    タスク間の統計的検定を実行

    Args:
        results: 集計結果

    Returns:
        統計検定の結果
    """
    # 全ユーザーのデータを取得
    if "__all_users__" not in results:
        return {}

    # 各被験者の各タスクにおける正答率を抽出
    task_data = defaultdict(list)

    for username, user_stats in results.items():
        if username == "__all_users__":
            continue

        for task_key in [f"task{i}" for i in range(1, 6)]:
            if task_key in user_stats:
                task_data[task_key].append(user_stats[task_key]["accuracy"])

    # データが揃っているか確認
    task_keys = [f"task{i}" for i in range(1, 6)]
    valid_tasks = [k for k in task_keys if k in task_data and len(task_data[k]) > 0]

    if len(valid_tasks) < 2:
        return {"error": "統計検定に十分なデータがありません"}

    # 全被験者が全タスクを実施しているか確認
    n_subjects = len(task_data[valid_tasks[0]])
    all_complete = all(len(task_data[k]) == n_subjects for k in valid_tasks)

    if not all_complete:
        return {"error": "全被験者が全タスクを完了していません"}

    # データを行列形式に変換（被験者 × タスク）
    data_matrix = np.array([task_data[k] for k in valid_tasks]).T

    # 記述統計
    descriptive_stats = {}
    for i, task_key in enumerate(valid_tasks):
        accuracies = data_matrix[:, i]
        descriptive_stats[task_key] = {
            "mean": float(np.mean(accuracies)),
            "median": float(np.median(accuracies)),
            "std": float(np.std(accuracies, ddof=1)),
            "min": float(np.min(accuracies)),
            "max": float(np.max(accuracies)),
        }

    # フリードマン検定
    friedman_stat, friedman_p = stats.friedmanchisquare(*data_matrix.T)

    statistical_results = {
        "test_type": "Friedman test (対応のあるノンパラメトリック検定)",
        "n_subjects": n_subjects,
        "n_tasks": len(valid_tasks),
        "tasks": valid_tasks,
        "descriptive_stats": descriptive_stats,
        "friedman_test": {
            "statistic": float(friedman_stat),
            "p_value": float(friedman_p),
            "significant": friedman_p < 0.05,
        },
    }

    # フリードマン検定が有意な場合、事後検定（多重比較）を実行
    if friedman_p < 0.05:
        pairwise_results = []
        n_comparisons = len(valid_tasks) * (len(valid_tasks) - 1) // 2
        bonferroni_alpha = 0.05 / n_comparisons

        for i in range(len(valid_tasks)):
            for j in range(i + 1, len(valid_tasks)):
                task1 = valid_tasks[i]
                task2 = valid_tasks[j]

                # Wilcoxon符号順位検定（対応のある2群の比較）
                stat, p_value = stats.wilcoxon(data_matrix[:, i], data_matrix[:, j])

                pairwise_results.append(
                    {
                        "task1": task1,
                        "task2": task2,
                        "statistic": float(stat),
                        "p_value": float(p_value),
                        "significant_bonferroni": p_value < bonferroni_alpha,
                        "mean_diff": float(
                            np.mean(data_matrix[:, i]) - np.mean(data_matrix[:, j])
                        ),
                    }
                )

        statistical_results["post_hoc"] = {
            "method": "Wilcoxon符号順位検定 (Bonferroni補正)",
            "n_comparisons": n_comparisons,
            "bonferroni_alpha": bonferroni_alpha,
            "pairwise_comparisons": pairwise_results,
        }
    else:
        statistical_results["post_hoc"] = {
            "note": "フリードマン検定が有意でないため、事後検定は実行しません"
        }

    return statistical_results


def print_statistical_results(stat_results: dict):
    """
    統計検定の結果を見やすく表示

    Args:
        stat_results: 統計検定の結果
    """
    if "error" in stat_results:
        print(f"\n統計検定エラー: {stat_results['error']}")
        return

    print("\n" + "=" * 80)
    print("統計的検定の結果 (正答率)")
    print("=" * 80)

    print(f"\n検定手法: {stat_results['test_type']}")
    print(f"被験者数: {stat_results['n_subjects']}")
    print(f"タスク数: {stat_results['n_tasks']}")

    # 記述統計
    print("\n【記述統計】")
    print("-" * 80)
    for task_key, stats_dict in stat_results["descriptive_stats"].items():
        print(f"\n{task_key.upper()}:")
        print(f"  平均: {stats_dict['mean'] * 100:.1f}%")
        print(f"  中央値: {stats_dict['median'] * 100:.1f}%")
        print(f"  標準偏差: {stats_dict['std'] * 100:.1f}%")
        print(
            f"  範囲: {stats_dict['min'] * 100:.1f}% - {stats_dict['max'] * 100:.1f}%"
        )

    # フリードマン検定
    print("\n【フリードマン検定】")
    print("-" * 80)
    friedman = stat_results["friedman_test"]
    print(f"検定統計量: {friedman['statistic']:.4f}")
    print(f"p値: {friedman['p_value']:.6f}")
    print(
        f"結果: {'有意差あり (p < 0.05)' if friedman['significant'] else '有意差なし (p ≥ 0.05)'}"
    )

    # 事後検定
    if "pairwise_comparisons" in stat_results["post_hoc"]:
        print("\n【事後検定（多重比較）】")
        print("-" * 80)
        post_hoc = stat_results["post_hoc"]
        print(f"検定手法: {post_hoc['method']}")
        print(f"比較回数: {post_hoc['n_comparisons']}")
        print(f"Bonferroni補正後の有意水準: {post_hoc['bonferroni_alpha']:.6f}")

        print("\nタスク間の比較:")
        for comparison in post_hoc["pairwise_comparisons"]:
            task1 = comparison["task1"].upper()
            task2 = comparison["task2"].upper()
            p_val = comparison["p_value"]
            significant = comparison["significant_bonferroni"]
            mean_diff = comparison["mean_diff"] * 100

            sig_marker = "***" if significant else "n.s."
            print(
                f"  {task1} vs {task2}: p = {p_val:.6f} {sig_marker} (平均差: {mean_diff:+.1f}%)"
            )

        print("\n*** p < Bonferroni補正後の有意水準")
        print("n.s. = not significant (有意差なし)")
    else:
        print("\n【事後検定】")
        print("-" * 80)
        print(stat_results["post_hoc"]["note"])


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

    # 統計的検定を実行
    print("\n統計的検定を実行中...")
    stat_results = perform_statistical_tests(results)
    print_statistical_results(stat_results)

    # 結果をJSONファイルに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(base_dir, f"accuracy_results_{timestamp}.json")
    combined_results = {
        "aggregated_data": results,
        "statistical_tests": stat_results,
    }
    save_results_json(combined_results, json_path)

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
