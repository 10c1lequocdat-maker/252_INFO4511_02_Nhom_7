from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

PRODUCTS = ["meInvoice", "MISA SME", "MISA AMIS", "Bamboo"]
PACKAGES = ["Standard", "Professional", "Enterprise"]
CUSTOMER_TYPES = ["Cá nhân", "Doanh nghiệp"]
USAGE_DURATION_TYPES = ["Có thời hạn", "Vĩnh viễn"]
SERVICE_STATUS_ALL = ["Tất cả", "Hoạt động", "Sắp hết hạn", "Hết hạn", "Đã xóa"]


# =========================
# 1. CHUẨN HÓA DỮ LIỆU
# =========================

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_spaces(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def remove_accents(text: Any) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def normalize_keyword(text: Any) -> str:
    return remove_accents(normalize_spaces(text)).lower()


def digits_only(text: Any) -> str:
    return re.sub(r"\D", "", str(text or ""))


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    value = normalize_spaces(value)
    if not value or value == "Vĩnh viễn":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


# =========================
# 2. TRẠNG THÁI VÀ DANH MỤC
# =========================

def parse_customer_no(customer_id: Any) -> int:
    match = re.search(r"KH(\d+)$", str(customer_id or "").upper())
    return int(match.group(1)) if match else 0


def generate_next_customer_id(customers: List[Dict[str, Any]]) -> str:
    """Sinh mã KH dựa trên mã lớn nhất từng tồn tại, kể cả bản ghi đã xóa."""
    max_no = max([parse_customer_no(c.get("customer_id", "")) for c in customers] or [0])
    return f"KH{max_no + 1:03d}"


def calculate_payment_status(balance: Any) -> str:
    balance = to_float(balance)
    if balance == 0:
        return "Đã thanh toán"
    if balance > 0:
        return "Chưa thanh toán"
    return f"Đã thanh toán (Dư: {abs(balance):,.0f} VND)"


def calculate_service_status(expiry_date: Any, usage_duration_type: str = "Có thời hạn") -> str:
    if usage_duration_type == "Vĩnh viễn":
        return "Hoạt động"

    exp = parse_date(expiry_date)
    if not exp:
        return "Hết hạn"

    today = date.today()
    if exp < today:
        return "Hết hạn"
    if (exp - today).days <= 30:
        return "Sắp hết hạn"
    return "Hoạt động"


def enrich_customer(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Tạo bản sao khách hàng kèm trạng thái dịch vụ/tài chính được tính động."""
    c = dict(customer)
    balance = to_float(c.get("balance", 0))

    if c.get("is_deleted", False):
        c["service_status"] = "Đã xóa"
    else:
        c["service_status"] = calculate_service_status(
            c.get("expiry_date", ""),
            c.get("usage_duration_type", "Có thời hạn"),
        )

    c["payment_status"] = calculate_payment_status(balance)
    c["balance"] = balance
    return c


def active_customers(customers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in customers if not c.get("is_deleted", False)]


# =========================
# 3. RÀNG BUỘC VÀ KIỂM TRA DỮ LIỆU
# =========================

def phone_is_valid(phone: Any) -> bool:
    phone_digits = digits_only(phone)
    return len(phone_digits) == 10 and phone_digits.startswith("0")


def email_is_valid(email: Any) -> bool:
    email = normalize_spaces(email)
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}$", email))


def tax_code_is_valid(tax_code: Any) -> bool:
    tax_code = normalize_spaces(tax_code)
    if not tax_code:
        return True
    return len(digits_only(tax_code)) in (10, 12, 13)


def validate_date_range(start_date_value: Any, expiry_date_value: Any, usage_duration_type: str = "Có thời hạn") -> Optional[str]:
    """Kiểm tra ngày bắt đầu / ngày hết hạn. Trả về None nếu hợp lệ."""
    if usage_duration_type == "Vĩnh viễn":
        return None

    start = parse_date(start_date_value)
    expiry = parse_date(expiry_date_value)
    if not start:
        return "Ngày bắt đầu không hợp lệ."
    if not expiry:
        return "Ngày hết hạn không hợp lệ."
    if expiry <= start:
        return "Ngày hết hạn phải lớn hơn ngày bắt đầu."
    return None


def validate_balance(balance: Any) -> Optional[str]:
    try:
        if float(balance) < 0:
            return "Công nợ không được nhỏ hơn 0."
    except (TypeError, ValueError):
        return "Công nợ phải là số."
    return None


def validate_field(field_name: str, value: Any, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    context = context or {}
    text_value = normalize_spaces(value)

    if field_name == "customer_name":
        if not text_value:
            return "Tên khách hàng không được để trống."
        if len(text_value) < 2:
            return "Tên khách hàng phải có ít nhất 2 ký tự."
        return None

    if field_name == "phone":
        if not phone_is_valid(value):
            return "Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0."
        return None

    elif field_name == "email":
        if not str(value).strip():
            return "Email không được để trống."
        if not email_is_valid(value):
            return "Email không đúng định dạng. Ví dụ đúng: abc@gmail.com"
        return None

    if field_name == "address":
        if not text_value:
            return "Địa chỉ không được để trống."
        if len(text_value) < 5:
            return "Địa chỉ phải có ít nhất 5 ký tự."
        if len(text_value) > 250:
            return "Địa chỉ không được vượt quá 250 ký tự."
        return None

    if field_name == "representative":
        if context.get("customer_type") == "Doanh nghiệp" and not text_value:
            return "Khách hàng Doanh nghiệp bắt buộc nhập người đại diện."
        return None

    if field_name == "tax_code":
        if context.get("customer_type") == "Doanh nghiệp" and not text_value:
            return "Khách hàng Doanh nghiệp bắt buộc nhập mã số thuế."
        if text_value and not tax_code_is_valid(text_value):
            return "Mã số thuế phải gồm 10, 12 hoặc 13 chữ số."
        return None

    if field_name == "customer_type":
        if text_value not in CUSTOMER_TYPES:
            return "Loại khách hàng không hợp lệ."
        return None

    if field_name == "product_service":
        if text_value not in PRODUCTS:
            return "Sản phẩm cung cấp không hợp lệ."
        return None

    if field_name == "service_package":
        if text_value not in PACKAGES:
            return "Gói dịch vụ không hợp lệ."
        return None

    if field_name == "usage_duration_type":
        if text_value not in USAGE_DURATION_TYPES:
            return "Thời hạn sử dụng không hợp lệ."
        return None

    if field_name == "balance":
        return validate_balance(value)

    if field_name == "date_range":
        return validate_date_range(
            context.get("start_date"),
            context.get("expiry_date"),
            context.get("usage_duration_type", "Có thời hạn"),
        )

    return None


def get_customer_duplicate_error(
    customer: Dict[str, Any],
    customers: List[Dict[str, Any]],
    current_id: Optional[str] = None,
) -> Optional[str]:
    phone = digits_only(customer.get("phone", ""))
    name = normalize_keyword(customer.get("customer_name", ""))
    product = customer.get("product_service", "")
    package = customer.get("service_package", "")

    if not phone:
        return None

    for c in active_customers(customers):
        if current_id and c.get("customer_id") == current_id:
            continue

        if digits_only(c.get("phone", "")) != phone:
            continue

        same_name = normalize_keyword(c.get("customer_name", "")) == name
        same_product = c.get("product_service") == product
        same_package = c.get("service_package") == package

        if not same_name:
            return "Số điện thoại này đã tồn tại với một khách hàng khác tên."
        if same_name and same_product and same_package:
            return "Khách hàng đã tồn tại với cùng tên, số điện thoại, sản phẩm và gói dịch vụ."

    return None


def validate_customer_record(
    customer: Dict[str, Any],
    customers: List[Dict[str, Any]],
    current_id: Optional[str] = None,
) -> List[str]:
    errors: List[str] = []

    field_context = {"customer_type": customer.get("customer_type", "")}
    fields = [
        ("customer_name", customer.get("customer_name")),
        ("phone", customer.get("phone")),
        ("email", customer.get("email")),
        ("address", customer.get("address")),
        ("representative", customer.get("representative")),
        ("tax_code", customer.get("tax_code")),
        ("customer_type", customer.get("customer_type")),
        ("product_service", customer.get("product_service")),
        ("service_package", customer.get("service_package")),
        ("usage_duration_type", customer.get("usage_duration_type")),
        ("balance", customer.get("balance")),
    ]

    if not customer.get("customer_id"):
        errors.append("Mã khách hàng không được để trống.")

    for field_name, value in fields:
        message = validate_field(field_name, value, field_context)
        if message:
            errors.append(message)

    date_message = validate_field(
        "date_range",
        None,
        {
            "usage_duration_type": customer.get("usage_duration_type", "Có thời hạn"),
            "start_date": customer.get("start_date", ""),
            "expiry_date": customer.get("expiry_date", ""),
        },
    )
    if date_message:
        errors.append(date_message)

    if len(str(customer.get("notes", "") or "")) > 500:
        errors.append("Ghi chú không được vượt quá 500 ký tự.")

    duplicate_error = get_customer_duplicate_error(customer, customers, current_id=current_id)
    if duplicate_error:
        errors.append(duplicate_error)

    # Loại bỏ lỗi trùng để kết quả gọn hơn
    unique_errors: List[str] = []
    for error in errors:
        if error not in unique_errors:
            unique_errors.append(error)
    return unique_errors


validate_customer = validate_customer_record


# =========================
# 4. TẠO / CẬP NHẬT / XÓA / TÌM KIẾM
# =========================

def build_customer_record(
    customer_id: str,
    customer_name: str,
    customer_type: str,
    phone: str,
    email: str,
    address: str,
    representative: str,
    tax_code: str,
    product_service: str,
    service_package: str,
    usage_duration_type: str,
    start_date_value: Optional[date],
    expiry_date_value: Optional[date],
    balance: Any,
    notes: str,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
    is_deleted: bool = False,
    deleted_at: Optional[str] = None,
) -> Dict[str, Any]:
    customer_id = normalize_spaces(customer_id).upper()
    customer_name = normalize_spaces(customer_name)
    customer_type = normalize_spaces(customer_type)
    phone = digits_only(phone)
    email = normalize_spaces(email).lower()
    address = normalize_spaces(address)
    representative = normalize_spaces(representative) or None
    tax_code = digits_only(tax_code) or None
    product_service = normalize_spaces(product_service)
    service_package = normalize_spaces(service_package)
    usage_duration_type = normalize_spaces(usage_duration_type) or "Có thời hạn"
    notes = normalize_spaces(notes)
    balance = to_float(balance)

    if customer_type == "Cá nhân":
        representative = representative or None
        tax_code = tax_code or None

    if usage_duration_type == "Vĩnh viễn":
        start_date_str = ""
        expiry_date_str = "Vĩnh viễn"
    else:
        start_date_str = start_date_value.strftime("%Y-%m-%d") if isinstance(start_date_value, date) else ""
        expiry_date_str = expiry_date_value.strftime("%Y-%m-%d") if isinstance(expiry_date_value, date) else ""

    current_time = now_str()
    return {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_type": customer_type,
        "phone": phone,
        "email": email,
        "address": address,
        "representative": representative,
        "tax_code": tax_code,
        "product_service": product_service,
        "service_package": service_package,
        "usage_duration_type": usage_duration_type,
        "start_date": start_date_str,
        "expiry_date": expiry_date_str,
        "service_status": calculate_service_status(expiry_date_str, usage_duration_type),
        "payment_status": calculate_payment_status(balance),
        "balance": balance,
        "notes": notes,
        "created_at": created_at or current_time,
        "updated_at": updated_at or current_time,
        "is_deleted": bool(is_deleted),
        "deleted_at": deleted_at,
    }


def find_customer_by_id(customers: List[Dict[str, Any]], customer_id: str) -> Optional[Dict[str, Any]]:
    customer_id = normalize_spaces(customer_id).upper()
    for c in customers:
        if c.get("customer_id") == customer_id:
            return c
    return None


def replace_customer_by_id(customers: List[Dict[str, Any]], customer_id: str, new_record: Dict[str, Any]) -> bool:
    customer_id = normalize_spaces(customer_id).upper()
    for idx, c in enumerate(customers):
        if c.get("customer_id") == customer_id:
            customers[idx] = new_record
            return True
    return False


def can_delete_customer(customer: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    if not customer:
        return False, "Không tìm thấy khách hàng."
    if customer.get("is_deleted", False):
        return False, "Khách hàng này đã bị xóa mềm trước đó."

    c = enrich_customer(customer)
    if c.get("service_status") in ("Hoạt động", "Sắp hết hạn"):
        return False, "Không thể xóa khách hàng khi dịch vụ còn Hoạt động hoặc Sắp hết hạn."

    if to_float(c.get("balance", 0)) != 0:
        return False, f"Không thể xóa vì khách hàng còn công nợ: {to_float(c.get('balance', 0)):,.0f} VND."

    return True, "Có thể xóa khách hàng."


def soft_delete_customer(customers: List[Dict[str, Any]], customer_id: str) -> Tuple[bool, str]:
    customer = find_customer_by_id(customers, customer_id)
    ok, message = can_delete_customer(customer)
    if not ok:
        return False, message

    customer["is_deleted"] = True
    customer["deleted_at"] = now_str()
    customer["updated_at"] = now_str()
    return True, f"Đã xóa mềm khách hàng {customer.get('customer_id')} - {customer.get('customer_name')}."


def search_customers(
    customers: List[Dict[str, Any]],
    keyword: str,
    status_filter: str = "Tất cả",
    include_deleted: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    raw_keyword = normalize_spaces(keyword)
    key = normalize_keyword(raw_keyword)
    phone_key = digits_only(raw_keyword)

    if not key and not phone_key:
        return [], "Vui lòng nhập từ khóa tìm kiếm."

    is_email_keyword = "@" in raw_keyword or "." in raw_keyword
    keyword_results: List[Dict[str, Any]] = []

    for customer in customers:
        c = enrich_customer(customer)
        if not include_deleted and c.get("is_deleted"):
            continue

        matched = (
            key in normalize_keyword(c.get("customer_id", ""))
            or key in normalize_keyword(c.get("customer_name", ""))
            or (bool(phone_key) and phone_key in digits_only(c.get("phone", "")))
            or (is_email_keyword and key in normalize_keyword(c.get("email", "")))
        )

        if matched:
            keyword_results.append(c)

    if not keyword_results:
        return [], "Không tìm thấy khách hàng phù hợp với từ khóa đã nhập."

    final_results = [
        c for c in keyword_results
        if status_filter == "Tất cả" or c.get("service_status") == status_filter
    ]

    if not final_results:
        return [], f"Tìm thấy {len(keyword_results)} khách hàng khớp từ khóa, nhưng không phù hợp với trạng thái đã chọn."

    return final_results, ""


def filter_customers(
    customers: List[Dict[str, Any]],
    keyword: str = "",
    customer_type: str = "Tất cả",
    service_status: str = "Tất cả",
    include_deleted: bool = False,
) -> List[Dict[str, Any]]:
    key = normalize_keyword(keyword)
    result: List[Dict[str, Any]] = []

    for customer in customers:
        c = enrich_customer(customer)
        if not include_deleted and c.get("is_deleted"):
            continue
        if customer_type != "Tất cả" and c.get("customer_type") != customer_type:
            continue
        if service_status != "Tất cả" and c.get("service_status") != service_status:
            continue
        if key and key not in normalize_keyword(c.get("customer_id", "")) and key not in normalize_keyword(c.get("customer_name", "")):
            continue
        result.append(c)

    return result


def customers_to_rows(customers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, customer in enumerate([enrich_customer(c) for c in customers], start=1):
        rows.append({
            "STT": idx,
            "Mã KH": customer.get("customer_id", ""),
            "Tên khách hàng": customer.get("customer_name", ""),
            "Loại KH": customer.get("customer_type", ""),
            "SĐT": customer.get("phone", ""),
            "Email": customer.get("email", ""),
            "Sản phẩm": customer.get("product_service", ""),
            "Gói DV": customer.get("service_package", ""),
            "Thời hạn": customer.get("usage_duration_type", ""),
            "Ngày bắt đầu": customer.get("start_date", ""),
            "Ngày hết hạn": customer.get("expiry_date", ""),
            "Trạng thái": customer.get("service_status", ""),
            "Thanh toán": customer.get("payment_status", ""),
            "Công nợ": f"{to_float(customer.get('balance', 0)):,.0f} VND",
            "Đã xóa": bool(customer.get("is_deleted", False)),
        })
    return rows
