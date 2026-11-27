# OpenData Lab 1.0 — 接口契约规范（v1.0.0 待签署）

> 文档编号：OD-CONTRACT-001  
> 版本：**v1.0.0**  
> 制定日期：2026-10-28  
> 状态：**待四人确认后冻结**  
> 适用范围：OpenData Lab 1.0，四人团队 A / B / C / D  
> 关联文件：《OpenData Lab 1.0 四人协作开发任务书》及[团队开发规范（`docs/02_TEAM_DEVELOPMENT_STANDARD.md`）](02_TEAM_DEVELOPMENT_STANDARD.md)
>
> **优先级：** 若本文件与旧任务书中的第 4 节、聊天中的教学示例有冲突，以本文件为准。
>
> 本次修订为待审提案。新增辅助接口、UPSERT 合并校验与配套验收待团队确认，确认后按第 7 节冻结。

## 0. 一句话约定

Open-Meteo JSON `dict` → 清洗后的 `list[dict]` → SQLite → 查询得到的 `list[dict]` → Streamlit。

**本项目 v1 不在模块之间传递 Pandas DataFrame。** B、D 等模块可在内部使用 Pandas。跨模块调用使用约定的 Python `dict`、`list[dict]` 或明确规定的辅助接口结果，字段中也不得出现 Pandas `Timestamp`、`NaN` 或 NumPy 标量。

## 1. 五个必须遵守的核心 Python 接口

```python
# src/opendata/collector.py — 成员 A
def fetch_forecast(city_code: str) -> dict: ...

# src/opendata/cleaner.py — 成员 B
def clean_forecast(raw: dict, city_code: str) -> list[dict]: ...

# src/opendata/repository.py — 成员 C
def save_forecast(records: list[dict]) -> int: ...
def query_forecast(
    city_codes: list[str],
    start_date: str,
    end_date: str,
) -> list[dict]: ...

# src/opendata/dashboard.py — 成员 D
def render_dashboard() -> None: ...
```

- 以上**函数名、参数名、参数顺序、参数类型、返回类型**在 v1.0.0 冻结，不得个人擅自修改。
- 核心接口属于 **Python 函数之间的调用约定**，不是自己搭建的 HTTP 接口；仅 A 访问外部 Open-Meteo HTTP API。
- 允许成员自由定义内部辅助函数。内部函数不得改变上述契约的对外行为。
- `list[dict]` 意为 Python 字典组成的列表。标准记录字典遵守第 2 节，原始 JSON 和分析结果各遵守对应接口约定。

## 2. 统一配置与数据结构

### 2.1 城市编码（由 `config.py` 维护）

第一版固定三个城市，不使用中文城市名作为跨模块主键：

| `city_code` | 显示名 | 纬度 | 经度 | 预报时区 |
|---|---|---:|---:|---|
| `guangzhou` | 广州 | 23.1291 | 113.2644 | `Asia/Shanghai` |
| `beijing` | 北京 | 39.9042 | 116.4074 | `Asia/Shanghai` |
| `shanghai` | 上海 | 31.2304 | 121.4737 | `Asia/Shanghai` |

- C 负责 `src/opendata/config.py` 的初始建设与协调维护。三个城市只定义在公共 `CITY_CONFIG` 中，按 `city_code` 索引。每项含 `name`（`str`）、`latitude`（`float`）、`longitude`（`float`）和 `timezone`（`str`）。其他模块通过 import 使用。公共配置变更先在 Issue 通知团队，再提交审查。
- `city_code` **严格匹配小写编码**，如 `guangzhou`；输入 `广州`、`Guangzhou`、空串或未知值，视为非法参数并抛 `ValueError`。
- UI 使用中文显示名，但传递的值必须为英文 `city_code`。

### 2.2 标准化天气记录（B 输出、C 输入/输出、D 读取）

