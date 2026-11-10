# opendata-lab

[中文](#中文) · [English](#english)

## 中文

OpenData Lab 是一个面向四人小组的 Python 学习项目。团队计划把公开天气预报做成一个可定期刷新的小应用，练习 API 请求、数据清洗、SQLite 读写、Streamlit 展示，以及通过 GitHub 分支和 Pull Request 协作。

首版计划使用 [Open-Meteo](https://open-meteo.com/en/docs) 的每日预报，覆盖广州、北京和上海，展示每日最高温、最低温和降水量。仓库目前处于初始化阶段，下文是开发计划。

### 数据流程

1. **采集** — 按城市请求 Open-Meteo API，获取原始 JSON，处理请求超时和异常响应。
2. **清洗** — 将原始数据整理为每个城市每天一条记录，统一日期和单位，校验数值并去重。缺失的降水量保留为空。
3. **存储** — 将清洗结果写入 SQLite 的 `weather_daily` 表，按城市和预报日期更新记录，并提供城市和日期范围查询。
4. **展示** — 在 Streamlit 页面按城市和日期筛选预报，查看气温与降水图表及最近更新时间。CSV 下载安排在收尾阶段。

### 四人分工

| 成员 | 负责模块 | 交付内容 |
| --- | --- | --- |
| A | 数据采集 | API 请求、原始 JSON 样本、定时刷新入口 |
| B | 数据清洗 | 字段校验、去重和标准化记录，与上下游确认记录格式 |
| C | SQLite 与集成 | 初始化数据库和表，编写批量写入与条件查询，串联采集、清洗和存储 |
| D | Streamlit 可视化 | 城市和日期筛选、气温与降水图表、空数据提示和 CSV 下载 |

### 开发阶段

1. **搭建项目** — 确定城市、共享字段和模块接口，准备一份 JSON 样本，方便四人并行开发。
2. **实现模块** — 各成员实现自己的模块并补齐测试。用模拟响应测试采集，用临时数据库测试 SQLite 读写。
3. **联调验证** — 跑通采集、清洗、入库、查询和展示，检查重复刷新、缺失值和空查询等情况。
4. **收尾演示** — 接入定时刷新和 CSV 下载，配置自动测试，补充运行说明并完成团队演示。

从 `develop` 创建功能分支，通过 Pull Request 审查后合入 `develop`。`main` 用于发布通过验收的版本。

## English

A collaborative Python project for automated weather data collection, cleaning, SQLite storage, and interactive visualization using Streamlit.

OpenData Lab is a learning project for four Python teammates. The team will practice API requests, data validation, database access, dashboard development, and collaboration through GitHub branches and pull requests.

The first version is planned around daily forecasts from [Open-Meteo](https://open-meteo.com/en/docs) for Guangzhou, Beijing, and Shanghai. It will show daily high and low temperatures and precipitation. The repository is in the setup phase, and the sections below describe the development plan.

### Data workflow

1. **Collect** — Request raw JSON from Open-Meteo for each city and handle timeouts and invalid responses.
2. **Clean** — Produce one record per city and forecast date. Standardize dates and units, validate values, and remove duplicates. Keep missing precipitation values empty.
3. **Store** — Save cleaned records in the SQLite `weather_daily` table, update them by city and forecast date, and support queries by city and date range.
4. **Visualize** — Use Streamlit to filter forecasts by city and date, plot temperature and precipitation, and show when the data was last refreshed. CSV export is planned for the final stage.

### Team roles

| Member | Area | Deliverables |
| --- | --- | --- |
| A | Data collection | API requests, a sample JSON response, and an entry point for scheduled refreshes |
| B | Data cleaning | Field validation, deduplication, and standardized records, with a shared record format agreed across modules |
| C | SQLite and integration | Database and table setup, batch writes, filtered queries, and integration of collection, cleaning, and storage |
| D | Streamlit visualization | City and date filters, temperature and precipitation charts, empty states, and CSV export |

### Development stages

1. **Set up the project** — Agree on the cities, shared fields, and module interfaces. Prepare a sample JSON response so each teammate can work independently.
2. **Build the modules** — Implement and test each module. Use mocked API responses for collection and a temporary database for SQLite tests.
3. **Integrate and verify** — Run the full workflow from collection to visualization. Check repeated refreshes, missing values, and empty query results.
4. **Prepare the demo** — Add scheduled refreshes and CSV export, configure automated tests, and document how to run the app.

Create feature branches from `develop` and open pull requests back into `develop` for review. Use `main` for releases that have passed acceptance checks.

## License

[MIT](LICENSE)
