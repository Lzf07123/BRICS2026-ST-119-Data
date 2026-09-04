#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POOL_CSV = ROOT / "全国景点覆盖分母登记表.csv"
SOURCE_CSV = ROOT / "数据来源与版本登记表.csv"
SOURCE_DIR = ROOT / "数据来源" / "文化和旅游部"
KB_DIR = ROOT / "知识库数据"
POOL_VERSION = "CN-POOL-20260904-r0"

PROVINCE_ALIASES = {
    "上海": "上海市",
    "云南": "云南省",
    "内蒙古": "内蒙古自治区",
    "北京": "北京市",
    "吉林": "吉林省",
    "四川": "四川省",
    "天津": "天津市",
    "宁夏": "宁夏回族自治区",
    "安徽": "安徽省",
    "山东": "山东省",
    "山西": "山西省",
    "山西、陕西": "跨省",
    "广东": "广东省",
    "广西": "广西壮族自治区",
    "新疆": "新疆维吾尔自治区",
    "江苏": "江苏省",
    "江西": "江西省",
    "河北": "河北省",
    "河南": "河南省",
    "浙江": "浙江省",
    "海南": "海南省",
    "湖北": "湖北省",
    "湖南": "湖南省",
    "甘肃": "甘肃省",
    "福建": "福建省",
    "西藏": "西藏自治区",
    "贵州": "贵州省",
    "辽宁": "辽宁省",
    "重庆": "重庆市",
    "陕西": "陕西省",
    "青海": "青海省",
    "黑龙江": "黑龙江省",
}

SOURCE_INFO = {
    "4": ("A/B", "5A级旅游景区", "A级景区"),
    "40": ("H", "红色旅游经典景区", "红色旅游"),
    "36": ("J", "第一批全国乡村旅游重点村", "乡村旅游重点村"),
    "37": ("J", "第二批全国乡村旅游重点村", "乡村旅游重点村"),
    "38": ("J", "第三批全国乡村旅游重点村", "乡村旅游重点村"),
    "43": ("J", "第四批全国乡村旅游重点村", "乡村旅游重点村"),
    "39": ("J", "第一批全国乡村旅游重点镇", "乡村旅游重点镇"),
    "44": ("J", "第二批全国乡村旅游重点镇", "乡村旅游重点镇"),
    "56": ("J", "国家级旅游度假区", "旅游度假区"),
    "49": ("I", "第一批国家级旅游休闲街区", "旅游休闲街区"),
    "50": ("I", "第二批国家级旅游休闲街区", "旅游休闲街区"),
    "60": ("I", "第三批国家级旅游休闲街区", "旅游休闲街区"),
    "61": ("I", "第四批国家级旅游休闲街区", "旅游休闲街区"),
    "51": ("J", "第一批国家级滑雪旅游度假地", "滑雪旅游度假地"),
    "52": ("J", "第二批国家级滑雪旅游度假地", "滑雪旅游度假地"),
    "59": ("J", "第三批国家级滑雪旅游度假地", "滑雪旅游度假地"),
    "54": ("J", "国家工业旅游示范基地", "工业旅游"),
}

POOL_FIELDS = [
    "pool_id",
    "dedup_key",
    "official_name",
    "aliases",
    "province",
    "city",
    "county",
    "grade_bucket",
    "category",
    "operational_status",
    "coverage_status",
    "source_name",
    "source_url",
    "source_version",
    "kb_file",
    "kb_id",
    "pending_reason",
    "merge_target_id",
    "removed_reason",
    "is_denominator",
    "pool_version",
    "verification_note",
]

SOURCE_FIELDS = [
    "source_code",
    "source_name",
    "publisher",
    "source_url",
    "source_version",
    "captured_at",
    "captured_by",
    "sha256",
    "archive_path",
    "dedup_rule",
    "note",
]

SEED_MAPPING_FIELDS = [
    "kb_id",
    "kb_name",
    "kb_city",
    "official_name",
    "pool_id",
    "coverage_status",
    "classification",
    "confidence",
    "reason",
]


def normalize_name(value: str) -> str:
    return re.sub(r"[\s（）()·、,，。.]", "", value or "").lower()


def normalize_province(value: str) -> str:
    return PROVINCE_ALIASES.get((value or "").strip(), (value or "").strip())


