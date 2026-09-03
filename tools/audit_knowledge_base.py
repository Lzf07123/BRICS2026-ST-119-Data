#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "知识库数据"

DEST_FIELDS = ["目的地名", "省份", "定位标签", "关键词", "一句话简介", "核心体验", "建议天数", "预算档", "最佳季节", "交通枢纽", "市内交通", "周边联动", "避坑提示"]
ATTRACTION_FIELDS = ["关键词", "名称", "目的地", "类型", "星级", "简介", "核心看点", "建议时长", "门票与预约", "开放时间", "交通指引", "最佳时段与避峰", "适合人群", "周边联动", "注意事项"]
FOOD_FIELDS = ["店名或品名", "城市", "类别", "关键词", "人均", "招牌必点", "地址", "营业时间", "排队情况", "口味标签", "适合场景", "附近联动", "贴士"]
ITIN_FIELDS = ["模板名", "适用人群", "预算档", "天数", "逐时段安排", "预算估算", "备选方案"]
FAQ_FIELDS = ["问题", "答案", "关联主题"]
TRANSPORT_FIELDS = ["线路", "方式", "时长", "费用区间", "班次频率", "实用提示"]
STAY_FIELDS = ["城市", "区域", "价位档", "推荐理由", "适合人群"]
CULTURE_FIELDS = ["关键词", "导览词", "关联地点", "趣味知识点"]

RANGE_RULES = {
    "01-目的地库.md": (25, 35),
    "03-美食库.md": (80, 120),
    "04-行程模板库.md": (15, 40),
    "05-FAQ库.md": (25, 35),
    "06-交通住宿库.md": (20, 60),
    "07-文化讲解库.md": (10, 30),
}

SCHEMA_RULES = {
    "01-目的地库.md": DEST_FIELDS,
    "02-景点库-*.md": ATTRACTION_FIELDS,
    "03-美食库.md": FOOD_FIELDS,
    "04-行程模板库.md": ITIN_FIELDS,
    "05-FAQ库.md": FAQ_FIELDS,
    "07-文化讲解库.md": CULTURE_FIELDS,
}

KEYWORD_RULES = {
    "01-目的地库.md": "关键词",
    "02-景点库-*.md": "关键词",
    "03-美食库.md": "关键词",
    "07-文化讲解库.md": "关键词",
}

HARD_INFO_RULES = {
    "01-目的地库.md": ["建议天数", "最佳季节", "交通枢纽", "市内交通"],
    "02-景点库-*.md": ["建议时长", "门票与预约", "开放时间", "交通指引"],
    "03-美食库.md": ["人均", "地址", "营业时间", "排队情况"],
    "04-行程模板库.md": ["天数", "逐时段安排", "预算估算"],
    "06-交通住宿库.md": ["时长", "费用区间", "班次频率", "价位档", "区域"],
}


def blocks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [block.strip() for block in text.split("\n\n") if block.startswith("### 【")]


def check_heading(block: str, path: Path, line: int, errors: list[str]) -> None:
    heading = block.splitlines()[0]
    if not re.match(r"^### 【[A-Z]\d{3}】.+｜.+?(｜.+)?$", heading):
        errors.append(f"{path}:{line} 首行缺少条目ID/名称/城市：{heading}")


def check_fields(block: str, path: Path, line: int, fields: list[str], errors: list[str]) -> None:
    actual = [row.split("：", 1)[0] for row in block.splitlines()[1:] if "：" in row]
    if actual != fields:
        errors.append(f"{path}:{line} 字段顺序不符，期望 {fields}，实际 {actual}")
    for row in block.splitlines()[1:]:
        if not row.strip() or "：" not in row:
            continue
        name, value = row.split("：", 1)
        if name in fields and not value.strip():
            errors.append(f"{path}:{line} 字段为空：{name}")


def check_len(block: str, path: Path, line: int, errors: list[str]) -> None:
    n = len(block.replace("\n", "").replace(" ", ""))
    if not 200 <= n <= 400:
        errors.append(f"{path}:{line} 条目长度 {n} 不在 200-400")


def check_len_range(block: str, path: Path, low: int, high: int, errors: list[str]) -> None:
    n = len(block.replace("\n", "").replace(" ", ""))
    if not low <= n <= high:
        errors.append(f"{path} 条目长度 {n} 不在 {low}-{high}")


def check_ids(path: Path, entries: list[str], errors: list[str]) -> list[str]:
    ids = []
    for block in entries:
        match = re.search(r"^### 【([A-Z]\d{3})】", block)
        if match:
            ids.append(match.group(1))
    if len(ids) != len(set(ids)):
        errors.append(f"{path} 条目ID重复")
    return ids


