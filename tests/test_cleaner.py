"""clean_forecast 的单元测试与契约测试（成员 B）。"""

import re

import pytest

from opendata.cleaner import clean_forecast


def make_raw(
    time=("2026-10-28", "2026-10-29"),
    tmax=(28.5, 27.0),
    tmin=(21.3, None),
    precip=(2.5, 0.0),
):
    """构造契约 2.4 节的原始样本，各数组长度由 time 决定。"""
    return {
        "timezone": "Asia/Shanghai",
        "daily": {
            "time": list(time),
            "temperature_2m_max": list(tmax),
            "temperature_2m_min": list(tmin),
            "precipitation_sum": list(precip),
        },
    }


# CT-04 有效数组 -> 标准 list[dict]
def test_returns_standard_records():
    records = clean_forecast(make_raw(), "guangzhou")

    assert isinstance(records, list) and len(records) == 2
    assert set(records[0]) == {
        "city_code",
        "forecast_date",
        "temp_max_c",
        "temp_min_c",
        "precipitation_mm",
        "fetched_at",
    }
    assert records[0]["city_code"] == "guangzhou"
    assert records[0]["forecast_date"] == "2026-10-28"
    assert records[0]["temp_max_c"] == 28.5
    assert isinstance(records[0]["temp_max_c"], float)


# CT-05 部分值为 None -> 保留 None，不改成 0
def test_keeps_none_instead_of_zero():
    records = clean_forecast(make_raw(), "guangzhou")

    assert records[1]["temp_min_c"] is None
    assert records[1]["precipitation_mm"] == 0.0  # 真实的 0 与 None 必须区分开


# CT-06 数组长度不匹配 -> ValueError
@pytest.mark.parametrize(
    "broken_kwargs",
    [
        {"tmax": (28.5,)},
        {"tmin": (21.3, 20.0, 19.0)},
        {"precip": (2.5,)},
    ],
)
def test_length_mismatch_raises(broken_kwargs):
    with pytest.raises(ValueError):
        clean_forecast(make_raw(**broken_kwargs), "guangzhou")


# CT-07 非法日期 / 负降水 / 最高温小于最低温 -> 剔除该行、保留合法行
def test_drops_invalid_rows_and_keeps_valid_ones():
    raw = make_raw(
        time=("2026-10-28", "2026-10-30", "2026-10-31"),
        tmax=(28.5, 30.0, 20.0),
        tmin=(21.3, 22.0, 25.0),
        precip=(2.5, -1.0, 0.0),
    )
    records = clean_forecast(raw, "guangzhou")

    assert [r["forecast_date"] for r in records] == ["2026-10-28"]


def test_drops_impossible_calendar_date():
    raw = make_raw(time=("2026-02-30", "2026-10-29"), tmax=(1.0, 1.0), tmin=(0.0, 0.0))
    records = clean_forecast(raw, "guangzhou")

    assert [r["forecast_date"] for r in records] == ["2026-10-29"]


# CT-08 全部无效 -> ValueError
def test_all_invalid_raises():
    raw = make_raw(
        time=("2026-10-28", "2026-10-29"),
        tmax=(None, None),
        tmin=(None, None),
        precip=(-1.0, -2.0),
    )
    with pytest.raises(ValueError):
        clean_forecast(raw, "guangzhou")


def test_empty_time_raises():
    with pytest.raises(ValueError):
        clean_forecast(make_raw(time=(), tmax=(), tmin=(), precip=()), "guangzhou")


# 重复日期 -> 只保留最后一条，且按日期升序
def test_dedup_keeps_last_and_sorts_ascending():
    raw = make_raw(
        time=("2026-10-29", "2026-10-28", "2026-10-29"),
        tmax=(26.0, 28.5, 27.0),
        tmin=(20.0, 21.3, 19.0),
        precip=(1.0, 2.5, 0.0),
    )
    records = clean_forecast(raw, "shanghai")

    assert [r["forecast_date"] for r in records] == ["2026-10-28", "2026-10-29"]
    assert records[1]["temp_max_c"] == 27.0  # 后出现的那条覆盖了前一条


# fetched_at：UTC、ISO 8601、秒精度、以 Z 结尾，且同批一致
def test_fetched_at_is_utc_and_shared():
    records = clean_forecast(make_raw(), "beijing")

    pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
    assert all(pattern.fullmatch(r["fetched_at"]) for r in records)
    assert len({r["fetched_at"] for r in records}) == 1


# 数字字符串可解析、bool / NaN / inf / 普通文本判为无效行
def test_numeric_strings_are_converted():
    raw = make_raw(tmax=("28.5", "27"), tmin=("21.3", "20.0"), precip=("2.5", "0"))
    records = clean_forecast(raw, "guangzhou")

    assert records[0]["temp_max_c"] == 28.5
    assert records[1]["temp_max_c"] == 27.0


@pytest.mark.parametrize("bad_value", [True, "abc", "nan", "", float("nan"), float("inf")])
def test_bad_numeric_values_drop_row(bad_value):
    raw = make_raw(tmax=(bad_value, 27.0))
    records = clean_forecast(raw, "guangzhou")

    assert [r["forecast_date"] for r in records] == ["2026-10-29"]


# 城市与顶层结构校验
@pytest.mark.parametrize("bad_city", ["广州", "Guangzhou", "", "shenzhen", None])
def test_illegal_city_raises(bad_city):
    with pytest.raises(ValueError):
        clean_forecast(make_raw(), bad_city)


def test_missing_daily_raises():
    with pytest.raises(ValueError):
        clean_forecast({"timezone": "Asia/Shanghai"}, "guangzhou")


def test_daily_not_dict_raises():
    with pytest.raises(ValueError):
        clean_forecast({"daily": ["2026-10-28"]}, "guangzhou")


def test_missing_one_array_raises():
    raw = make_raw()
    del raw["daily"]["precipitation_sum"]
    with pytest.raises(ValueError):
        clean_forecast(raw, "guangzhou")


def test_array_not_list_raises():
    raw = make_raw()
    raw["daily"]["time"] = "2026-10-28"
    with pytest.raises(ValueError):
        clean_forecast(raw, "guangzhou")


def test_raw_not_dict_raises():
    with pytest.raises(ValueError):
        clean_forecast(None, "guangzhou")
