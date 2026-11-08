"""作者：Wangyuan；日期：2026-10-29；职责：显式约束排班、工作量分配与时间余量。"""
from __future__ import annotations

import csv
import io
import math
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from itertools import product
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def calendar_zone(name: str) -> ZoneInfo:
    """显式业务日历时区，默认UTC；不从首行或电脑所在地猜测。"""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError("业务日历时区无效") from exc


def stamp(value: str) -> datetime:
    """拒绝没有时区的时间。"""
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("时刻须带时区")
    return result.astimezone(timezone.utc)


def interval(row: dict) -> tuple[datetime, datetime]:
    """解析有效的正时长区间。"""
    start, end = stamp(row["start"]), stamp(row["end"])
    if end <= start:
        raise ValueError("结束必须晚于开始")
    return start, end


def validate_schedule(assignments: list[dict], people: list[dict], slots: list[dict],
                      minimum_rest_hours: float = 0, *, calendar_timezone: str = "UTC") -> list[dict]:
    """检查身份、资格、可用性、重叠、休息间隔、数量上限与缺岗。"""
    if not math.isfinite(minimum_rest_hours) or minimum_rest_hours < 0:
        raise ValueError("休息参数无效")
    zone = calendar_zone(calendar_timezone)
    persons, shifts = {x["id"]: x for x in people}, {x["id"]: x for x in slots}
    if len(persons) != len(people) or len(shifts) != len(slots):
        raise ValueError("人员或班次身份重复")
    for shift in slots:
        interval(shift)
        if type(shift.get("needed", 1)) is not int or shift.get("needed", 1) < 1:
            raise ValueError("岗位需求须为正整数")
    seen, issues, by_person, counts = set(), [], {}, Counter()
    for assignment in assignments:
        pid, sid = assignment.get("person"), assignment.get("slot")
        if pid not in persons or sid not in shifts:
            issues.append({"kind": "unknown_identity", "assignment": assignment}); continue
        if (pid, sid) in seen:
            issues.append({"kind": "duplicate", "person": pid, "slot": sid}); continue
        seen.add((pid, sid)); counts[sid] += 1
        person, shift = persons[pid], shifts[sid]
        start, end = interval(shift)
        if not set(shift.get("skills", [])) <= set(person.get("skills", [])):
            issues.append({"kind": "qualification", "person": pid, "slot": sid})
        for blocked in person.get("unavailable", []):
            a, b = interval(blocked)
            if start < b and a < end:
                issues.append({"kind": "unavailable", "person": pid, "slot": sid})
        if person.get("available") and not any(interval(window)[0] <= start and end <= interval(window)[1] for window in person["available"]):
            issues.append({"kind": "outside_availability", "person": pid, "slot": sid})
        by_person.setdefault(pid, []).append((start, end, sid))
    for pid, intervals in by_person.items():
        intervals.sort()
        if len(intervals) > persons[pid].get("max_assignments", len(intervals)):
            issues.append({"kind": "quota", "person": pid})
        for left, right in zip(intervals, intervals[1:]):
            if (right[0] - left[1]).total_seconds() < minimum_rest_hours * 3600:
                issues.append({"kind": "rest_or_overlap", "person": pid, "slots": [left[2], right[2]]})
        max_days = persons[pid].get("max_consecutive_days")
        if max_days is not None:
            if type(max_days) is not int or max_days < 1:
                raise ValueError("连续天数须为正整数")
            days = sorted({start.astimezone(zone).date() for start, _, _ in intervals}); run = 0; previous = None
            for day in days:
                run = run + 1 if previous and day == previous + timedelta(days=1) else 1
                previous = day
                if run > max_days:
                    issues.append({"kind": "consecutive_days", "person": pid, "date": day.isoformat()})
    for sid, shift in shifts.items():
        if counts[sid] != shift.get("needed", 1):
            issues.append({"kind": "coverage", "slot": sid, "actual": counts[sid], "required": shift.get("needed", 1)})
    return issues


