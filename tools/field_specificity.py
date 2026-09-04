#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "知识库数据"
REPORT = ROOT / "景点字段具体率报告.md"
CSV_PATH = ROOT / "字段时效兜底清单.csv"

CSV_FIELDS = [
    "条目ID",
    "名称",
    "目的地",
    "字段",
    "当前口径",
    "状态",
    "处理建议",
]


def load_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(KB_DIR.glob("02-景点库-*.md")):
        text = path.read_text(encoding="utf-8")
        for part in text.split("### 【")[1:]:
            block = "### 【" + part.strip()
            heading = block.splitlines()[0]
            match = re.match(r"^### 【([A-Z]\d{3})】(.+?)｜(.+?)｜", heading)
            if not match:
                continue
            kb_id, name, city = match.groups()
            for field in ("门票与预约", "开放时间"):
                field_match = re.search(rf"^{field}：(.*)$", block, re.M)
                if field_match:
                    entries.append(
                        {
                            "条目ID": kb_id,
                            "名称": name.strip(),
                            "目的地": city.strip(),
                            "字段": field,
                            "当前口径": field_match.group(1).strip(),
                        }
                    )
    return entries


def classify(value: str) -> str:
    if re.fullmatch(r"以官方渠道(?:当日公告)?为准（待核实）", value):
        return "完全兜底"
    if "以官方渠道" in value or value == "待核实":
        return "部分兜底"
    return "具体口径"


def write_csv(rows: list[dict[str, str]]) -> None:
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(entries: list[dict[str, str]], rows: list[dict[str, str]]) -> None:
    total = len(entries)
    exact_generic = sum(row["状态"] == "完全兜底" for row in rows)
    partial = sum(row["状态"] == "部分兜底" for row in rows)
    specific = total - exact_generic - partial
    ticket_entries = [entry for entry in entries if entry["字段"] == "门票与预约"]
    open_entries = [entry for entry in entries if entry["字段"] == "开放时间"]
    ticket_generic = sum(
        entry["当前口径"] == "以官方渠道为准（待核实）" for entry in ticket_entries
    )
    open_generic = sum(
        entry["当前口径"] == "以官方渠道为准（待核实）" for entry in open_entries
    )
    lines = [
        "# 景点字段具体率报告",
        "",
        "> 生成时间：2026-09-04  ",
        "> 范围：`知识库数据/02-景点库-*.md` 340 条景点、每条两个时效字段。  ",
        "> 本报告只用于本地复核和补库排期，不上传平台。",
        "",
        "## 快照",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 景点条目 | {len(ticket_entries)} |",
        f"| 时效字段总数 | {total} |",
        f"| 完全兜底字段 | {exact_generic} |",
        f"| 部分兜底字段 | {partial} |",
        f"| 非兜底字段 | {specific} |",
        f"| 非兜底率 | {specific / total:.2%} |",
        f"| 门票字段完全兜底 | {ticket_generic} / {len(ticket_entries)} |",
        f"| 开放时间字段完全兜底 | {open_generic} / {len(open_entries)} |",
        "",
        "## 口径说明",
        "",
        "- `完全兜底`：字段仅写“以官方渠道为准（待核实）”。",
        "- `部分兜底`：字段已有部分信息，但仍包含官方渠道兜底表述。",
        "- `具体口径`：字段未使用官方渠道兜底句式。",
        "- 清单见 `字段时效兜底清单.csv`，只作为本地补库排期，不上传平台。",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-only", action="store_true")
    args = parser.parse_args()
    entries = load_entries()
    if len(entries) != 680:
        raise ValueError(f"时效字段总数应为 680，实际 {len(entries)}")
    rows = []
    for entry in entries:
        status = classify(entry["当前口径"])
        if status == "具体口径":
            continue
        rows.append(
            {
                **entry,
                "状态": status,
                "处理建议": "以官方渠道当日公告回填票价、预约、放票和开放时间",
            }
        )
    write_csv(rows)
    if not args.csv_only:
        write_report(entries, rows)
    exact_generic = sum(row["状态"] == "完全兜底" for row in rows)
    partial = sum(row["状态"] == "部分兜底" for row in rows)
    print(
        f"字段时效兜底清单已生成：total={len(entries)}, "
        f"exact_generic={exact_generic}, partial={partial}"
    )


if __name__ == "__main__":
    main()