标准记录对外包含以下六个字段。B 的清洗输出和 C 的查询结果固定为这六个字段。C 写入要求至少具备六字段，只处理约定字段，忽略额外键。扩展对外字段须遵循第 7 节。

| 字段 | Python 类型 | 示例 | 规则 |
|---|---|---|---|
| `city_code` | `str` | `guangzhou` | 必须在配置内 |
| `forecast_date` | `str` | `2026-10-28` | 严格 `YYYY-MM-DD`，真实有效日期 |
| `temp_max_c` | `float \| None` | `28.5` | 摄氏度；未知为 `None` |
| `temp_min_c` | `float \| None` | `21.3` | 摄氏度；未知为 `None` |
| `precipitation_mm` | `float \| None` | `2.5` | 毫米，非负；未知为 `None`，**不可补 0** |
| `fetched_at` | `str` | `2026-10-28T08:30:00Z` | UTC、ISO 8601、秒精度、以 `Z` 结尾 |

**字段恒定语义：**

1. `forecast_date` 表示对应城市的**预报当地日历日期**（本项目预设三城均用 `Asia/Shanghai`）；它不是请求发送时刻，也不是 UTC 日期。
2. `fetched_at` 是 B 清洗时生成的 UTC 处理时间，同一次 `clean_forecast()` 输出统一使用 `YYYY-MM-DDTHH:MM:SSZ`。它不代表 HTTP 请求时刻、实测时刻或单项指标的更新时间。
3. `temp_max_c` 与 `temp_min_c` 均非空时，必须满足 `temp_max_c >= temp_min_c`。
4. `None` 是未知值，不意味着零摄氏度或零降水量；负降水无效。
5. 已知数值输出为有限的 Python `float`，日期和时间输出统一为 `str`。
6. `city_code + forecast_date` 是一条记录的业务唯一键。

**标准记录示例：**

```python
{
    "city_code": "guangzhou",
    "forecast_date": "2026-10-28",
    "temp_max_c": 28.5,
    "temp_min_c": 21.3,
    "precipitation_mm": 2.5,
    "fetched_at": "2026-10-28T08:30:00Z",
}
```

### 2.3 外部 Open-Meteo API 字段映射

使用 `GET https://api.open-meteo.com/v1/forecast`，推荐参数：

```text
latitude=<城市纬度>
longitude=<城市经度>
daily=temperature_2m_max,temperature_2m_min,precipitation_sum
timezone=Asia/Shanghai
forecast_days=7
temperature_unit=celsius
precipitation_unit=mm
```

Open-Meteo `daily` 中的数组一一对应：

| API JSON 路径 | 标准记录字段 |
|---|---|
| `daily.time[i]` | `forecast_date` |
| `daily.temperature_2m_max[i]` | `temp_max_c` |
| `daily.temperature_2m_min[i]` | `temp_min_c` |
| `daily.precipitation_sum[i]` | `precipitation_mm` |

`city_code` 取自函数参数；`fetched_at` 由 B 按 UTC 时钟一次性生成。A 保证请求使用摄氏度、毫米和配置中的预报时区，再将原始 JSON 交给 B 清洗。B 按这一输入约定解释数据，v1 无需强制校验 `daily_units`。以上字段及单位参考 Open-Meteo 官方文档：<https://open-meteo.com/en/docs>。

### 2.4 原始样本（A → B）

```python
raw = {
    "timezone": "Asia/Shanghai",
    "daily": {
        "time": ["2026-10-28", "2026-10-29"],
        "temperature_2m_max": [28.5, 27.0],
        "temperature_2m_min": [21.3, None],
        "precipitation_sum": [2.5, 0.0],
    },
}
```

本示例只有 2 天，用于测试；正式接口请求 7 天预报，并**不保证 API 在任何异常情形下总会返回恰好 7 条**。

## 3. 各接口详细契约

### 3.1 A — `fetch_forecast(city_code: str) -> dict`

