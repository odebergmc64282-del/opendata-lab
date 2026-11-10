# OpenData Lab 1.0 — 四人团队开发与 GitHub 协作规范

> 文档编号：OD-STANDARD-001  
> 版本：v1.0.0  
> 日期：2026-10-28  
> 状态：待四人确认  
> **依赖：** `01_INTERFACE_CONTRACT.md`（接口行为以契约文件为准）

## 1. 规范的目标

本规范面向 **2 名基础较好 + 2 名初学者** 的 Python 四人团队。目标不是规定每个人如何写内部函数，而是确保四个人能在不同功能分支并行开发，稳定地集成、测试和交付同一个应用。

基础纪律：**小功能、小 PR、先定接口、必须测试、必须审查、不得直接改稳定分支。**

## 2. 人员职责与代码所有权

| 成员 | 主模块 | 负责文件 | 对其他成员的交付 |
|---|---|---|---|
| A（初学者） | 数据采集 | `collector.py`、`scripts/refresh.py`、`test_collector.py` | Open-Meteo 原始 JSON `dict` |
| B（有基础） | 数据清洗与分析 | `cleaner.py`、`analytics.py`、`test_cleaner.py`、CI | 6 字段 `list[dict]`，维护契约文档 |
| C（有基础） | 数据库与集成 | `repository.py`、`pipeline.py`、`test_repository.py` | 数据保存、条件查询与主流程集成 |
| D（初学者） | 可视化界面 | `dashboard.py`、`app.py`、`test_dashboard.py` | Streamlit 页面、图表和 CSV |

- **C** 负责项目首次初始化和主流程集成；**B** 负责协调接口变更；这不意味着 C 或 B 可不经审查直接改动其他人的代码。
- **每个人**至少交付一个 Python 主模块、一个测试文件、2 个 PR 和 1 次他人 PR Review。
- 审核轮换建议：B 审 A、C 审 B、D 审 C、A 审 D（复杂代码可增加第二位 reviewer）。
- 公共模块（`config.py`、`pyproject.toml`、`docs`、CI）修改前必须在 Issue 中通知所有人。

## 3. 仓库目录（标准 `src` 布局）

```text
opendata-lab/
├── app.py                     # D：Streamlit 启动入口
├── src/
│   └── opendata/
│       ├── __init__.py
│       ├── config.py           # 公共：城市配置、数据库路径
│       ├── collector.py        # A
│       ├── cleaner.py          # B
│       ├── analytics.py        # B
│       ├── repository.py       # C
│       ├── pipeline.py         # C
│       └── dashboard.py        # D
├── scripts/
│   └── refresh.py              # A：命令行调度入口
├── tests/
│   ├── fixtures/
│   │   └── sample_response.json
│   ├── test_collector.py
│   ├── test_cleaner.py
│   ├── test_repository.py
│   ├── test_dashboard.py
│   └── test_pipeline.py
├── docs/
│   ├── contracts.md            # 复制并维护正式接口契约
│   ├── development-standards.md # 复制并维护本文件
│   ├── architecture.md
│   └── windows-scheduler.md
├── .github/
│   ├── workflows/ci.yml
│   └── pull_request_template.md
├── data/                       # 数据库存储目录，数据库文件忽略
├── pyproject.toml
├── requirements.txt            # 若团队决定保留，须与 pyproject 依赖一致
├── .gitignore
└── README.md
```

**导入规则：** 使用标准包导入，如 `from opendata.collector import fetch_forecast`，不写 `from collector import ...`；仓库使用 `pyproject.toml` 配置 `src` 目录并执行可编辑安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

> `-e ".[dev]"` 要求 C 在初始化任务中提供有效 `pyproject.toml` 及 `dev` 可选依赖。如果暂时只准备了 `requirements.txt`，先安装 `pip install -r requirements.txt`，但需要确保 `src` 包能被正确导入。不要同时维护两套内容冲突的依赖文件。

## 4. Python 代码规范

**基础要求：**

