# 约束排班与多特征分配

作者：Wangyuan · 2026-10-29

本项目源码采用 MIT 许可证，见 LICENSE；第三方依赖仍适用各自上游许可。

## 可用能力

- 显式班次、岗位资格、可用/不可用区间、每人班次数上限、连续天数与最短休息；资格稀缺班次优先、有界回溯排班。
- 意向班次影响候选顺序，硬约束始终生效；无解、预算耗尽和完整方案明确区分。
- 任意维度工作量、多组受限枚举分配、同组冲突惩罚、允许分组；输出目标分、维度差与冲突解释。
- 独立校验已有排班，按月/类别汇总及调用方配置折算，CSV/XLSX导出；时间链顺序/重叠检查、累计分钟与显式限值余量、连续日期合并。

## 运行

Python 3.11+。依赖仅为标准库，或 requirements.txt 明确列出的开源解析库。程序默认不联网；安装依赖时由包管理器下载。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -B cli.py demo
python3 -B cli.py demo --output demo-output
python3 -B cli.py run example.json --output demo-output
python3 -B -m unittest discover -s tests -v
```

演示数据从零生成；默认临时目录会在命令结束时释放。需要保留文件或数据库时必须指定 --output，输入与输出目录应由使用者自行控制。JSON输出到标准输出，参数错误返回非零状态。

## 输入与输出

动作：`schedule`、`validate`、`counts`、`allocate`、`margin`、`contiguous`、`export_xlsx`；库接口另提供 `export_csv`。每个动作参数名称对应核心文件中的同名函数/方法签名，公共接口有类型标注及中文说明。通用调用格式是 action 与 args；目录、收集模块另接受 tools/events/contract 等顶层显式合同。

```json
{
  "action": "margin",
  "args": {
    "intervals": [
      {
        "start": "2030-01-01T08:00:00+00:00",
        "end": "2030-01-01T12:00:00+00:00"
      }
    ],
    "limit_minutes": 300
  }
}
```

所有时间须有时区。排班是可行性搜索，不宣称最优；分配仅当 optimal=true 才说明遍历了当前声明的全部有限组合。预算耗尽须复核，不把部分排班当完整排班。连续天数与月度统计按班次开始日；跨日工作日计数需调用方先定义班次。

## 保留边界

原人员/资格/轮班序列、行业劳动与值勤限值、机队/机场特征、原Excel样式模板与Web页面不进入候选；改用显式通用参数和从零生成的CSV/XLSX。

只保留通用流程与算法；这是经过提取/重构的独立工具或组件集合，并不声称完整迁移原应用、原业务质量或生产验收。源码来源、哈希与原入口映射保存在本地私有审计台账，不随此目录分发。

## 验证

tests/仅使用合成数据与临时文件，覆盖主流程、空/缺失、身份冲突和关键异常；cli.py demo可独立复现完整示例。未运行真实业务数据、联网/正式发送、原系统回归或生产部署。本项目为CLI/库，不包含Web UI。

日历口径：排班连续天数与月计数统一使用显式 `calendar_timezone`（IANA名称，默认 `UTC`）。例如输入当地+08时刻但按当地业务日统计，应传 `Asia/Shanghai`。时长和休息间隔始终按实际时间差计算。资源枚举提前触及预算时返回 `budget_exhausted`，即便已找到暂定解也不称已穷尽搜索。

资源分配可选 `method="local"`，保留随机重启与单点改进算法；显式 `seed`、`restarts` 和 `budget`，每次评分计入预算。支持 `allowed_groups` 和 `fixed_group`，不凭镜像对称假定固定首项。局部搜索始终 `optimal=false`；`heuristic_complete` 只表示设定搜索结束。

## 2026-11-08 候选修订

- 声明tzdata，支持无系统时区库的平台。
- 搜索明确最多200需求单位，超过给出ValueError及拆分建议，不进入递归崩溃。
- 检查累计特征和派生评分有限，拒绝inf/NaN。

使用包内合成样例复跑；发布集合根目录的 `verify_release.py --project workflow-planning` 会依次执行测试和首次使用命令。原有版本的测试计数属于当时记录，本轮汇总以集合验证报告为准。
