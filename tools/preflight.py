#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

STEPS = [
    ("上传文件清单", [TOOLS / "build_upload_manifest.py", "--check"]),
    ("知识库生成校验", [TOOLS / "build_knowledge_base.py", "--validate-only"]),
    ("全库审计", [TOOLS / "audit_knowledge_base.py"]),
]


def main() -> int:
    for label, command in STEPS:
        print(f"== {label} ==")
        result = subprocess.run([sys.executable, *(str(item) for item in command)], cwd=ROOT)
        if result.returncode:
            print(f"赛前预检失败：{label}")
            return result.returncode
    print("== 赛前预检通过 ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