1. Python 最低建议 3.12；四人保持一致的小版本范围及依赖锁定策略。
2. 统一 UTF-8；缩进 **4 空格**；文件名和函数名 `snake_case`；类名 `PascalCase`；常量 `UPPER_SNAKE_CASE`。
3. 五个对外接口必须写类型注解、docstring，保持接口契约中的参数和返回值不变。
4. 单个函数尽量只负责一件事；可分出校验、转换、日志等内部辅助函数。
5. 不允许使用裸 `except:`；捕获明确异常并记录必要上下文，无法恢复的异常重新抛出。
6. 公共函数不得使用 `print()` 代替错误处理；业务日志采用 `logging`，Streamlit 页面使用 `st.error()` 提示用户。
7. 所有数据库 SQL 使用参数化查询；不提交口令、Token、私密配置。
8. 不跨层直接访问其他人的内部私有函数（例如 `_validate_response`），依赖五个公开接口。
9. 不将数据库文件、缓存、虚拟环境、临时 CSV、日志或编辑器工作目录提交到 Git。
10. 每次提交前运行 `ruff check .` 与 `python -m pytest -q`。

**建议的公开函数文档格式：**

```python
def fetch_forecast(city_code: str) -> dict:
    """获取指定城市的每日天气预报原始响应。

    Args:
        city_code: config.py 中的城市编码。

    Returns:
        Open-Meteo 响应的 JSON 字典，至少包含 daily 对象。

    Raises:
        ValueError: 城市非法或响应结构无效。
        requests.exceptions.RequestException: 请求失败或超时。
    """
    ...
```

## 5. Git 分支与提交规范

```text
main                     # 已通过验收的稳定版本
  └── develop            # 日常集成分支
       ├── feature/OD-06-collector
       ├── feature/OD-07-cleaner
       ├── feature/OD-08-repository
       └── feature/OD-09-dashboard
```

**开发流程：**

```bash
git switch develop
git pull origin develop
git switch -c feature/OD-06-collector
# 编写代码与测试
git add .
git commit -m "feat(collector): add forecast request [OD-06]"
git push -u origin feature/OD-06-collector
```

然后在 GitHub 建立 **目标分支为 `develop`** 的 Pull Request；通过审查和 CI 才能合并。`main` 只接收测试通过的 `develop` 版本。推荐为 `main` 和 `develop` 配置分支保护（审核、状态检查、禁止 force push）。GitHub 规则可参考 <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches>。

**提交格式建议：** `type(scope): 简要说明 [OD-xx]`，常用 `type`：`feat`、`fix`、`test`、`docs`、`refactor`、`chore`。

例：

```text
feat(cleaner): normalize forecast records [OD-07]
fix(repository): preserve non-null values on upsert [OD-08]
test(collector): mock timeout response [OD-06]
docs(contract): clarify date interval [OD-02]
```

## 6. GitHub Issues 与 PR 模板规范

### 6.1 Issue 格式

```markdown
## 任务编号
OD-06

## 负责人
A

## 目标
实现 fetch_forecast(city_code) -> dict。

## 输入和输出
输入 guangzhou；输出原始 daily JSON。

## 验收标准
- [ ] 正常请求成功
- [ ] 城市非法抛 ValueError
- [ ] 网络超时和 HTTP 500 已覆盖测试

## 依赖
OD-01、OD-02
```

### 6.2 PR 格式

```markdown
## 关联 Issue
Closes #<实际 GitHub Issue 编号>

## 本次变更
- 

## 接口契约变化
- [ ] 无变化
- [ ] 有变化，已同步 contracts.md 和测试，并完成受影响成员评审

## 自测结果
- [ ] python -m pytest -q 通过
- [ ] ruff check . 通过
- [ ] 在本机手动验证核心流程

## 截图 / 日志（如涉及界面）

## Reviewer
@<其他成员账号>
```

`OD-06` 是团队任务编号，真实 GitHub Issue 可能是 `#12`、`#34` 等，不能将 OD 任务号误当成 GitHub Issue 编号。

**PR 合并条件：** 关联 Issue 明确、改动范围合理、至少一名他人 Review、自动化测试与 Ruff 通过、文档和接口样例同步、无机密数据和真实数据库文件。

## 7. 测试规范

### 7.1 测试层次

- **单元测试：** 每位成员对自己模块的正常、异常和边界条件负责；使用 `pytest`。
- **接口契约测试：** A/B/C/D 必须通过 `01_INTERFACE_CONTRACT.md` 的 CT-01～CT-20；改签名或字段必须更新相应测试。
- **集成测试：** C 负责 A→B→C 完整链路，D 与 C 共同验证 C→D 页面；CI 默认不联网。
- **人工演示：** 四人分别使用不同城市/日期筛选，测试刷新按钮、空数据、CSV 下载。

