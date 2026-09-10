#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from kb_data import attractions, destinations, faqs, foods, itineraries


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "知识库数据"


ATTRACTION_FIELDS = [
    "关键词", "名称", "目的地", "类型", "星级", "简介", "核心看点",
    "建议游玩时间", "门票与预约", "开放时间", "最佳季节", "交通指引",
    "最佳时段与避峰", "适合人群", "周边联动", "注意事项",
]


def attraction_block(row: dict[str, str]) -> str:
    lines = [f"### 【{row['id']}】{row['heading_name']}｜{row['heading_city']}｜{row['heading_star']}"]
    lines.extend(f"{field}：{row[field]}" for field in ATTRACTION_FIELDS)
    return "\n".join(lines)


def write_attractions() -> None:
    for city, rows in attractions.items():
        path = OUT / f"02-景点库-{city}.md"
        lines = [f"# {city}景点库", ""]
        for row in rows:
            if row["heading_city"] != city:
                raise ValueError(f"景点目的地与文件不一致：{row['id']} {row['heading_city']} != {city}")
            lines.extend([attraction_block(row), ""])
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_simple(
    filename: str,
    title: str,
    prefix: str,
    rows: list[dict[str, str]],
    headings: list[str],
    first_heading_name: str,
    heading_city,
) -> None:
    lines = [f"# {title}", ""]
    for seq, row in enumerate(rows, 1):
        primary = row[first_heading_name]
        extra = row.get("星级", "")
        heading = f"### 【{prefix}{seq:03d}】{primary}｜{heading_city(row)}" + (f"｜{extra}" if extra else "")
        lines.append(heading)
        for field in headings:
            lines.append(f"{field}：{row[field]}")
        lines.append("")
    (OUT / filename).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def validate() -> None:
    if not 25 <= len(destinations) <= 35:
        raise ValueError(f"目的地数量不在 25-35：{len(destinations)}")
    if not 250 <= sum(map(len, attractions.values())) <= 100000:
        raise ValueError(f"景点数量不在 250-100000：{sum(map(len, attractions.values()))}")
    if not 80 <= len(foods) <= 120:
        raise ValueError(f"美食数量不在 80-120：{len(foods)}")
    if not 15 <= len(itineraries) <= 40:
        raise ValueError(f"行程模板数量不在 15-20：{len(itineraries)}")
    if not 25 <= len(faqs) <= 35:
        raise ValueError(f"FAQ数量不在 25-35：{len(faqs)}")

    destination_names = {row["目的地名"] for row in destinations}
    missing = destination_names - attractions.keys()
    if missing:
        raise ValueError(f"景点库缺少目的地：{missing}")
    attraction_ids = [row["id"] for rows in attractions.values() for row in rows]
    if len(attraction_ids) != len(set(attraction_ids)):
        raise ValueError("景点ID重复")
    for city, rows in attractions.items():
        if not 10 <= len(rows) <= 2000:
            raise ValueError(f"{city} 景点数量不在 10-2000：{len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    validate()
    if args.validate_only:
        print("校验通过")
        return
    OUT.mkdir(exist_ok=True)
    write_attractions()
    write_simple(
        "01-目的地库.md",
        "目的地库",
        "D",
        destinations,
        ["目的地名", "省份", "定位标签", "关键词", "一句话简介", "核心体验", "建议天数", "预算档", "最佳季节", "交通枢纽", "市内交通", "周边联动", "避坑提示"],
        "目的地名",
        lambda row: row["目的地名"],
    )
    write_simple(
        "03-美食库.md",
        "美食库",
        "F",
        foods,
        ["店名或品名", "城市", "类别", "关键词", "人均", "招牌必点", "地址", "营业时间", "排队情况", "口味标签", "适合场景", "附近联动", "贴士"],
        "店名或品名",
        lambda row: row["城市"],
    )
    write_simple(
        "04-行程模板库.md",
        "行程模板库",
        "R",
        itineraries,
        ["模板名", "适用人群", "预算档", "天数", "逐时段安排", "预算估算", "备选方案"],
        "模板名",
        lambda row: row["模板名"].split(" ")[0],
    )
    write_simple(
        "05-FAQ库.md",
        "FAQ库",
        "Q",
        faqs,
        ["问题", "答案", "关联主题"],
        "问题",
        lambda row: "通用",
    )
    print("生成完成")


if __name__ == "__main__":
    main()