**职责：** 检查 `city_code` → 从 `config.py` 获取经纬度 → 使用 Requests 获取 JSON → 检查基本响应形状 → 返回原始 JSON 对象。

**前置条件：** `city_code` 为第 2.1 节的合法城市编码。

**成功返回：** Python `dict`；至少有 `daily` 对象；不进行 Pandas 清洗、不写数据库、不返回 `list[dict]`。

**失败行为：**

- 城市非法：抛 `ValueError`。
- 超时、连接失败、HTTP 非成功状态码：抛 `requests.exceptions.RequestException` 或其子类（包括 `Timeout`、`HTTPError`）。
- JSON 无法解析、顶层不是 `dict`、`daily` 不存在或不是 `dict`：抛 `ValueError`。
- 失败时不返回伪造数据，不写数据库。HTTP 调用必须配置超时，推荐 `timeout=(3, 10)` 秒。

**最小测试：** 合法城市和正常响应；未知城市；HTTP 超时；HTTP 500；JSON 缺少 `daily`。**测试使用 mock，不能依赖真实网络。**

### 3.2 B — `clean_forecast(raw: dict, city_code: str) -> list[dict]`

**职责：** 对 Open-Meteo JSON 的每日数组做格式检查、按索引展开、类型转换、异常行处理、去重、排序、字段标准化。

**前置条件：** `raw` 是 `dict`；`city_code` 合法。

**成功返回：** `list[dict]`，每个字典遵循第 2.2 节的六字段结构；按 `forecast_date` 升序排列；同一城市/日期仅保留最后一条有效记录。

**数据清洗细则：**

1. `daily.time`、`daily.temperature_2m_max`、`daily.temperature_2m_min`、`daily.precipitation_sum` 缺任意一个、不是列表、或长度不一致：**整批抛 `ValueError`**，不产生半截输出。
2. 合法数字（`int` / `float`，不接受 `bool`），以及可以解析的数字字符串（如 `"28.5"`）均转换为 `float`；`None` 原样保留；`NaN`、无穷大、不可转换字符串视为**无效数据行并剔除**，记录 warning 日志。
3. 不合法日期、负降水、已知最高温小于已知最低温：剔除该行，记录 warning 日志。
4. 任意气温/降水字段为 `None`：**保留该行与 `None`**，不擅自插值或补 0。
5. 过滤后无有效行（包括 `time` 为空）：抛 `ValueError`，不默默返回成功。
6. 输出每个记录的 `fetched_at` 使用同一个 UTC 时间戳，格式固定为 `YYYY-MM-DDTHH:MM:SSZ`。

**最小测试：** 正常展开、`None` 保留、数组长度不一致、非法日期、负降水、全部无效、重复日期去重、输出按日期排序。

### 3.3 C — `save_forecast(records: list[dict]) -> int`

**职责：** 校验已清洗的数据，将记录原子性地写入 SQLite，重复业务键执行 UPSERT。

**前置条件：** `records` 是 `list[dict]`，每条具备六字段且类型正确；同批不允许重复 `(city_code, forecast_date)`；除允许的 `None` 外，数据必须有效。

**成功返回：** 本批**成功处理的记录数**，定义为 `len(records)`，包含新增、更新以及内容完全相同但成功处理的记录；不等于 SQLite `rowcount` 变化数。

**特殊情况：** `save_forecast([])` 返回 `0`，不改变数据库。

**数据库规则：**

