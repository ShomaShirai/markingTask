"""
結果分析スクリプト
各ユーザーの課題モードごとのメトリクスを集計し、平均処理時間を計算する
"""

import os
import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import statistics
import numpy as np
from scipy import stats
from itertools import combinations


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


def load_metrics_from_csv(csv_path: Path) -> list[dict]:
    """
    metrics.csvからデータを読み込む

    Args:
        csv_path: CSVファイルのパス

    Returns:
        メトリクスデータのリスト
    """
    metrics = []

    if not csv_path.exists():
        return metrics

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 空行をスキップ
                if not row.get("image_id"):
                    continue

                metrics.append(
                    {
                        "image_id": row.get("image_id", ""),
                        "mode": row.get("mode", ""),
                        "start_latency_ms": int(row["start_latency_ms"])
                        if row.get("start_latency_ms")
                        else None,
                        "stroke_duration_ms": int(row["stroke_duration_ms"])
                        if row.get("stroke_duration_ms")
                        else None,
                        "rotation_deg": float(row["rotation_deg"])
                        if row.get("rotation_deg")
                        else None,
                    }
                )
    except Exception as e:
        print(f"Warning: Failed to read {csv_path}: {e}")

    return metrics


def analyze_user_results(user_dir: Path) -> dict:
    """
    1人のユーザーの結果を分析

    Args:
        user_dir: ユーザーの結果ディレクトリ

    Returns:
        課題モードごとの統計情報
    """
    task_stats = {}

    # 課題モード（1〜5）のディレクトリを探す
    for task_num in range(1, 6):
        task_dir = user_dir / str(task_num)
        if not task_dir.exists():
            continue

        metrics_csv = task_dir / "metrics.csv"
        if not metrics_csv.exists():
            continue

        # メトリクスを読み込み
        metrics = load_metrics_from_csv(metrics_csv)

        if not metrics:
            continue

        # start_latency_msとstroke_duration_msを抽出
        start_latencies = [
            m["start_latency_ms"] for m in metrics if m["start_latency_ms"] is not None
        ]
        stroke_durations = [
            m["stroke_duration_ms"]
            for m in metrics
            if m["stroke_duration_ms"] is not None
        ]

        task_stats[f"task{task_num}"] = {
            "count": len(metrics),
            "start_latency_ms": {
                "mean": statistics.mean(start_latencies) if start_latencies else None,
                "stdev": statistics.stdev(start_latencies)
                if len(start_latencies) > 1
                else None,
            },
            "stroke_duration_ms": {
                "mean": statistics.mean(stroke_durations) if stroke_durations else None,
                "stdev": statistics.stdev(stroke_durations)
                if len(stroke_durations) > 1
                else None,
            },
        }

    return task_stats


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
    task_aggregation = defaultdict(
        lambda: {"start_latency_ms": [], "stroke_duration_ms": []}
    )

    for user_dir in result_dirs:
        username = user_dir.name
        print(f"\n分析中: {username}")

        user_stats = analyze_user_results(user_dir)
        all_results[username] = user_stats

        # 全ユーザー集計用にデータを追加
        for task_key, stats in user_stats.items():
            if stats["start_latency_ms"]["mean"] is not None:
                task_aggregation[task_key]["start_latency_ms"].append(
                    stats["start_latency_ms"]["mean"]
                )
            if stats["stroke_duration_ms"]["mean"] is not None:
                task_aggregation[task_key]["stroke_duration_ms"].append(
                    stats["stroke_duration_ms"]["mean"]
                )

    # 全ユーザーの平均と標準偏差を計算
    all_users_stats = {}
    for task_key, data in task_aggregation.items():
        all_users_stats[task_key] = {
            "start_latency_ms_mean": statistics.mean(data["start_latency_ms"])
            if data["start_latency_ms"]
            else None,
            "start_latency_ms_stdev": statistics.stdev(data["start_latency_ms"])
            if len(data["start_latency_ms"]) > 1
            else None,
            "stroke_duration_ms_mean": statistics.mean(data["stroke_duration_ms"])
            if data["stroke_duration_ms"]
            else None,
            "stroke_duration_ms_stdev": statistics.stdev(data["stroke_duration_ms"])
            if len(data["stroke_duration_ms"]) > 1
            else None,
            "user_count": len(data["start_latency_ms"]),
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
    print("課題モード別 平均処理時間の分析結果")
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
            print(
                f"  開始潜時（平均）: {stats['start_latency_ms_mean']:.1f} ms"
                if stats["start_latency_ms_mean"]
                else "  開始潜時（平均）: データなし"
            )
            print(
                f"  開始潜時（標準偏差）: {stats['start_latency_ms_stdev']:.1f} ms"
                if stats["start_latency_ms_stdev"]
                else "  開始潜時（標準偏差）: -"
            )
            print(
                f"  描画時間（平均）: {stats['stroke_duration_ms_mean']:.1f} ms"
                if stats["stroke_duration_ms_mean"]
                else "  描画時間（平均）: データなし"
            )
            print(
                f"  描画時間（標準偏差）: {stats['stroke_duration_ms_stdev']:.1f} ms"
                if stats["stroke_duration_ms_stdev"]
                else "  描画時間（標準偏差）: -"
            )

    # 各ユーザーの詳細を表示
    print("\n" + "=" * 80)
    print("【ユーザー別の詳細】")
    print("=" * 80)

    for username, user_stats in results.items():
        if username == "__all_users__":
            continue

        print(f"\n{username}:")
        print("-" * 80)

        for task_key in sorted([k for k in user_stats.keys() if k.startswith("task")]):
            stats = user_stats[task_key]
            print(f"\n  {task_key.upper()}:")
            print(f"    試行回数: {stats['count']}")

            sl = stats["start_latency_ms"]
            print(f"    開始潜時:")
            print(
                f"      平均: {sl['mean']:.1f} ms"
                if sl["mean"]
                else "      平均: データなし"
            )
            print(
                f"      標準偏差: {sl['stdev']:.1f} ms"
                if sl["stdev"]
                else "      標準偏差: -"
            )

            sd = stats["stroke_duration_ms"]
            print(f"    描画時間:")
            print(
                f"      平均: {sd['mean']:.1f} ms"
                if sd["mean"]
                else "      平均: データなし"
            )
            print(
                f"      標準偏差: {sd['stdev']:.1f} ms"
                if sd["stdev"]
                else "      標準偏差: -"
            )


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


def perform_statistical_tests(results: dict) -> dict:
    """
    タスク間の統計的有意差検定を実行

    Args:
        results: aggregate_all_usersの結果

    Returns:
        統計検定の結果
    """
    print("\n" + "=" * 80)
    print("統計的有意差検定")
    print("=" * 80)

    # 被験者ごとのタスク別データを抽出
    users_data = {}
    for username, user_stats in results.items():
        if username == "__all_users__":
            continue

        task_means = {}
        for task_key in sorted([k for k in user_stats.keys() if k.startswith("task")]):
            stats_data = user_stats[task_key]
            # start_latency_msとstroke_duration_msの両方を記録
            task_means[task_key] = {
                "start_latency_ms": stats_data["start_latency_ms"]["mean"],
                "stroke_duration_ms": stats_data["stroke_duration_ms"]["mean"],
            }

        users_data[username] = task_means

    # 統計検定結果を格納
    test_results = {}

    # 開始潜時（start_latency_ms）の検定
    print("\n【開始潜時（start_latency_ms）の検定】")
    print("-" * 80)
    test_results["start_latency_ms"] = perform_friedman_test(
        users_data, "start_latency_ms"
    )

    # 描画時間（stroke_duration_ms）の検定
    print("\n【描画時間（stroke_duration_ms）の検定】")
    print("-" * 80)
    test_results["stroke_duration_ms"] = perform_friedman_test(
        users_data, "stroke_duration_ms"
    )

    return test_results


def perform_friedman_test(users_data: dict, metric: str) -> dict:
    """
    フリードマン検定と事後検定（多重比較）を実行

    Args:
        users_data: 被験者ごとのタスク別データ
        metric: 検定する指標名（"start_latency_ms" or "stroke_duration_ms"）

    Returns:
        検定結果
    """
    # データを整形（タスクごとに被験者のデータを配列化）
    tasks = [f"task{i}" for i in range(1, 6)]
    task_data = {task: [] for task in tasks}

    for username, task_means in users_data.items():
        for task in tasks:
            if task in task_means and task_means[task][metric] is not None:
                task_data[task].append(task_means[task][metric])

    # 全てのタスクでデータが揃っている被験者のみを使用
    n_subjects = min(len(task_data[task]) for task in tasks)

    # データを配列化（各行が1被験者、各列が1タスク）
    data_arrays = [task_data[task][:n_subjects] for task in tasks]

    print(f"被験者数: {n_subjects}")
    print(f"タスク数: {len(tasks)}")

    # 各タスクの記述統計
    print("\n記述統計:")
    for i, task in enumerate(tasks):
        data = data_arrays[i]
        print(
            f"  {task.upper()}: 平均={np.mean(data):.1f}, 中央値={np.median(data):.1f}, "
            f"標準偏差={np.std(data, ddof=1):.1f}"
        )

    # フリードマン検定
    friedman_stat, friedman_p = stats.friedmanchisquare(*data_arrays)

    print(f"\nフリードマン検定:")
    print(f"  統計量 (χ²): {friedman_stat:.4f}")
    print(f"  p値: {friedman_p:.6f}")

    result = {
        "test": "Friedman",
        "statistic": friedman_stat,
        "p_value": friedman_p,
        "n_subjects": n_subjects,
        "significant": friedman_p < 0.05,
    }

    if friedman_p < 0.05:
        print(f"  → 有意差あり (p < 0.05)")
        print("\n事後検定（多重比較）:")
        post_hoc = perform_post_hoc_tests(data_arrays, tasks)
        result["post_hoc"] = post_hoc
    else:
        print(f"  → 有意差なし (p >= 0.05)")

    return result


def perform_post_hoc_tests(data_arrays: list, tasks: list) -> dict:
    """
    事後検定（Wilcoxon符号順位検定 + Bonferroni補正）

    Args:
        data_arrays: 各タスクのデータ配列
        tasks: タスク名のリスト

    Returns:
        多重比較の結果
    """
    # 全ての組み合わせで比較
    comparisons = list(combinations(range(len(tasks)), 2))
    n_comparisons = len(comparisons)
    bonferroni_alpha = 0.05 / n_comparisons

    print(f"  Wilcoxon符号順位検定（対応あり）")
    print(f"  比較回数: {n_comparisons}")
    print(f"  Bonferroni補正後の有意水準: {bonferroni_alpha:.6f}")
    print()

    post_hoc_results = []

    for i, j in comparisons:
        task1 = tasks[i]
        task2 = tasks[j]
        data1 = data_arrays[i]
        data2 = data_arrays[j]

        # Wilcoxon符号順位検定（対応あり）
        stat, p_value = stats.wilcoxon(data1, data2)

        is_significant = p_value < bonferroni_alpha

        mean_diff = np.mean(data1) - np.mean(data2)

        result_item = {
            "task1": task1,
            "task2": task2,
            "statistic": stat,
            "p_value": p_value,
            "significant": is_significant,
            "mean_difference": mean_diff,
        }
        post_hoc_results.append(result_item)

        sig_mark = "***" if is_significant else "n.s."
        print(
            f"  {task1.upper()} vs {task2.upper()}: "
            f"p={p_value:.6f} {sig_mark} (平均差={mean_diff:.1f})"
        )

    return post_hoc_results


def main():
    """メイン関数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("課題結果の分析を開始します...")

    results = aggregate_all_users(base_dir)

    if not results:
        print("分析する結果が見つかりませんでした。")
        return

    print_results(results)

    # 統計的有意差検定を実行
    test_results = perform_statistical_tests(results)

    # 結果をJSONファイルに保存
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 分析結果と統計検定結果を統合
    full_results = {"analysis": results, "statistical_tests": test_results}

    json_path = os.path.join(base_dir, f"analysis_results_{timestamp}.json")
    save_results_json(full_results, json_path)

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
