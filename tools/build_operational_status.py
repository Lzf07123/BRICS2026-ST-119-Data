#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED_CSV = ROOT / "tools" / "seed_pool_mapping.csv"
STATUS_CSV = ROOT / "种子池运营状态登记表.csv"
REPORT = ROOT / "种子池运营状态核对报告.md"

ALLOWED_STATUSES = {
    "open",
    "closed_temporary",
    "paused",
    "renovating",
    "seasonal",
    "permanently_closed",
    "unknown",
}

STATUS_FIELDS = [
    "kb_id",
    "kb_name",
    "kb_city",
    "classification",
    "operational_status",
    "status_source",
    "status_checked_at",
    "status_note",
]

STATUS_OVERRIDES = {
    "A038": {
        "operational_status": "seasonal",
        "status_source": "本地口径登记",
        "status_note": "蓝眼泪为季节性自然现象，观赏受季节、天气和海况影响",
    },
    "A121": {
        "operational_status": "seasonal",
        "status_source": "本地口径登记",
        "status_note": "冰雪大世界为季节性项目，开放窗口与运营安排需按官方公告核实",
    },
    "A126": {
        "operational_status": "seasonal",
        "status_source": "本地口径登记",
        "status_note": "滑雪场具有明显雪季属性，非雪季运营范围需按官方公告核实",
    },
}


def load_seed() -> list[dict[str, str]]:
    with SEED_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_rows(seed: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in seed:
        override = STATUS_OVERRIDES.get(row["kb_id"], {})
        status = override.get("operational_status", "unknown")
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"非法运营状态：{row['kb_id']} {status}")
        rows.append(
            {
                "kb_id": row["kb_id"],
                "kb_name": row["kb_name"],
                "kb_city": row["kb_city"],
                "classification": row["classification"],
                "operational_status": status,
                "status_source": override.get("status_source", "待官网核对"),
                "status_checked_at": override.get(
                    "status_checked_at", "2026-09-04"
                ),
                "status_note": override.get(
                    "status_note",
                    "尚未完成官方运营状态核对；如闭园、改造或暂停开放，需保留状态卡",
                ),
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    with STATUS_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATUS_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, str]]) -> None:
    counts = {status: 0 for status in sorted(ALLOWED_STATUSES)}
    for row in rows:
        counts[row["operational_status"]] += 1
    lines = [
        "# 种子池运营状态核对报告",
        "",
        "> 生成时间：2026-09-04  ",
        "> 范围：340 条种子池景点。  ",
        "> 本报告只用于本地复核，不上传平台。",
        "",
        "## 状态快照",
        "",
        "| 运营状态 | 条目数 |",
        "| --- | ---: |",
    ]
    for status, count in counts.items():
        lines.append(f"| {status} | {count} |")
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- `unknown` 表示尚未完成官方运营状态核对，不得改写为确定状态。",
            "- `seasonal` 表示季节性运营或季节性自然现象，需在回答中说明季节窗口。",
            "- 若后续发现闭园、改造、暂停开放或永久关闭，必须更新本表并保留状态卡，不得删除条目。",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(rows: list[dict[str, str]]) -> None:
    if len(rows) != 340:
        raise ValueError(f"运营状态表应为 340 行，实际 {len(rows)}")
    if len({row["kb_id"] for row in rows}) != len(rows):
        raise ValueError("运营状态表 kb_id 重复")
    for row in rows:
        if row["operational_status"] not in ALLOWED_STATUSES:
            raise ValueError(f"非法运营状态：{row['kb_id']}")
        if not row["kb_id"] or not row["kb_name"] or not row["kb_city"]:
            raise ValueError(f"运营状态表缺少关键字段：{row['kb_id']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    seed = load_seed()
    if len(seed) != 340:
        raise ValueError(f"种子池映射应为 340 行，实际 {len(seed)}")
    if args.check:
        if not STATUS_CSV.exists():
            raise FileNotFoundError("种子池运营状态登记表缺失")
        with STATUS_CSV.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        validate(rows)
        print("运营状态表校验通过")
        return
    rows = build_rows(seed)
    validate(rows)
    write_csv(rows)
    write_report(rows)
    unknown = sum(row["operational_status"] == "unknown" for row in rows)
    print(f"运营状态登记表已生成：rows={len(rows)}, unknown={unknown}")


if __name__ == "__main__":
    main()
