"""作者：Wangyuan；日期：2026-10-29；职责：独立离线JSON命令行入口。"""
from __future__ import annotations
import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from planning import generate_schedule, validate_schedule, monthly_counts, allocate_resources, duration_margin, contiguous_days, export_csv, export_xlsx
def run(payload: dict, output: Path) -> Any:
    """调用约束排班、计数、分配或区间验证。"""
    if payload["action"] == "export_xlsx": return export_xlsx(output=str(output / "schedule.xlsx"), **payload["args"])
    actions = {name: function for name, function in [("schedule", generate_schedule), ("validate", validate_schedule), ("counts", monthly_counts), ("allocate", allocate_resources), ("margin", duration_margin), ("contiguous", contiguous_days)]}
    if payload["action"] not in actions: raise ValueError("未知动作")
    return actions[payload["action"]](**payload["args"])

def demo(output: Path) -> dict:
    """演示资格/休息约束和多特征分配。"""
    people = [{"id": "person-1", "skills": ["review"], "max_assignments": 1}, {"id": "person-2", "skills": ["review"], "max_assignments": 1}]
    slots = [{"id": "slot-1", "start": "2030-01-01T08:00:00+00:00", "end": "2030-01-01T12:00:00+00:00", "skills": ["review"]}, {"id": "slot-2", "start": "2030-01-01T13:00:00+00:00", "end": "2030-01-01T17:00:00+00:00", "skills": ["review"]}]
    schedule = generate_schedule(people, slots, minimum_rest_hours=10)
    (output / "schedule.csv").write_text(export_csv(schedule["assignments"]), encoding="utf-8")
    return {"schedule": schedule, "counts": monthly_counts(schedule["assignments"], slots, "2030-01"), "allocation": allocate_resources([{"id": "item-1", "features": {"work": 3}}, {"id": "item-2", "features": {"work": 2}}], ["group-A", "group-B"], {"work": 1}, [], 0)}

def main() -> int:
    """运行合成演示或显式输入；错误返回非零，不访问外部服务。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo", "run"])
    parser.add_argument("input", nargs="?")
    parser.add_argument("--output", help="显式输出目录；默认临时目录")
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(args.output or temporary)
            output.mkdir(parents=True, exist_ok=True)
            if args.command == "demo":
                result = demo(output)
            else:
                if not args.input:
                    raise ValueError("run必须提供JSON文件")
                source = Path(args.input)
                if source.stat().st_size > 10_000_000:
                    raise ValueError("JSON文件超出预算")
                result = run(json.loads(source.read_text(encoding="utf-8")), output)
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
if __name__ == "__main__":
    raise SystemExit(main())