- 表名 `weather_daily`；复合主键 `PRIMARY KEY(city_code, forecast_date)`。
- 每次调用在**一个事务内**完成；任何记录校验失败或 SQL 失败都不能留下部分写入。
- 数值为 `None` 时，**不得覆盖数据库中此前已有的非空有效数值**。数据库 NULL 对应 Python `None`。
- `fetched_at` 使用本批传入的 UTC 处理时间，记录该业务键最近一次成功处理。某个指标沿用旧值时，时间戳仍按成功处理更新。
- C 在同一写事务内读取实际旧值，按 UPSERT 规则合成并校验最终记录，再写入。同批有任一最终记录的已知最高温低于已知最低温时，抛 `ValueError` 并回滚整批。例：旧记录最高温 28、最低温 21，新记录最高温 18、最低温 `None`，合并结果 18/21 不合法。
- 事务必须阻止并发写入在读取旧值与写入之间改变校验依据，例如在读旧值前使用 `BEGIN IMMEDIATE`。
- SQL 必须使用参数占位符，禁止字符串拼接用户输入。

**建议 DDL：**

```sql
CREATE TABLE IF NOT EXISTS weather_daily (
    city_code TEXT NOT NULL,
    forecast_date TEXT NOT NULL,
    temp_max_c REAL,
    temp_min_c REAL,
    precipitation_mm REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (city_code, forecast_date)
);
```

**UPSERT 更新语义（示例）：** 以下 SQL 仅展示字段更新。执行前仍须在同一写事务内校验最终记录。

```sql
INSERT INTO weather_daily (
    city_code, forecast_date, temp_max_c,
    temp_min_c, precipitation_mm, fetched_at
) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(city_code, forecast_date) DO UPDATE SET
    temp_max_c = COALESCE(excluded.temp_max_c, weather_daily.temp_max_c),
    temp_min_c = COALESCE(excluded.temp_min_c, weather_daily.temp_min_c),
    precipitation_mm = COALESCE(excluded.precipitation_mm, weather_daily.precipitation_mm),
    fetched_at = excluded.fetched_at;
```

**失败行为：** 输入字段、类型、日期、重复键或最终合并后的温度关系错误 → `ValueError`；数据库连接或执行故障 → `sqlite3.Error` 或其子类，并回滚；失败时不改变已经保存的数据。

**最小测试：** 首次插入、重复 UPSERT、`None` 不覆盖旧值、空列表、无效字段回滚、重复输入拒绝、事务失败回滚，以及第 6 节 RC-01～RC-04 的合并校验。

### 3.4 C — `query_forecast(city_codes: list[str], start_date: str, end_date: str) -> list[dict]`

**职责：** 按一个或多个城市和日期范围查询数据，按统一字段返回供 D 使用。

**前置条件：** `city_codes` 是**非空列表**，元素均为合法 `city_code`；`start_date` 与 `end_date` 均为严格 `YYYY-MM-DD`，且 `start_date <= end_date`。

**成功返回：** `list[dict]`；每行固定返回第 2.2 节的六字段；按 `city_code` 升序、`forecast_date` 升序排序；开始和结束日期**均包含**。查询到零条数据时返回 `[]`，不抛错。

**失败行为：** 无效城市列表、非法日期、起始日大于结束日 → `ValueError`；数据库故障 → `sqlite3.Error`。

**示例：**

```python
rows = query_forecast(
    ["guangzhou", "beijing"],
    "2026-10-28",
    "2026-11-03",
)
# rows: list[dict]，允许为空
```

**最小测试：** 单城市、多城市、闭区间端点、空结果、排序、非法城市、反向日期范围。

### 3.5 D — `render_dashboard() -> None`

**职责：** 渲染 Streamlit 页面，使用城市配置展示中文名；调用 C 的查询接口，使用 B 的分析辅助接口处理查询结果，展示最高/最低温、降水、处理时间及 CSV 下载。

**前置条件：** 已初始化应用环境；SQLite 可以不存在但应能够按设计初始化空库。允许数据库中当前无天气数据。

**成功行为：** 无返回值（`None`）；页面可以展示空状态，网络异常时提示原因并保留已缓存的旧数据；日期/城市筛选传给 `query_forecast()`。

**交互约定：**

