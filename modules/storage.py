from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "customers.json"


def ensure_data_file() -> None:
    """Tạo thư mục data và file customers.json nếu chưa tồn tại."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_customers() -> List[Dict[str, Any]]:
    """Đọc danh sách khách hàng từ data/customers.json."""
    ensure_data_file()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_customers(customers: List[Dict[str, Any]]) -> None:
    """Ghi danh sách khách hàng vào data/customers.json."""
    ensure_data_file()
    DATA_FILE.write_text(
        json.dumps(customers, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
