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

    # 全ユーザーの平均を計算
    all_users_stats = {}
    for task_key, data in task_aggregation.items():
        all_users_stats[task_key] = {
            "start_latency_ms_mean": statistics.mean(data["start_latency_ms"])
            if data["start_latency_ms"]
            else None,
            "stroke_duration_ms_mean": statistics.mean(data["stroke_duration_ms"])
            if data["stroke_duration_ms"]
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
                f"  描画時間（平均）: {stats['stroke_duration_ms_mean']:.1f} ms"
                if stats["stroke_duration_ms_mean"]
                else "  描画時間（平均）: データなし"
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


def main():
    """メイン関数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("課題結果の分析を開始します...")

    results = aggregate_all_users(base_dir)

    if not results:
        print("分析する結果が見つかりませんでした。")
        return

    print_results(results)

    # 結果をJSONファイルに保存
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(base_dir, f"analysis_results_{timestamp}.json")
    save_results_json(results, json_path)

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