- 页面支持 3 座预设城市；可以单城查看，允许多城比较。
- 城市显示名映射来自 `config.py`；内部传 `city_code`。
- D 可在展示模块内部将标准记录转换为 Pandas DataFrame 供图表使用。上游输入仍是契约约定的 Python 类型。
- 可把 `forecast_date` 内部转换为日期轴；CSV 输出应有一致字段名，`None` 为空单元格。
- 将 `fetched_at` 显示为最近处理或更新时间，并注明这是**预报数据**。展示降水统计时注明已知降水覆盖天数，区分未知与真实零。
- 手动刷新复用第 4.1 节的入口。捕获预期异常并显示友好提示，保留已有数据，避免向用户显示完整栈追踪。

**最小测试：** 使用 mock 的 `query_forecast` 模拟有数据/无数据/异常三种情况；验证图表输入不破坏字段约定。

## 4. 主流程与公共辅助接口（拟议）

以下两个公共辅助接口供 v1 集成使用，五个核心接口仍见第 1 节。`app.py` 只负责调用 `render_dashboard()`。

### 4.1 C — `refresh_city(city_code: str) -> int`

由 C 在 `src/opendata/pipeline.py` 实现，A 的 `scripts/refresh.py` 与 D 的手动刷新共同调用。A 和 D 通过此入口刷新城市，避免重复编排或访问 C 的私有函数。

```python
raw = fetch_forecast(city_code)
records = clean_forecast(raw, city_code)
count = save_forecast(records)
```

按上述顺序执行，返回 `save_forecast()` 成功处理的条数。原样传播 `ValueError`、`requests.exceptions.RequestException` 或 `sqlite3.Error`（含子类），失败时不给出成功计数。采集或清洗失败时跳过保存，保存失败按第 3.3 节回滚。原子性限于单城此次写入，多城调度可有部分城市成功。

### 4.2 B — `summarize_forecast(records: list[dict]) -> dict`

由 B 在 `src/opendata/analytics.py` 实现，供 D 在取得 C 的查询结果后调用。仅处理传入的标准记录，不读写数据库、不联网、不渲染页面、不修改输入。

- 接受单城、多城及空列表。每条记录须符合第 2.2 节，包括六字段、配置内城市、真实日期、UTC 时间格式、有限数值及字段约束。业务键须唯一。输入无效时抛 `ValueError`，不重新清洗或静默去重。
- 返回 `{"by_city": {...}}`，每个城市独立聚合，城市键按编码升序生成。空列表返回 `{"by_city": {}}`。
- 每项统计只使用对应指标的非 `None` 值。全缺失时相关温度、累计降水和降雨日返回 `None`。真实零降水计入已知降水天数。累计值只覆盖有值日期。输出保留数值类型，由 D 格式化。

| 每城字段 | 类型 | 定义 |
|---|---|---|
| `record_count` | `int` | 有效标准记录条数 |
| `mean_temp_max_c` | `float \| None` | 已知最高温的平均值（°C） |
| `mean_temp_min_c` | `float \| None` | 已知最低温的平均值（°C） |
| `max_temp_c` | `float \| None` | 已知最高温的最大值（°C） |
| `min_temp_c` | `float \| None` | 已知最低温的最小值（°C） |
| `total_precipitation_mm` | `float \| None` | 已知降水量之和（mm） |
| `rainy_day_count` | `int \| None` | 已知降水量大于零的日期数 |
| `known_precipitation_days` | `int` | 降水量已知的日期数 |

第 2.4 节的样本以 `guangzhou` 清洗后，分析结果如下。

```python
{
    "by_city": {
        "guangzhou": {
            "record_count": 2,
            "mean_temp_max_c": 27.75,
            "mean_temp_min_c": 21.3,
            "max_temp_c": 28.5,
            "min_temp_c": 21.3,
            "total_precipitation_mm": 2.5,
            "rainy_day_count": 1,
            "known_precipitation_days": 2,
        },
    },
}
```

### 4.3 模块依赖

