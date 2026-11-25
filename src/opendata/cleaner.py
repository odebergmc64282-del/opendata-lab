"""Open-Meteo 原始 JSON 的清洗模块（成员 B）。

对外唯一契约接口：

    clean_forecast(raw: dict, city_code: str) -> list[dict]

输入  A 交给 B 的原始 dict（见契约 2.4 节）
输出  六字段标准化记录组成的 list[dict]（见契约 2.2 节），按 forecast_date 升序
"""

from __future__ import annotations

import logging
import math
import re
from datetime import UTC, datetime

from opendata.config import CITY_CONFIG

logger = logging.getLogger(__name__)

# 四个每日数组必须同时存在，且长度一致（契约 3.2 节清洗细则 1）
DAILY_KEYS = (
    "time",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
)

# 严格 YYYY-MM-DD：先正则卡格式，再交给 datetime 判断日期是否真实存在
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")

# 哨兵对象：区分“合法的 None（未知值）”与“非法值（该行必须剔除）”
_INVALID = object()


def clean_forecast(raw: dict, city_code: str) -> list[dict]:
    """把 Open-Meteo 原始 JSON 清洗成标准化的天气记录列表。

    Args:
        raw: Open-Meteo /v1/forecast 返回的 JSON 字典，至少含 daily 对象。
        city_code: config.py 中的城市编码，必须是小写英文编码（如 ``guangzhou``）。

    Returns:
        list[dict]，每条记录含 city_code / forecast_date / temp_max_c /
        temp_min_c / precipitation_mm / fetched_at 六个字段，按 forecast_date 升序。
        同一 (city_code, forecast_date) 只保留最后一条有效记录。

    Raises:
        ValueError: 城市非法、raw 结构不合法、四个每日数组缺失/非列表/长度不一致、
            或过滤后没有任何有效行。
    """
    daily = _validate_input(raw, city_code)

    arrays = _extract_arrays(daily)
    fetched_at = _utc_now()  # 同一次清洗的所有记录共用一个时间戳

    # 以日期为键暂存，后写入者覆盖先写入者 —— 天然实现“同一日期保留最后一条有效记录”
    valid_by_date: dict[str, dict] = {}

    for index, date_value in enumerate(arrays["time"]):
        record, reason = _build_record(arrays, index, city_code, fetched_at)
        if record is None:
            logger.warning(
                "丢弃第 %s 条数据（日期原值=%r）：%s", index, date_value, reason
            )
            continue
        valid_by_date[record["forecast_date"]] = record

    if not valid_by_date:
        raise ValueError(
            f"{city_code} 的原始数据全部无效，没有可输出的记录"
        )

    return [valid_by_date[key] for key in sorted(valid_by_date)]


# --------------------------------------------------------------------------- #
# 内部辅助函数（契约允许自由定义，但不得改变对外的六个字段与行为）
# --------------------------------------------------------------------------- #


def _validate_input(raw: dict, city_code: str) -> dict:
    """校验 city_code 与 raw 的顶层结构，返回 daily 子字典。"""
    if not isinstance(city_code, str) or city_code not in CITY_CONFIG:
        raise ValueError(f"未配置的城市编码：{city_code!r}")

    if not isinstance(raw, dict):
        # 契约 3.2 节明确要求结构错误抛 ValueError，故不采用 TypeError
        raise ValueError(f"raw 必须是 dict，收到 {type(raw).__name__}")  # noqa: TRY004

    daily = raw.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("raw 缺少 daily 对象，或 daily 不是 dict")  # noqa: TRY004

    return daily


def _extract_arrays(daily: dict) -> dict[str, list]:
    """校验四个每日数组都存在、都是列表、且长度一致，返回它们。"""
    missing = [key for key in DAILY_KEYS if key not in daily]
    if missing:
        raise ValueError(f"daily 缺少数组：{missing}")

    arrays = {}
    for key in DAILY_KEYS:
        value = daily[key]
        if not isinstance(value, list):
            raise ValueError(  # noqa: TRY004 - 契约要求 ValueError
                f"daily.{key} 必须是 list，收到 {type(value).__name__}"
            )
        arrays[key] = value

    lengths = {key: len(value) for key, value in arrays.items()}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"daily 各数组长度不一致：{lengths}")

    return arrays


def _build_record(
    arrays: dict[str, list],
    index: int,
    city_code: str,
    fetched_at: str,
) -> tuple[dict | None, str]:
    """按索引拼装一条记录。返回 (记录, "") 或 (None, 丢弃原因)。"""
    raw_date = arrays["time"][index]
    forecast_date = _parse_date(raw_date)
    if forecast_date is None:
        return None, "日期格式非法或日期不存在"

    temp_max = _parse_number(arrays["temperature_2m_max"][index])
    if temp_max is _INVALID:
        return None, "temperature_2m_max 不是有效数字"

    temp_min = _parse_number(arrays["temperature_2m_min"][index])
    if temp_min is _INVALID:
        return None, "temperature_2m_min 不是有效数字"

    precipitation = _parse_number(arrays["precipitation_sum"][index])
    if precipitation is _INVALID:
        return None, "precipitation_sum 不是有效数字"

    if precipitation is not None and precipitation < 0:
        return None, f"降水量为负：{precipitation}"

    if temp_max is not None and temp_min is not None and temp_max < temp_min:
        return None, f"最高温 {temp_max} 小于最低温 {temp_min}"

    return (
        {
            "city_code": city_code,
            "forecast_date": forecast_date,
            "temp_max_c": temp_max,          # None 原样保留，不插值、不补 0
            "temp_min_c": temp_min,
            "precipitation_mm": precipitation,
            "fetched_at": fetched_at,
        },
        "",
    )


def _parse_date(value: object) -> str | None:
    """把日期值校验成严格的 ``YYYY-MM-DD`` 字符串，非法返回 None。"""
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not _DATE_PATTERN.fullmatch(text):
        return None

    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:  # 格式对但日期不存在，如 2026-02-30
        return None
    return text


def _parse_number(value: object) -> float | None | object:
    """转换数值字段。

    返回 float 表示合法数值；返回 None 表示“未知值（原样保留）”；
    返回 _INVALID 哨兵表示该行无效、必须剔除。
    """
    if value is None:
        return None                # 未知值：保留 None，绝不补 0
    if isinstance(value, bool):    # bool 是 int 的子类，必须先挡掉
        return _INVALID
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return _INVALID
    else:
        return _INVALID

    if not math.isfinite(number):  # NaN、inf、-inf 一律视为损坏数据
        return _INVALID
    return number


def _utc_now() -> str:
    """当前 UTC 时间，ISO 8601、秒精度、以 Z 结尾。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
