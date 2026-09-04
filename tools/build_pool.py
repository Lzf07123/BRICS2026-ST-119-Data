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
    if args.validate_only:
        print("总池校验通过")
        return
    write_csv(POOL_CSV, POOL_FIELDS, rows)
    write_csv(SOURCE_CSV, SOURCE_FIELDS, source_rows())
    coverage = Counter(row["coverage_status"] for row in rows)
    provinces = Counter(row["province"] for row in rows)
    print(
        "总池生成完成："
        f"entries={len(rows)}, covered={coverage['covered']}, "
        f"pending={coverage['pending']}, provinces={len(provinces)}, version={POOL_VERSION}"
    )


if __name__ == "__main__":
    main()