`pipeline` 可导入 `collector`、`cleaner` 和 `repository`。`dashboard` 可导入 `repository`、`pipeline` 和 `analytics`。`analytics` 可使用公共配置，不依赖 `repository`、`dashboard` 或 `pipeline`。`collector` 不得导入 `cleaner`、`repository` 或 `dashboard`，`cleaner` 不得导入 `repository` 或 `dashboard`，`repository` 不得导入 `dashboard`。禁止循环依赖。

## 5. 异常与边界情况矩阵

| 情形 | 发生层 | 对外行为 | 是否更改数据库 |
|---|---|---|---|
| 未配置城市 | A / B / C 查询 | `ValueError` | 否 |
| 网络断开 / 超时 / HTTP 500 | A | `requests.exceptions.RequestException` | 否 |
| JSON 无 `daily` | A | `ValueError` | 否 |
| `daily` 数组长度不一 | B | `ValueError` | 否 |
| 单行日期非法、负降水或数值损坏 | B | 丢弃该行，记录 warning | 只写其他合法行 |
| 气温/降水为 `None` | B → C | 保留 `None`，UPSERT 不覆盖原非空值 | 允许入库 |
| 所有行均无效 | B | `ValueError` | 否 |
| 同批记录重复（未经清洗） | C | `ValueError` | 否 |
| UPSERT 合并后的已知最高温低于最低温 | C | `ValueError`、整批回滚 | 否 |
| 分析输入无效或业务键重复 | B 的辅助接口 | `ValueError` | 否 |
| 刷新流程失败 | C 的辅助接口 | 原样传播失败阶段的预期异常 | 否（本次单城刷新） |
| 数据库读写失败 | C | `sqlite3.Error`、回滚 | 否（本次事务） |
| 合法查询无匹配记录 | C | `[]` | 否 |
| 前端点击刷新失败 | D | 显示错误提示和旧数据 | 否 |

## 6. 契约测试与最小验收

每个主模块须提供 `tests/test_<module>.py`，使用 `pytest`；A 的 HTTP 请求使用 mock；C 的数据库测试使用 pytest 的 `tmp_path`，或连接生命周期适合的 `:memory:`。涉及多次独立连接时优先使用临时文件。**禁止测试写入真实工作数据库**。

**五个接口的最小强制用例：**

| 编号 | 测试目标 | 通过条件 |
|---|---|---|
| CT-01 | `fetch_forecast` 正常响应 | 返回 dict，有 daily |
| CT-02 | API 超时 | 抛 RequestException 子类 |
| CT-03 | 城市非法 | 抛 ValueError |
| CT-04 | `clean_forecast` 有效数组 | 返回标准 list[dict] |
| CT-05 | 部分值为 None | 保留 None，不改为 0 |
| CT-06 | 数组长度不匹配 | 抛 ValueError |
| CT-07 | 异常日期/负降水 | 无效行被剔除，合法行保留 |
| CT-08 | 全部无效 | 抛 ValueError |
| CT-09 | `save_forecast` 首次写入 | 返回输入条数，数据可查询 |
| CT-10 | 相同业务键再次写入 | 不出现重复行 |
| CT-11 | NULL 更新 | 旧的非空气温/降水保持不变 |
| CT-12 | 事务内有无效记录 | 本次全部回滚 |
| CT-13 | `query_forecast` 多城市 | 按城市、日期有序 |
| CT-14 | 日期区间端点 | 两个端点均包含 |
| CT-15 | 查询为空 | 返回 [] |
| CT-16 | 日期范围反向 | 抛 ValueError |
| CT-17 | D 无数据 | 可显示空状态 |
| CT-18 | D 有数据 | 正常生成数据表和图表 |
| CT-19 | D 查询异常 | 页面友好提示 |
| CT-20 | 全流程模拟联调 | A→B→C→D 数据字段完全一致 |

**新增辅助接口和回归验收（拟议）：**

