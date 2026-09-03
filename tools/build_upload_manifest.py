#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "知识库数据"
BUSINESS_FILES = [
    "00-数据字典.md",
    "01-目的地库.md",
    *sorted(path.name for path in OUT.glob("02-景点库-*.md")),
    "03-美食库.md",
    "04-行程模板库.md",
    "05-FAQ库.md",
    "06-交通住宿库.md",
    "07-文化讲解库.md",
]

CATEGORIES = {
    "00": "数据字典",
    "01": "目的地库",
    "02": "景点库",
    "03": "美食库",
    "04": "行程模板库",
    "05": "FAQ库",
    "06": "交通住宿库",
    "07": "文化讲解库",
}


def entry_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("### 【"))


def build(csv_path: Path, sums_path: Path) -> None:
    if len(BUSINESS_FILES) != 41:
        raise ValueError(f"上传业务文件数应为 41，实际 {len(BUSINESS_FILES)}")

    rows = []
    total_bytes = 0
    for number, name in enumerate(BUSINESS_FILES, 1):
        path = OUT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        size = len(data)
        total_bytes += size
        rows.append(
            {
                "序号": number,
                "文件": name,
                "类别": CATEGORIES[name[:2]],
                "条目数": entry_count(path),
                "字节": size,
                "SHA-256": digest,
            }
        )

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with sums_path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(f"{row['SHA-256']}  知识库数据/{row['文件']}\n")

    print(f"已生成 {csv_path.name} 和 {sums_path.name}：{len(rows)} 份独立文件，{total_bytes} 字节，不打包压缩")


def check(csv_path: Path, sums_path: Path) -> None:
    if len(BUSINESS_FILES) != 41:
        raise ValueError(f"上传业务文件数应为 41，实际 {len(BUSINESS_FILES)}")
    if not csv_path.is_file() or not sums_path.is_file():
        raise FileNotFoundError("上传文件清单或 SHA256SUMS 缺失")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(BUSINESS_FILES):
        raise ValueError(f"清单行数应为 41，实际 {len(rows)}")
    if [row["文件"] for row in rows] != BUSINESS_FILES:
        raise ValueError("上传文件清单顺序与业务文件列表不一致")

    for row in rows:
        name = row["文件"]
        path = OUT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if row["SHA-256"] != digest:
            raise ValueError(f"{name} SHA-256 与清单不一致")
        if row["字节"] != str(len(data)):
            raise ValueError(f"{name} 字节数与清单不一致")
        if row["条目数"] != str(entry_count(path)):
            raise ValueError(f"{name} 条目数与清单不一致")

    sums_lines = [line for line in sums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(sums_lines) != len(rows):
        raise ValueError(f"SHA256SUMS 行数应为 {len(rows)}，实际 {len(sums_lines)}")
    for row, line in zip(rows, sums_lines):
        digest, relative = line.split("  ", 1)
        if digest != row["SHA-256"] or relative != f"知识库数据/{row['文件']}":
            raise ValueError(f"{row['文件']} 在 SHA256SUMS 中与清单不一致")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只校验清单数量与哈希文件一致性")
    args = parser.parse_args()
    csv_path = OUT / "上传文件清单.csv"
    sums_path = OUT / "上传文件SHA256SUMS.txt"
    if args.check:
        check(csv_path, sums_path)
        print("上传文件清单校验通过")
        return
    build(csv_path, sums_path)


if __name__ == "__main__":
    main()