def generate_schedule(people: list[dict], slots: list[dict], *, minimum_rest_hours: float,
                      budget: int = 50_000, calendar_timezone: str = "UTC") -> dict:
    """最受限班次优先、有界回溯；明确报告无解或预算耗尽，不称全局最优。"""
    if type(budget) is not int or budget < 1:
        raise ValueError("搜索预算须为正整数")
    validate_schedule([], people, slots, minimum_rest_hours, calendar_timezone=calendar_timezone)
    if sum(slot.get("needed",1) for slot in slots)>200:raise ValueError("排班搜索最多支持200个需求单位；请拆分计划")
    units = [slot for slot in slots for _ in range(slot.get("needed", 1))]
    units.sort(key=lambda s: (sum(set(s.get("skills", [])) <= set(p.get("skills", [])) for p in people), s["start"], s["id"]))
    chosen: list[dict] = []; best: list[dict] = []; visited = 0
    def search(index: int) -> bool:
        """在固定搜索预算内递归选择满足硬约束的人员。"""
        nonlocal visited, best
        if len(chosen) > len(best): best = list(chosen)
        if index == len(units): return True
        if visited >= budget: return False
        slot = units[index]; counts = Counter(x["person"] for x in chosen)
        ordered = sorted(people, key=lambda p: (slot["id"] not in p.get("preferred_slots", []), counts[p["id"]], p["id"]))
        for person in ordered:
            if visited >= budget: break
            visited += 1
            candidate = {"person": person["id"], "slot": slot["id"]}
            candidate_rows = chosen + [candidate]
            invalid = [issue for issue in validate_schedule(candidate_rows, people, slots, minimum_rest_hours, calendar_timezone=calendar_timezone) if issue["kind"] != "coverage"]
            if invalid: continue
            chosen.append(candidate)
            if search(index + 1): return True
            chosen.pop()
        return False
    complete = search(0)
    assignments = chosen if complete else best
    return {"status": "complete" if complete else "budget_exhausted" if visited >= budget else "infeasible",
            "assignments": assignments, "visited": visited,
            "issues": validate_schedule(assignments, people, slots, minimum_rest_hours, calendar_timezone=calendar_timezone), "optimal": False, "calendar_timezone": calendar_timezone}


def monthly_counts(assignments: list[dict], slots: list[dict], month: str,
                   factors: dict[str, float] | None = None, *, calendar_timezone: str = "UTC") -> list[dict]:
    """按显式月份/类别计数，重复身份拒绝，折算系数由调用方给出。"""
    date.fromisoformat(month + "-01")
    zone = calendar_zone(calendar_timezone)
    lookup = {x["id"]: x for x in slots}; seen = set(); result = {}
    if len(lookup) != len(slots): raise ValueError("班次身份重复")
    factors = factors or {}
    if any(isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in factors.values()):
        raise ValueError("折算系数无效")
    for row in assignments:
        key = (row["person"], row["slot"])
        if key in seen: raise ValueError("重复排班")
        seen.add(key)
        slot = lookup[row["slot"]]; interval(slot)
        if stamp(slot["start"]).astimezone(zone).strftime("%Y-%m") != month: continue
        kind = slot.get("kind", "default"); item = result.setdefault(row["person"], {"person": row["person"], "count": 0, "weighted": 0, "by_kind": {}})
        item["count"] += 1; item["weighted"] += factors.get(kind, 1)
        item["by_kind"][kind] = item["by_kind"].get(kind, 0) + 1
    return sorted(result.values(), key=lambda x: x["person"])


