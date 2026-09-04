#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POOL_CSV = ROOT / "全国景点覆盖分母登记表.csv"
SOURCE_CSV = ROOT / "数据来源与版本登记表.csv"
SEED_CSV = ROOT / "tools" / "seed_pool_mapping.csv"
REPORT = ROOT / "总池状态报告.md"


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def counter_lines(counter: Counter[str], label: str) -> list[str]:
    lines = [f"| {label} | 条目数 |"]
    lines.append("| --- | ---: |")
    for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {key} | {value} |")
    return lines


def main() -> None:
    pool = load(POOL_CSV)
    sources = load(SOURCE_CSV)
    seed = load(SEED_CSV)

    versions = Counter(row["pool_version"] for row in pool)
    if len(versions) != 1:
        raise ValueError(f"总池版本不唯一：{versions}")
    pool_version = next(iter(versions))

    province_counter = Counter(row["province"] for row in pool)
    coverage_counter = Counter(row["coverage_status"] for row in pool)
    status_counter = Counter(row["operational_status"] for row in pool)
    grade_counter = Counter(row["grade_bucket"] for row in pool)
    source_counter = Counter(row["source_code"] for row in sources)
    seed_status_counter = Counter(row["coverage_status"] for row in seed)
    seed_class_counter = Counter(row["classification"] for row in seed)

    lines = [
        "# 全国景点总池状态报告",
        "",
        f"> 报告生成时间：2026-09-04 17:05  ",
        f"> 总池版本：`{pool_version}`  ",
        "> 本报告只做本地复核，不上传平台，也不作为答案语料。",
        "",
        "## 总池快照",
        "",
        "| 维度 | 结果 |",
        "| --- | ---: |",
        f"| 总池条目 | {len(pool)} |",
        f"| 覆盖条目 | {coverage_counter['covered']} |",
        f"| 待补条目 | {coverage_counter['pending']} |",
        f"| 待定条目 | {coverage_counter['undetermined']} |",
        f"| 合并条目 | {coverage_counter['merged']} |",
        f"| 剔除条目 | {coverage_counter['removed']} |",
        f"| 省级行政区 | {len(province_counter)} |",
        "",
        "## 覆盖状态分布",
        "",
        *counter_lines(coverage_counter, "覆盖状态"),
        "",
        "## 运营状态分布",
        "",
        *counter_lines(status_counter, "运营状态"),
        "",
        "## 景区等级分布",
        "",
        *counter_lines(grade_counter, "等级"),
        "",
        "## 来源类别覆盖",
        "",
        *counter_lines(source_counter, "来源类别"),
        "",
        "## 种子池映射快照",
        "",
        "| 维度 | 结果 |",
        "| --- | ---: |",
        f"| 种子池条目 | {len(seed)} |",
        f"| 映射为 covered | {seed_status_counter['covered']} |",
        f"| 映射为 pending | {seed_status_counter['pending']} |",
        "",
        "### 种子池分类",
        "",
        *counter_lines(seed_class_counter, "分类"),
        "",
        "## 分省总池条目",
        "",
        "| 省级行政区 | 总池条目 |",
        "| --- | ---: |",
    ]
    for province, count in sorted(province_counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {province} | {count} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成 {REPORT.name}：entries={len(pool)}, covered={coverage_counter['covered']}, pending={coverage_counter['pending']}")


if __name__ == "__main__":
    main()