def check_hard_info(block: str, path: Path, line: int, fields: list[str], errors: list[str]) -> None:
    present = sum(1 for field in fields if f"{field}：" in block)
    if present < 2:
        errors.append(f"{path}:{line} 服务硬信息不足，仅 {present} 项")


def audit() -> list[str]:
    errors: list[str] = []
    all_ids: list[str] = []

    for pattern in ["01-目的地库.md", "03-美食库.md", "04-行程模板库.md", "05-FAQ库.md", "07-文化讲解库.md"]:
        path = OUT / pattern
        entries = blocks(path)
        low, high = RANGE_RULES[pattern]
        if not low <= len(entries) <= high:
            errors.append(f"{path} 条目数 {len(entries)} 不在 {low}-{high}")
        fields = SCHEMA_RULES[pattern]
        for block in entries:
            line = block.splitlines()[0]
            check_heading(block, path, 0, errors)
            check_fields(block, path, 0, fields, errors)
            check_len(block, path, 0, errors)
            keyword_field = KEYWORD_RULES.get(pattern)
            if keyword_field and (f"{keyword_field}：" not in block or not re.search(rf"^{keyword_field}：.{{4,}}$", block, re.M)):
                errors.append(f"{path}:{line} 关键词缺失或过短")
            if keyword_field:
                match = re.search(rf"^{keyword_field}：(.+)$", block, re.M)
                if match and len([x for x in re.split(r"[、,，]", match.group(1)) if x.strip()]) < 2:
                    errors.append(f"{path}:{line} 关键词少于 2 个")
            if pattern in HARD_INFO_RULES:
                check_hard_info(block, path, 0, HARD_INFO_RULES[pattern], errors)
        all_ids.extend(check_ids(path, entries, errors))

    attraction_files = sorted(OUT.glob("02-景点库-*.md"))
    total_attractions = 0
    star_count: dict[int, int] = {}
    for path in attraction_files:
        entries = blocks(path)
        total_attractions += len(entries)
        if not 8 <= len(entries) <= 15:
            errors.append(f"{path} 条目数 {len(entries)} 不在 8-15")
        for block in entries:
            line = block.splitlines()[0]
            check_heading(block, path, 0, errors)
            check_fields(block, path, 0, ATTRACTION_FIELDS, errors)
            check_len(block, path, 0, errors)
            if "关键词：" not in block or "★" not in line:
                errors.append(f"{path}:{line} 关键词或星级缺失")
            check_hard_info(block, path, 0, HARD_INFO_RULES["02-景点库-*.md"], errors)
            star_count[line.count("★")] = star_count.get(line.count("★"), 0) + 1
        all_ids.extend(check_ids(path, entries, errors))
    if not 250 <= total_attractions <= 400:
        errors.append(f"景点总条目 {total_attractions} 不在 250-400")
    if total_attractions and star_count.get(5, 0) / total_attractions > 0.25:
        errors.append(f"五星占比 {star_count.get(5, 0) / total_attractions:.2%} 超过 25%")

    stay_path = OUT / "06-交通住宿库.md"
    entries = blocks(stay_path)
    if not RANGE_RULES["06-交通住宿库.md"][0] <= len(entries) <= RANGE_RULES["06-交通住宿库.md"][1]:
        errors.append(f"{stay_path} 条目数 {len(entries)} 不在 20-30")
    for block in entries:
        line = block.splitlines()[0]
        check_len_range(block, stay_path, 150, 400, errors)
        if block.startswith("### 【T") and "线路：" in block:
            fields = TRANSPORT_FIELDS
        elif block.startswith("### 【T") and "城市：" in block:
            fields = STAY_FIELDS
        else:
            errors.append(f"{stay_path}:{line} 交通住宿类型无法识别")
            continue
        check_fields(block, stay_path, 0, fields, errors)
        check_hard_info(block, stay_path, 0, HARD_INFO_RULES["06-交通住宿库.md"], errors)
    all_ids.extend(check_ids(stay_path, entries, errors))

    if len(all_ids) != len(set(all_ids)):
        errors.append("全库条目ID重复")

    sensitive = re.compile(r"(?i)(password|passwd|token|api[_-]?key|secret|身份证|银行卡|手机号[:：])")
    for path in OUT.glob("*.md"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if sensitive.search(line):
                errors.append(f"{path}:{number} 疑似敏感信息")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    errors = audit()
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    if args.report:
        report = OUT / "自检报告.md"
        text = report.read_text(encoding="utf-8")
        text = text.replace("本地生成器校验 + 全库条目统计 + 重点联网核查", "本地生成器校验 + 全库审计脚本 + 重点联网核查")
        report.write_text(text, encoding="utf-8")
    print("审计通过")


if __name__ == "__main__":
    main()
