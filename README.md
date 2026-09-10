# 中国国内旅行管家知识库工作区

> BRICS2026-ST-119 智能体备赛工作区。本仓库用于版本保护知识库底稿、生产脚本、验收材料和总决赛设计文件。Checklist 只跟踪数据质量、抽查与检索验收；平台知识库上传由数据负责人线下处理。

## 目录结构

```text
知识库数据/              # 平台上传用知识库底稿与验收材料
tools/                   # 数据生成与全库审计脚本
知识库生产Checklist.md    # 生产与验收基线
景点库拓展与99%覆盖检验Checklist.md # 全国景点总池与覆盖验收
景点库覆盖率与真实性审查报告.md # 覆盖率与真实性审查快照
知识库使用契约.md        # 知识库使用与提示词约束
未来拓展计划.md          # 决赛与产品化扩展路线
总决赛设计方案.md        # 决赛工作流、演示与评测总纲
```

## 数据概览

- 目的地：34 条
- 景点：346 条，34 个目的地各 10-11 条，含最佳季节与建议游玩时间；种子池拓展目标为每城 15 条、总计 510 条，全国总池数量待登记
- 美食：120 条
- 行程模板：35 条，覆盖全部目的地
- FAQ：30 条
- 交通住宿：68 条（34 条交通 + 34 条住宿，覆盖全部目的地）
- 文化讲解：34 条，覆盖全部目的地
- 头部旅游程序：17 条，仅用于本地竞品能力对标，不上传

## 常用命令

```bash
python3 tools/preflight.py
python3 tools/build_knowledge_base.py --validate-only
python3 tools/audit_knowledge_base.py
python3 tools/build_knowledge_base.py
python3 tools/build_pool.py
python3 tools/pool_report.py
python3 tools/field_specificity.py
python3 tools/build_operational_status.py --check
```

## 上传前流程

1. 打开 `知识库数据/上传与检索验证清单.md`。
2. 按顺序上传 41 份知识库数据文件；先运行 `python3 tools/build_upload_manifest.py` 生成 `上传文件清单.csv` 与 `上传文件SHA256SUMS.txt`，再用 `--check` 核对文件、条目数、字节数和哈希。所有清单、哈希和 QC 文件仅本地参考，不上传。
3. 上传后按清单中的别名问法和跨字段问法验证检索。
4. 修正问题时回到 `tools/kb_data.py` 或对应 Markdown 文件，改完后重新审计并提交。
5. 比赛或上传前可运行 `python3 tools/preflight.py`，一次性执行清单、生成和全库审计三项检查。

## 质量底线

- 只做中国国内旅行。
- 门票、营业时间、班次、人均等时效信息一律标注“待核实”，并提示以官方渠道为准。
- 普通条目 200-400 字，FAQ 答案 80-150 字，交通住宿条目 150-400 字；首行含条目 ID、名称、城市，景点附星级。
- 不编造店名、地址、价格、班次、评价和统计数字。
- 99% 只能指已锁定的全国权威景点总池覆盖率；必须先登记总池版本、来源和去重规则。34 个 L1 目的地只是种子池。