def allocate_resources(items: list[dict], groups: list[str], weights: dict[str, float],
                       conflicts: list[list[str]], conflict_penalty: float, *, budget: int = 50_000,
                       method: str = "exact", seed: int = 0, restarts: int = 40) -> dict:
    """泛化原多特征分配评分：负载差与冲突惩罚，受限枚举并给出解释。"""
    if len(groups) < 2 or len(set(groups)) != len(groups) or len({x["id"] for x in items}) != len(items):
        raise ValueError("分组或任务标识无效")
    for value in [*weights.values(), conflict_penalty]:
        if isinstance(value, bool) or not math.isfinite(value) or value < 0: raise ValueError("权重无效")
    for item in items:
        if set(weights) - set(item.get("features", {})): raise ValueError("任务缺少已配置特征")
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in item.get("features", {}).values()): raise ValueError("任务特征无效")
    ids = {x["id"] for x in items}
    if any(len(pair) != 2 or not set(pair) <= ids for pair in conflicts): raise ValueError("冲突引用无效")
    if type(budget) is not int or budget < 1: raise ValueError("预算无效")
    if method not in {"exact", "local"} or type(seed) is not int or type(restarts) is not int or restarts < 1:
        raise ValueError("搜索方式、随机种子或重启次数无效")
    choices = []
    for item in items:
        allowed = item.get("allowed_groups", groups)
        if not isinstance(allowed, list) or not allowed or not set(allowed) <= set(groups):
            raise ValueError("允许分组须为非空有效列表")
        fixed = item.get("fixed_group")
        if fixed is not None and fixed not in allowed: raise ValueError("固定分组不在允许列表中")
        choices.append([fixed] if fixed is not None else list(dict.fromkeys(allowed)))
    best = None; examined = 0
    def evaluate(assignment: tuple | list) -> dict | None:
        """所有候选评分统一计入预算，不复用公司特征或优先级。"""
        nonlocal best, examined
        if examined >= budget: return None
        examined += 1
        if any(group not in allowed for group, allowed in zip(assignment, choices)): return None
        mapping = dict(zip([x["id"] for x in items], assignment))
        totals = {g: {key: sum(item.get("features", {}).get(key, 0) for item, group in zip(items, assignment) if group == g) for key in weights} for g in groups}
        if any(not math.isfinite(v) for values in totals.values() for v in values.values()):raise ValueError("累计特征超出有限数值范围")
        differences = {key: max(totals[g][key] for g in groups) - min(totals[g][key] for g in groups) for key in weights}
        collisions = sum(mapping[a] == mapping[b] for a, b in conflicts)
        score = sum(weights[k] * v for k, v in differences.items()) + collisions * conflict_penalty
        if not math.isfinite(score):raise ValueError("加权评分超出有限数值范围")
        result = {"assignment": mapping, "score": score, "totals": totals, "differences": differences, "conflicts": collisions}
        if best is None or score < best["score"]: best = result
        return result
    if method == "local":
        import random
        rng = random.Random(seed)
        for _ in range(restarts):
            if examined >= budget: break
            assignment = [rng.choice(allowed) for allowed in choices]
            current = evaluate(assignment)
            improved = True
            while improved and examined < budget:
                improved = False
                for index, allowed in enumerate(choices):
                    for group in allowed:
                        if group == assignment[index]: continue
                        if examined >= budget: break
                        trial = assignment.copy(); trial[index] = group
                        candidate = evaluate(trial)
                        if candidate is not None and candidate["score"] < current["score"]:
                            assignment, current = trial, candidate
                            improved = True
                    if examined >= budget: break
        return {"status": "budget_exhausted" if examined >= budget else "heuristic_complete", "result": best,
                "examined": examined, "optimal": False, "method": "local", "seed": seed}
    for assignment in product(groups, repeat=len(items)):
        if examined >= budget: break
        evaluate(assignment)
    return {"status": "budget_exhausted" if examined < len(groups)**len(items) else "complete" if best else "infeasible", "result": best, "examined": examined, "optimal": examined == len(groups)**len(items)}


def duration_margin(intervals: list[dict], limit_minutes: int) -> dict:
    """校验时间链并按显式限值计算余量，不包含行业法规或默认阈值。"""
    if type(limit_minutes) is not int or limit_minutes < 0: raise ValueError("限值必须为非负整数")
    parsed = [interval(x) for x in intervals]
    if parsed != sorted(parsed): raise ValueError("时间链未排序")
    if any(right[0] < left[1] for left, right in zip(parsed, parsed[1:])): raise ValueError("时间链重叠")
    total = sum((end - start).total_seconds() for start, end in parsed) / 60
    return {"total_minutes": total, "limit_minutes": limit_minutes, "margin_minutes": limit_minutes - total,
            "exceeded": total > limit_minutes, "status": "available" if parsed else "missing"}


def contiguous_days(days: list[str]) -> list[list[str]]:
    """合并连续值班日，缺口不跨越。"""
    ordered = sorted({date.fromisoformat(x) for x in days}); groups: list[list[str]] = []
    for day in ordered:
        if groups and date.fromisoformat(groups[-1][-1]) + timedelta(days=1) == day: groups[-1].append(day.isoformat())
        else: groups.append([day.isoformat()])
    return groups


def export_csv(assignments: list[dict]) -> str:
    """输出中性可编辑表格，不读取公司模板。"""
    stream = io.StringIO(); writer = csv.DictWriter(stream, fieldnames=["person", "slot"]); writer.writeheader()
    for row in assignments:
        writer.writerow({key: "'" + str(row[key]) if str(row[key]).startswith(("=", "+", "-", "@", "\t", "\r")) else row[key] for key in ("person", "slot")})
    return stream.getvalue()


def export_xlsx(assignments: list[dict], output: str) -> dict:
    """生成中性排班Excel，不复制原模板或人员。"""
    from openpyxl import Workbook
    from pathlib import Path
    workbook = Workbook(); worksheet = workbook.active; worksheet.title = "排班"
    worksheet.append(["person", "slot"])
    for row in assignments:
        values = [str(row[key]) for key in ("person", "slot")]
        worksheet.append(["'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value for value in values])
    worksheet.freeze_panes = "A2"; worksheet.auto_filter.ref = worksheet.dimensions
    workbook.save(output); workbook.close()
    return {"output": Path(output).name, "rows": len(assignments)}
