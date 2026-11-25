"""A → B 接口验收工具（成员 B 自用，不属于五个公开接口）。

两种用法：

    # 离线：A 把一次真实响应存成 JSON 文件，你用它验
    python tools/verify_a_output.py tests/fixtures/sample_response.json guangzhou

    # 联调：直接调用 A 的 fetch_forecast（需要 collector.py 已就位且联网）
    python tools/verify_a_output.py --live guangzhou
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opendata.cleaner import clean_forecast
from opendata.config import CITY_CONFIG

DAILY_KEYS = ("time", "temperature_2m_max", "temperature_2m_min", "precipitation_sum")


class _Collect(logging.Handler):
    """收集 clean_forecast 发出的 warning，便于汇总展示。"""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def describe_structure(raw: object) -> list[str]:
    """列出原始响应的结构事实，不判断对错。"""
    lines = [f"顶层类型：{type(raw).__name__}"]
    if not isinstance(raw, dict):
        return lines

    lines.append(f"顶层键：{sorted(raw)}")

    daily = raw.get("daily")
    if not isinstance(daily, dict):
        lines.append(f"daily 类型：{type(daily).__name__}（契约要求 dict）")
        return lines

    lines.append(f"daily 键：{sorted(daily)}")
    for key in DAILY_KEYS:
        value = daily.get(key, "缺失")
        if isinstance(value, list):
            lines.append(f"  daily.{key}: list，长度 {len(value)}")
        else:
            lines.append(f"  daily.{key}: {type(value).__name__}，值 {value!r}")
    return lines


def verify(raw: object, city_code: str) -> bool:
    print(f"== 城市：{city_code} 是否在配置内：{city_code in CITY_CONFIG} ==")
    print("== 原始结构 ==")
    for line in describe_structure(raw):
        print(line)

    collector = _Collect()
    logger = logging.getLogger("opendata.cleaner")
    logger.addHandler(collector)
    old_level = logger.level
    logger.setLevel(logging.WARNING)

    print("== 清洗结果 ==")
    try:
        records = clean_forecast(raw, city_code)  # type: ignore[arg-type]
    except ValueError as exc:
        print(f"FAIL 抛 ValueError：{exc}")
        return False
    finally:
        logger.removeHandler(collector)
        logger.setLevel(old_level)

    raw_count = len(raw["daily"]["time"]) if isinstance(raw, dict) and isinstance(raw.get("daily"), dict) else 0
    print(f"原始 {raw_count} 条 -> 输出 {len(records)} 条，丢弃 {len(collector.messages)} 条")
    for message in collector.messages:
        print(f"  WARNING {message}")

    print("== 首条输出 ==")
    print(json.dumps(records[0], ensure_ascii=False, indent=2))

    problems = []
    six_keys = {"city_code", "forecast_date", "temp_max_c", "temp_min_c",
                "precipitation_mm", "fetched_at"}
    for index, record in enumerate(records):
        if set(record) != six_keys:
            problems.append(f"第 {index} 条字段不匹配：{set(record) ^ six_keys}")
        if record["city_code"] != city_code:
            problems.append(f"第 {index} 条 city_code 错误")
        if not isinstance(record["temp_max_c"], float) and record["temp_max_c"] is not None:
            problems.append(f"第 {index} 条 temp_max_c 类型不是 float")
    dates = [r["forecast_date"] for r in records]
    if dates != sorted(dates):
        problems.append("输出未按 forecast_date 升序")

    print("== 结论 ==")
    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        return False
    print("PASS 六字段齐备、类型正确、排序正确")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="验收 A 的原始响应能否被 B 的 cleaner 吃下")
    parser.add_argument("path", nargs="?", help="A 导出的 JSON 文件路径")
    parser.add_argument("city_code", nargs="?", default="guangzhou", help="城市编码")
    parser.add_argument("--live", action="store_true", help="直接调用 collector.fetch_forecast")
    args = parser.parse_args()

    if args.live:
        from opendata.collector import fetch_forecast

        raw = fetch_forecast(args.city_code)
    else:
        if not args.path:
            parser.error("离线模式需要提供 JSON 文件路径")
        raw = json.loads(Path(args.path).read_text(encoding="utf-8"))

    return 0 if verify(raw, args.city_code) else 1


if __name__ == "__main__":
    raise SystemExit(main())