def dedup_key(row: dict[str, str], external_id: int) -> str:
    parts = [
        row["official_name"],
        row["province"],
        row["city"],
        row["source_name"],
        str(external_id),
    ]
    return hashlib.sha256("｜".join(parts).encode("utf-8")).hexdigest()


def read_attractions() -> dict[str, tuple[str, str]]:
    attractions: dict[str, tuple[str, str]] = {}
    for path in sorted(KB_DIR.glob("02-景点库-*.md")):
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(r"^### 【([A-Z]\d{3})】(.+?)｜(.+?)｜", re.M)
        for kb_id, name, city in pattern.findall(text):
            attractions.setdefault(kb_id, (name.strip(), city.strip(), path.name))
    return attractions


def read_manual_mapping() -> dict[str, str]:
    path = ROOT / "tools" / "seed_mapping.txt"
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("A"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        kb_id, _, official_name = parts[:3]
        mapping[kb_id] = official_name
    return mapping


def used_kb_ids() -> set[str]:
    used: set[str] = set()
    return used


def source_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for directory_id, (code, name, _) in SOURCE_INFO.items():
        path = SOURCE_DIR / f"content_{directory_id}.json"
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(
            {
                "source_code": code,
                "source_name": name,
                "publisher": "文化和旅游部",
                "source_url": "https://www.mct.gov.cn/tourism/#/list",
                "source_version": f"API目录ID-{directory_id}/2026-09-04",
                "captured_at": "2026-09-04T14:49+08:00",
                "captured_by": "Codex",
                "sha256": digest,
                "archive_path": str(path.relative_to(ROOT)),
                "dedup_rule": "官方名称｜省份｜来源目录｜MCT内容ID",
                "note": "文化和旅游部公开名录接口抓取，N0 版本锁定源",
            }
        )
    extra_rows = [
        {
            "source_code": "C",
            "source_name": "全国重点文物保护单位名录查询",
            "publisher": "国家政务服务平台",
            "source_url": "http://app.gjzwfw.gov.cn/jmopen/webapp/html5/gjwwjqgzdwwbhdwmlcx/index.html",
            "source_version": "2026-09-04",
            "captured_at": "2026-09-04T16:20+08:00",
            "captured_by": "Codex",
            "sha256": "",
            "archive_path": "数据来源/国家政务服务平台/col529_index.md",
            "dedup_rule": "文保编号｜名称｜行政区",
            "note": "国家政务服务平台国家文物局服务页，内含全国重点文物保护单位名录入口",
        },
        {
            "source_code": "F",
            "source_name": "全国博物馆名录",
            "publisher": "国家政务服务平台",
            "source_url": "http://app.gjzwfw.gov.cn/jmopen/webapp/html5/gjwwjqgbwgmlcxpc/index.html",
            "source_version": "2026-09-04",
            "captured_at": "2026-09-04T16:20+08:00",
            "captured_by": "Codex",
            "sha256": "",
            "archive_path": "数据来源/国家政务服务平台/col529_index.md",
            "dedup_rule": "备案编号｜名称｜行政区",
            "note": "国家政务服务平台国家文物局服务页，内含全国博物馆名录入口",
        },
        {
            "source_code": "G",
            "source_name": "中国的世界文化遗产",
            "publisher": "国家文物局",
            "source_url": "http://www.ncha.gov.cn/col/col2790/index.html",
            "source_version": "2026-09-04",
            "captured_at": "2026-09-04T16:20+08:00",
            "captured_by": "Codex",
            "sha256": "",
            "archive_path": "数据来源/国家文物局/col2790_world_heritage.md",
            "dedup_rule": "UNESCO ID｜官方名称｜中国名称",
            "note": "国家文物局中国的世界文化遗产页面",
        },
        {
            "source_code": "D/E",
            "source_name": "国务院关于3省国家级自然保护区和国家级风景名胜区整合优化方案的批复",
            "publisher": "中国政府网",
            "source_url": "https://www.gov.cn/zhengce/content/202606/content_7072483.htm",
            "source_version": "国函〔2026〕53号/2026-06-17",
            "captured_at": "2026-09-04T16:20+08:00",
            "captured_by": "Codex",
            "sha256": "",
            "archive_path": "数据来源/中国政府网/2026-06-17_nature_reserve_scenic_area.md",
            "dedup_rule": "官方名称｜行政区｜发文机关｜文号",
            "note": "国务院批复，D/E 类官方公告原件；完整名录仍待接入",
        },
    ]
    for row in extra_rows:
        archive = ROOT / row["archive_path"]
        if archive.is_file():
            row["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    rows.extend(extra_rows)
    return rows


def pool_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    attractions = read_attractions()
    manual_mapping = read_manual_mapping()
    manual_by_official: dict[str, list[str]] = {}
    for kb_id, official_name in manual_mapping.items():
        manual_by_official.setdefault(normalize_name(official_name), []).append(kb_id)
    used = used_kb_ids()
    by_name: dict[str, list[str]] = {}
    for kb_id, (name, city, filename) in attractions.items():
        by_name.setdefault(normalize_name(name), []).append(kb_id)

    seq = 0
    for directory_id, (code, source_name, category) in SOURCE_INFO.items():
        path = SOURCE_DIR / f"content_{directory_id}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload["data"]["contentList"]["content"]
        for item in items:
            official_name = item["name"].strip()
            manual_kb_ids = manual_by_official.get(normalize_name(official_name), [])
            kb_ids = by_name.get(normalize_name(official_name), [])
            kb_id = ""
            kb_file = ""
            coverage_status = "pending"
            pending_reason = "尚未映射到可回跳的知识库景点卡"
            if len(manual_kb_ids) == 1:
                kb_ids = [manual_kb_ids[0]]
            if kb_ids:
                candidates = [kb for kb in kb_ids if kb not in used]
                if len(candidates) == 1:
                    kb_id = candidates[0]
                    kb_file = f"知识库数据/{attractions[kb_id][2]}"
                    coverage_status = "covered"
                    pending_reason = ""
                    used.add(kb_id)
            seq += 1
            row = {
                "pool_id": f"CN-P-{seq:06d}",
                "dedup_key": "",
                "official_name": official_name,
                "aliases": "",
                "province": normalize_province(item.get("provinceName") or ""),
                "city": item.get("cityName") or "",
                "county": "",
                "grade_bucket": "5A" if directory_id == "4" else "非A",
                "category": category,
                "operational_status": "unknown",
                "coverage_status": coverage_status,
                "source_name": source_name,
                "source_url": "https://www.mct.gov.cn/tourism/#/list",
                "source_version": f"API目录ID-{directory_id}/2026-09-04",
                "kb_file": kb_file,
                "kb_id": kb_id,
                "pending_reason": pending_reason,
                "merge_target_id": "",
                "removed_reason": "",
                "is_denominator": "1",
                "pool_version": POOL_VERSION,
                "verification_note": f"MCT内容ID={item['id']}；来源文件={path.name}",
            }
            row["dedup_key"] = dedup_key(row, item["id"])
            rows.append(row)
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_seed_mapping(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    attractions = read_attractions()
    manual_mapping = read_manual_mapping()
    pool_by_name: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        pool_by_name.setdefault(normalize_name(row["official_name"]), []).append(row)

    mapping: list[dict[str, str]] = []
    for kb_id, (name, city, _) in sorted(attractions.items()):
        official_name = manual_mapping.get(kb_id, name)
        matches = pool_by_name.get(normalize_name(official_name), [])
        if len(matches) == 1:
            match = matches[0]
            classification = "covered_exact" if match["official_name"] == name else "covered_variant"
            confidence = "high" if kb_id in manual_mapping else "medium"
            reason = "官方名录名称一致" if classification == "covered_exact" else "官方名录名称变体或含行政区前缀"
            mapping.append(
                {
                    "kb_id": kb_id,
                    "kb_name": name,
                    "kb_city": city,
                    "official_name": match["official_name"],
                    "pool_id": match["pool_id"],
                    "coverage_status": "covered",
                    "classification": classification,
                    "confidence": confidence,
                    "reason": reason,
                }
            )
        else:
            mapping.append(
                {
                    "kb_id": kb_id,
                    "kb_name": name,
                    "kb_city": city,
                    "official_name": official_name,
                    "pool_id": "",
                    "coverage_status": "pending",
                    "classification": "pending",
                    "confidence": "low",
                    "reason": "未完成官方名称、行政区或来源核对，不计入覆盖分子",
                }
            )
    return mapping


def read_seed_mapping() -> list[dict[str, str]]:
    path = ROOT / "tools" / "seed_mapping_full.txt"
    if not path.exists():
        return []
    mapping: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("A") or "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) < 9:
            continue
        mapping.append(
            {
                "kb_id": parts[0],
                "kb_name": parts[1],
                "kb_city": parts[2],
                "official_name": parts[3],
                "pool_id": parts[4],
                "coverage_status": parts[5],
                "classification": parts[6],
                "confidence": parts[7],
                "reason": parts[8],
            }
        )
    return mapping


def validate_seed_mapping(mapping: list[dict[str, str]], rows: list[dict[str, str]]) -> None:
    if len(mapping) != 340:
        raise ValueError(f"种子池映射应为 340 条，实际 {len(mapping)}")
    if len({row["kb_id"] for row in mapping}) != len(mapping):
        raise ValueError("种子池映射 kb_id 重复")
    allowed_status = {"covered", "pending"}
    allowed_classification = {
        "covered_exact",
        "covered_variant",
        "covered_component",
        "pending",
        "unmatched",
        "nested",
        "cross_city",
        "experience",
    }
    pool_ids = {row["pool_id"] for row in rows}
    for row in mapping:
        if row["coverage_status"] not in allowed_status:
            raise ValueError(f"非法覆盖状态：{row['kb_id']} {row['coverage_status']}")
        if row["classification"] not in allowed_classification:
            raise ValueError(f"非法分类：{row['kb_id']} {row['classification']}")
        if row["coverage_status"] == "covered":
            if not row["pool_id"] or row["pool_id"] not in pool_ids:
                raise ValueError(f"覆盖映射缺少有效 pool_id：{row['kb_id']}")
        elif row["pool_id"] and row["pool_id"] not in pool_ids:
            raise ValueError(f"待补映射的 pool_id 不在总池：{row['kb_id']}")


def validate_sources(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("来源登记表为空")
    allowed_codes = set("ABCDEFGHIJ")
    for row in rows:
        if not all(code in allowed_codes for code in row["source_code"].split("/")):
            raise ValueError(f"来源类别非法：{row['source_code']}")
        for field in ["source_name", "publisher", "source_url", "source_version", "captured_at", "captured_by", "sha256", "archive_path", "dedup_rule"]:
            if not row[field]:
                raise ValueError(f"{row['source_code']} 来源字段为空：{field}")
        archive = ROOT / row["archive_path"]
        if not archive.is_file():
            raise ValueError(f"来源归档文件缺失：{row['archive_path']}")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            raise ValueError(f"来源归档哈希不一致：{row['archive_path']}")
    covered_codes = set()
    for row in rows:
        covered_codes.update(row["source_code"].split("/"))
    missing = allowed_codes - covered_codes
    if missing:
        raise ValueError(f"来源类别缺失：{sorted(missing)}")


def validate(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("总池为空")
    ids = [row["pool_id"] for row in rows]
    keys = [row["dedup_key"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("pool_id 重复")
    if len(keys) != len(set(keys)):
        raise ValueError("dedup_key 重复")
    if any(not row["official_name"] for row in rows):
        raise ValueError("存在空官方名称")
    if any(row["is_denominator"] != "1" for row in rows):
        raise ValueError("当前 N0 全部条目应进入分母")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    rows = pool_rows()
    validate(rows)
    seed_mapping = read_seed_mapping()
    if seed_mapping:
        validate_seed_mapping(seed_mapping, rows)
    validate_sources(source_rows())
    if args.validate_only:
        print("总池校验通过")
        return
    write_csv(POOL_CSV, POOL_FIELDS, rows)
    write_csv(SOURCE_CSV, SOURCE_FIELDS, source_rows())
    write_csv(ROOT / "tools" / "seed_pool_mapping.csv", SEED_MAPPING_FIELDS, seed_mapping)
    coverage = Counter(row["coverage_status"] for row in rows)
    provinces = Counter(row["province"] for row in rows)
    print(
        "总池生成完成："
        f"entries={len(rows)}, covered={coverage['covered']}, "
        f"pending={coverage['pending']}, provinces={len(provinces)}, version={POOL_VERSION}"
    )


if __name__ == "__main__":
    main()
