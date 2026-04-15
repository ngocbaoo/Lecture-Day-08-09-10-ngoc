"""
eval_trace.py — Trace Evaluation & Comparison
Sprint 4: Chạy pipeline với test questions, phân tích trace, so sánh single vs multi.

Chạy:
    python eval_trace.py                  # Chạy 15 test questions
    python eval_trace.py --grading        # Chạy grading questions (sau 17:00)
    python eval_trace.py --analyze        # Phân tích trace đã có
    python eval_trace.py --compare        # So sánh single vs multi

Outputs:
    artifacts/traces/          — trace của từng câu hỏi
    artifacts/grading_run.jsonl — log câu hỏi chấm điểm
    artifacts/eval_report.json  — báo cáo tổng kết
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Optional, Any

# Import graph
sys.path.insert(0, os.path.dirname(__file__))
from graph import run_graph


def _normalize_mcp_tools(mcp_tools_used: Any) -> list[str]:
    """Normalize MCP tool list to list[str] for trace schema."""
    if not isinstance(mcp_tools_used, list):
        return []
    tools: list[str] = []
    for item in mcp_tools_used:
        if isinstance(item, str):
            tools.append(item)
        elif isinstance(item, dict):
            name = item.get("tool") or item.get("name")
            if isinstance(name, str) and name.strip():
                tools.append(name.strip())
    return tools


def _normalize_trace(result: dict, task: str) -> dict:
    """
    Build trace payload that matches required schema exactly.
    """
    now = datetime.now().isoformat(timespec="seconds")
    run_id = str(result.get("run_id") or f"run_{datetime.now().strftime('%Y-%m-%d_%H%M')}")
    latency = result.get("latency_ms")
    try:
        latency_ms = int(latency) if latency is not None else 0
    except (TypeError, ValueError):
        latency_ms = 0

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    trace = {
        "run_id": run_id,
        "task": str(result.get("task") or task),
        "supervisor_route": str(result.get("supervisor_route", "")),
        "route_reason": str(result.get("route_reason", "")),
        "workers_called": [str(w) for w in result.get("workers_called", []) if str(w).strip()],
        "mcp_tools_used": _normalize_mcp_tools(result.get("mcp_tools_used", [])),
        "retrieved_sources": [str(s) for s in result.get("retrieved_sources", []) if str(s).strip()],
        "final_answer": str(result.get("final_answer", "")),
        "confidence": confidence,
        "hitl_triggered": bool(result.get("hitl_triggered", False)),
        "latency_ms": latency_ms,
        "timestamp": str(result.get("timestamp") or now),
    }
    return trace


def _save_trace(trace: dict, output_dir: str = None) -> str:
    """Save normalized trace JSON to artifacts/traces."""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "artifacts", "traces")
        
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{trace['run_id']}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)
    return filename


def _make_unique_run_id(base_run_id: str, q_id: str, index: int) -> str:
    """
    Ensure trace filename is unique per question/run to avoid overwrite collisions.
    """
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_base = base_run_id.strip() or "run"
    return f"{safe_base}_{q_id}_{index:02d}_{suffix}"


# ─────────────────────────────────────────────
# 1. Run Pipeline on Test Questions
# ─────────────────────────────────────────────

def run_test_questions(questions_file: str = None) -> list:
    """
    Chạy pipeline với danh sách câu hỏi, lưu trace từng câu.
    """
    if questions_file is None:
        questions_file = os.path.join(os.path.dirname(__file__), "data", "test_questions.json")
        
    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n📋 Running {len(questions)} test questions from {questions_file}")
    print("=" * 60)

    results = []
    for i, q in enumerate(questions, 1):
        question_text = q["question"]
        q_id = q.get("id", f"q{i:02d}")

        print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

        try:
            result = run_graph(question_text)
            trace = _normalize_trace(result, question_text)
            trace["run_id"] = _make_unique_run_id(str(trace.get("run_id", "")), q_id, i)

            # Save individual trace (required schema)
            trace_file = _save_trace(trace)
            print(f"  ✓ route={trace.get('supervisor_route', '?')}, "
                  f"conf={trace.get('confidence', 0):.2f}, "
                  f"{trace.get('latency_ms', 0)}ms")

            results.append({
                "id": q_id,
                "question": question_text,
                "expected_answer": q.get("expected_answer", ""),
                "expected_sources": q.get("expected_sources", []),
                "difficulty": q.get("difficulty", "unknown"),
                "category": q.get("category", "unknown"),
                "result": trace,
                "trace_file": trace_file,
            })

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                "id": q_id,
                "question": question_text,
                "error": str(e),
                "result": None,
            })

    print(f"\n✅ Done. {sum(1 for r in results if r.get('result'))} / {len(results)} succeeded.")
    return results


# ─────────────────────────────────────────────
# 2. Run Grading Questions (Sprint 4)
# ─────────────────────────────────────────────

def run_grading_questions(questions_file: str = None) -> str:
    """
    Chạy pipeline với grading questions và lưu JSONL log.
    """
    if questions_file is None:
        questions_file = os.path.join(os.path.dirname(__file__), "data", "grading_questions.json")
        
    if not os.path.exists(questions_file):
        print(f"❌ {questions_file} chưa được public (sau 17:00 mới có).")
        return ""

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    output_file = os.path.join(artifacts_dir, "grading_run.jsonl")

    print(f"\n🎯 Running GRADING questions — {len(questions)} câu")
    print(f"   Output → {output_file}")
    print("=" * 60)

    with open(output_file, "w", encoding="utf-8") as out:
        for i, q in enumerate(questions, 1):
            q_id = q.get("id", f"gq{i:02d}")
            question_text = q["question"]
            print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

            try:
                result = run_graph(question_text)
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": result.get("final_answer", "PIPELINE_ERROR: no answer"),
                    "sources": result.get("retrieved_sources", []),
                    "supervisor_route": result.get("supervisor_route", ""),
                    "route_reason": result.get("route_reason", ""),
                    "workers_called": result.get("workers_called", []),
                    "mcp_tools_used": [t.get("tool") for t in result.get("mcp_tools_used", [])],
                    "confidence": result.get("confidence", 0.0),
                    "hitl_triggered": result.get("hitl_triggered", False),
                    "latency_ms": result.get("latency_ms"),
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✓ route={record['supervisor_route']}, conf={record['confidence']:.2f}")
            except Exception as e:
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "supervisor_route": "error",
                    "route_reason": str(e),
                    "workers_called": [],
                    "mcp_tools_used": [],
                    "confidence": 0.0,
                    "hitl_triggered": False,
                    "latency_ms": None,
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✗ ERROR: {e}")

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n✅ Grading log saved → {output_file}")
    return output_file


# ─────────────────────────────────────────────
# 3. Analyze Traces
# ─────────────────────────────────────────────

def analyze_traces(traces_dir: str = None) -> dict:
    """
    Đọc tất cả trace files và tính metrics tổng hợp.

    Metrics:
    - routing_distribution: % câu đi vào mỗi worker
    - avg_confidence: confidence trung bình
    - avg_latency_ms: latency trung bình
    - mcp_usage_rate: % câu có MCP tool call
    - hitl_rate: % câu trigger HITL
    - source_coverage: các tài liệu nào được dùng nhiều nhất

    Returns:
        dict of metrics
    """
    if traces_dir is None:
        traces_dir = os.path.join(os.path.dirname(__file__), "artifacts", "traces")
        
    if not os.path.exists(traces_dir):
        print(f"⚠️  {traces_dir} không tồn tại. Chạy run_test_questions() trước.")
        return {}

    trace_files = [f for f in os.listdir(traces_dir) if f.endswith(".json")]
    if not trace_files:
        print(f"⚠️  Không có trace files trong {traces_dir}.")
        return {}

    traces = []
    for fname in trace_files:
        with open(os.path.join(traces_dir, fname), encoding="utf-8") as f:
            raw = json.load(f)
        traces.append(_normalize_trace(raw, task=str(raw.get("task", ""))))

    # Compute metrics
    routing_counts = {}
    confidences = []
    latencies = []
    mcp_calls = 0
    hitl_triggers = 0
    source_counts = {}

    for t in traces:
        route = t.get("supervisor_route", "unknown")
        routing_counts[route] = routing_counts.get(route, 0) + 1

        conf = t.get("confidence", 0)
        if conf:
            confidences.append(conf)

        lat = t.get("latency_ms")
        if lat:
            latencies.append(lat)

        if t.get("mcp_tools_used"):
            mcp_calls += 1

        if t.get("hitl_triggered"):
            hitl_triggers += 1

        for src in t.get("retrieved_sources", []):
            source_counts[src] = source_counts.get(src, 0) + 1

    total = len(traces)
    metrics = {
        "total_traces": total,
        "routing_distribution": {k: f"{v}/{total} ({100*v//total}%)" for k, v in routing_counts.items()},
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "mcp_usage_rate": f"{mcp_calls}/{total} ({100*mcp_calls//total}%)" if total else "0%",
        "hitl_rate": f"{hitl_triggers}/{total} ({100*hitl_triggers//total}%)" if total else "0%",
        "top_sources": sorted(source_counts.items(), key=lambda x: -x[1])[:5],
    }

    return metrics


def analyze_trace(traces_dir: str = "artifacts/traces") -> dict:
    """Backward-compatible alias for README naming."""
    return analyze_traces(traces_dir)


# ─────────────────────────────────────────────
# 4. Compare Single vs Multi Agent
# ─────────────────────────────────────────────

def compare_single_vs_multi(
    multi_traces_dir: str = None,
    day08_results_file: Optional[str] = None,
) -> dict:
    """
    So sánh Day 08 (single agent RAG) vs Day 09 (multi-agent).

    TODO Sprint 4: Điền kết quả thực tế từ Day 08 vào day08_baseline.

    Returns:
        dict của comparison metrics
    """
    multi_metrics = analyze_traces(multi_traces_dir)

    # TODO: Load Day 08 results nếu có
    # Nếu không có, dùng baseline giả lập để format
    day08_baseline = {
        "total_questions": 15,
        "avg_confidence": 0.84,         # Từ Faithfulness/Relevance 4.2/5
        "avg_latency_ms": 1250,         # Ước tính trung bình Single Agent RAG
        "abstain_rate": 0.1,            # Tỷ lệ xử lý câu hỏi không có context
        "multi_hop_accuracy": 0.7,      # Tỷ lệ câu hỏi liên tỉnh (Cross-Document)
    }

    if day08_results_file and os.path.exists(day08_results_file):
        with open(day08_results_file) as f:
            day08_baseline = json.load(f)

    d08_conf = float(day08_baseline.get("avg_confidence", 0) or 0)
    d08_lat = int(day08_baseline.get("avg_latency_ms", 0) or 0)
    d09_conf = float(multi_metrics.get("avg_confidence", 0) or 0)
    d09_lat = int(multi_metrics.get("avg_latency_ms", 0) or 0)
    conf_delta = round(d09_conf - d08_conf, 3)
    lat_delta = d09_lat - d08_lat

    comparison = {
        "generated_at": datetime.now().isoformat(),
        "day08_single_agent": day08_baseline,
        "day09_multi_agent": multi_metrics,
        "analysis": {
            "routing_visibility": "Day 09 có route_reason cho từng câu → dễ debug hơn Day 08",
            "latency_delta": f"{lat_delta:+d} ms (Day09 - Day08)",
            "accuracy_delta": f"confidence delta {conf_delta:+.3f} (Day09 - Day08)",
            "debuggability": "Multi-agent: có thể test từng worker độc lập. Single-agent: không thể.",
            "mcp_benefit": "Day 09 có thể extend capability qua MCP không cần sửa core. Day 08 phải hard-code.",
        },
    }

    return comparison


# ─────────────────────────────────────────────
# 5. Save Eval Report
# ─────────────────────────────────────────────

def save_eval_report(comparison: dict) -> str:
    """Lưu báo cáo eval tổng kết ra file JSON."""
    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    output_file = os.path.join(artifacts_dir, "eval_report.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    return output_file


# ─────────────────────────────────────────────
# 6. CLI Entry Point
# ─────────────────────────────────────────────

def print_metrics(metrics: dict):
    """Print metrics đẹp."""
    if not metrics:
        return
    print("\n📊 Trace Analysis:")
    for k, v in metrics.items():
        if isinstance(v, list):
            print(f"  {k}:")
            for item in v:
                print(f"    • {item}")
        elif isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 09 Lab — Trace Evaluation")
    parser.add_argument("--grading", action="store_true", help="Run grading questions")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing traces")
    parser.add_argument("--compare", action="store_true", help="Compare single vs multi")
    parser.add_argument("--test-file", default=None, help="Test questions file")
    args = parser.parse_args()

    if args.grading:
        # Chạy grading questions
        log_file = run_grading_questions()
        if log_file:
            print(f"\n✅ Grading log: {log_file}")
            print("   Nộp file này trước 18:00!")

    elif args.analyze:
        # Phân tích traces
        metrics = analyze_traces()
        print_metrics(metrics)

    elif args.compare:
        # So sánh single vs multi
        comparison = compare_single_vs_multi()
        report_file = save_eval_report(comparison)
        print(f"\n📊 Comparison report saved → {report_file}")
        print("\n=== Day 08 vs Day 09 ===")
        for k, v in comparison.get("analysis", {}).items():
            print(f"  {k}: {v}")

    else:
        # Default: chạy test questions
        results = run_test_questions(args.test_file)

        # Phân tích trace
        metrics = analyze_traces()
        print_metrics(metrics)

        # Lưu báo cáo
        comparison = compare_single_vs_multi()
        report_file = save_eval_report(comparison)
        print(f"\n📄 Eval report → {report_file}")
        print("\n✅ Sprint 4 complete!")
        print("   Next: Điền docs/ templates và viết reports/")