### 7.2 不得违反的测试规则

1. 网络请求用 mock/fixture，CI 测试不依赖公网 Open-Meteo。
2. SQLite 使用内存数据库或 `tmp_path`，不污染 `data/` 中的工作库。
3. 测试必须可重复，多次运行结果一致，不依赖运行顺序。
4. 测试断言行为，不只断言函数“没有报错”。
5. 错误场景也必须测到：超时、数据异常、空查询、重复 UPSERT。
6. 每个 PR 至少更新相关测试；纯文档 PR 可例外，但 CI 仍要通过。

### 7.3 CI 最小命令

```bash
python -m pytest -q
ruff check .
```

C 和 B 在第 1/2 周建立可运行 CI 入口；第 4 周完善为 PR 必过检查。至少 20 项契约测试通过是最终验收标准，而不是每人只写一个 `assert True`。

## 8. 每周检查与交付

| 周次 | 本周交付 | 最低检查点 |
|---|---|---|
| Week 1 | 工程骨架、契约和样本 | 四人能 clone、安装、运行最小项目；5 个接口签名冻结 |
| Week 2 | A/B/C/D 核心代码与测试 | 每人完成独立 PR，模块与模拟数据契约一致 |
| Week 3 | 主流程、查询筛选、图表 | 模拟数据联调通过；真实网络请求也已手动验证 |
| Week 4 | CLI、任务计划、CI、CSV、演示 | CT-01～CT-20 通过；4 人贡献证据齐全 |

**每周同步会 30 分钟：** 每人演示一个可运行结果，说清已完成、阻塞、下一步；所有阻塞在 Issue 留言，24 小时内应有人回应。

**完成定义（DoD）：** 不是“我写完了”，而是“代码已 push、测试通过、PR 经他人审核并合并、文档同步、在集成分支可运行”。

## 9. 契约变更与冲突处理

接口变化一律遵守 `01_INTERFACE_CONTRACT.md` 第 7 节的提案和审批流程。出现以下情况时应停止盲目合并：

- A 将返回值 `dict` 改成 `list[dict]`；
- B 将数据输出改成 `pd.DataFrame`，或改了字段名；
- C 修改 `query_forecast` 的参数顺序或结果排序；
- D 假定 `query_forecast` 返回 DataFrame；
- 两人同时修改 `config.py`，导致城市编码不一致。

**处理方法：** 保持 `develop` 为基准 → 在 Issue 明确冲突 → 修改契约及样例（若确需改约定）→ 由受影响模块负责人确认 → 修改代码和测试 → 重新发起 PR。

## 10. Windows 开发注意事项

- Windows 开发统一使用 PowerShell 或 VS Code 终端；Python 解释器必须指向项目的 `.venv`。
- README 中分别列出 Windows 命令，不混用 Linux 的 `source .venv/bin/activate`。
- 路径尽量使用 `pathlib.Path`，不要把某个成员机器上的 `C:\\Users\\...` 写死进代码。
- Windows 计划任务由 A 在第 4 周实现，依赖 C 的 `pipeline`；脚本应使用项目环境中的 Python 完整路径执行。
- `.gitignore` 至少包含：`.venv/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`.env`、`data/*.db`、`data/*.sqlite*`、`*.log`。

## 11. 四人启动确认清单

- [ ] 四人确认成员 A/B/C/D 的真实负责人。
- [ ] 项目统一选择 Python 3.12+；四人各自在本地成功安装依赖。
- [ ] `docs/contracts.md` 与本文件入库，并提交第一次审查 PR。
- [ ] B 给出统一原始样本和标准输出样例。
- [ ] C 配置 `src` 包导入、SQLite 路径及集成测试基础。
- [ ] A/D 在未完成真实模块时使用 fixture/mock 开发，不等待他人。
- [ ] GitHub 已启用 Issues、PR、`develop` 分支及基本自动化检查。

---

**适用原则：** 本文件规定团队工作方式；涉及字段、函数、异常、排序、数据写入行为时，统一引用正式接口契约 `01_INTERFACE_CONTRACT.md`，不在群聊中重复定义另一套接口。