| 编号 | 测试目标 | 通过条件 |
|---|---|---|
| AC-01 | 正常单城统计 | `tests/test_analytics.py` 对第 4.2 节示例逐项检查值和类型 |
| AC-02 | 缺失、真实零及全缺失 | 忽略 `None`。有零无雨时累计为 0.0、降雨日为 0。全缺失的指标返回 `None`，全缺失降水的已知天数为 0 |
| AC-03 | 空列表 | 返回 `{"by_city": {}}` |
| AC-04 | 多城统计 | 每城独立聚合，城市键按编码升序 |
| AC-05 | 非法输入及输入不变 | 非列表、缺字段、非法城市/日期/时间、非法数值或重复键抛 `ValueError`。成功或失败均保持输入不变 |
| PC-01 | 正常刷新 | `tests/test_pipeline.py` 用 mock 验证参数、采集→清洗→保存顺序及计数 |
| PC-02 | 采集或清洗失败 | 分别模拟两阶段的失败，原样传播异常，均不调用保存 |
| PC-03 | 保存失败 | 模拟保存抛出 `ValueError` 或 `sqlite3.Error`，原样传播 |
| RC-01 | 更新最高温冲突 | 旧 28/21，新 18/`None`，抛 `ValueError` |
| RC-02 | 更新最低温冲突 | 旧 28/21，新 `None`/30，抛 `ValueError` |
| RC-03 | 合法部分更新 | 旧 28/21，新 29/`None`，结果为 29/21，更新处理时间，保留其他旧非空指标 |
| RC-04 | 冲突导致整批回滚 | 在有效更新、新增与温度冲突同批时，确认无新增，已存数据及处理时间保持原值 |

RC 用例放在 `tests/test_repository.py`。PC 不连接真实网络。最终发布须通过 CT-01～CT-20、AC-01～AC-05、PC-01～PC-03 和 RC-01～RC-04，并完成模拟联调。早期和单模块 PR 的门槛见[团队开发规范 §7](02_TEAM_DEVELOPMENT_STANDARD.md#7-测试规范)，初期 PR 的审查和引导期规则见[团队开发规范 §6.2](02_TEAM_DEVELOPMENT_STANDARD.md#62-pr-格式)。

## 7. 接口变更控制（必须遵守）

1. **提出变更：** 在 GitHub 创建 `contract-change` Issue，写明原因、原签名、新签名、对 A/B/C/D 的影响。
2. **影响评审：** 至少由受影响模块的负责人与 B（契约维护人）审核；对五个核心签名或字段的变更建议四人全部确认。
3. **文档先行：** 先提出契约修订供审查。实现可与文档同 PR，或在契约获确认后由后续 PR 同步实现、样例和测试。接口变化须有对应文档。
4. **版本规则：** 兼容性的说明修正升 PATCH；增加可选能力升 MINOR；删除/重命名字段或改变类型/返回值升 MAJOR。
5. **发布：** 合并到 `develop` 并通过 CI 后，再从 `develop` 合并到 `main`，发布标签。

本文件确认前可以提出修改；一旦四人在 GitHub Issue/PR 上确认 v1.0.0，其他模块即应以此为唯一对接依据。

## 8. 确认记录（在 GitHub PR 中填写）

| 角色 | 审核人 | 确认内容 | 状态 |
|---|---|---|---|
| A / 采集 | 待填 | 输入城市、外部 API、异常类型、原始 JSON | 待确认 |
| B / 清洗 | 待填 | 字段、清洗规则、缺失值和排序 | 待确认 |
| C / 数据库 | 待填 | 记录格式、查询语义、UPSERT、事务 | 待确认 |
| D / 前端 | 待填 | 查询入参、刷新动作、图表和空状态 | 待确认 |

**数据来源与政策：** Open-Meteo <https://open-meteo.com/en/docs>；GitHub 协作 <https://docs.github.com/en/pull-requests>。使用公开天气数据时应遵守服务条款并在 README / 页面注明来源。
