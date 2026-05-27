from __future__ import annotations
from typing import Any, Dict, List, Optional
from modules.customer_service import (
    CUSTOMER_TYPES, PACKAGES, PRODUCTS, SERVICE_STATUS_ALL, USAGE_DURATION_TYPES,
    active_customers, build_customer_record, customers_to_rows, enrich_customer,
    find_customer_by_id, generate_next_customer_id, get_customer_duplicate_error,
    parse_date, replace_customer_by_id, search_customers, soft_delete_customer,
    validate_customer_record, validate_field,
)
from modules.storage import load_customers, save_customers

# GIAO DIỆN DÒNG LỆNH
def choose_from_list(title: str, options: List[str], default: Optional[str] = None) -> str:
    while True:
        print(f"\n{title}:")
        for i, item in enumerate(options, start=1):
            print(f"{i}. {item}")
        suffix = f" [{default}]" if default else ""
        choice = input(f"Chọn số thứ tự hoặc nhập tên{suffix}: ").strip()
        if not choice and default in options:
            return default
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        for item in options:
            if choice.lower() == item.lower():
                return item
        print("⚠️ Lựa chọn không hợp lệ. Vui lòng chọn lại.")

def prompt_valid(field_name: str, label: str, default: Any = "", context: Optional[Dict[str, Any]] = None, allow_empty_default: bool = False) -> str:
    """Nhập một trường và kiểm tra ngay bằng validate_field trong customer_service.py."""
    while True:
        suffix = f" [{default}]" if default not in (None, "") else ""
        value = input(f"{label}{suffix}: ").strip()
        if value == "" and allow_empty_default:
            value = default or ""
        error = validate_field(field_name, value, context or {})
        if error:
            print(f"⚠️ {error}")
            continue
        return value

def prompt_date_range(usage_duration_type: str, old_start: Any = "", old_expiry: Any = ""):
    """Nhập ngày và kiểm tra ngay bằng validate_field('date_range')."""
    if usage_duration_type == "Vĩnh viễn":
        return None, None

    while True:
        start_raw = input(f"Ngày bắt đầu YYYY-MM-DD" + (f" [{old_start}]" if old_start else "") + ": ").strip() or old_start
        expiry_raw = input(f"Ngày hết hạn YYYY-MM-DD" + (f" [{old_expiry}]" if old_expiry else "") + ": ").strip() or old_expiry
        start_date = parse_date(start_raw)
        expiry_date = parse_date(expiry_raw)
        error = validate_field("date_range", None, {"usage_duration_type": usage_duration_type, "start_date": start_date, "expiry_date": expiry_date})
        if error:
            print(f"⚠️ {error}")
            continue
        return start_date, expiry_date

def prompt_balance(default: Any = 0) -> float:
    while True:
        raw = input(f"Công nợ VND [{default}]: ").strip()
        value = default if raw == "" else raw
        error = validate_field("balance", value)
        if error:
            print(f"⚠️ {error}")
            continue
        return float(value)

def print_errors(errors: List[str]) -> None:
    print("\nDữ liệu chưa hợp lệ:")
    for error in errors:
        print(f"- {error}")

def print_table(customers: List[Dict[str, Any]]) -> None:
    if not customers:
        print("Không có dữ liệu để hiển thị.")
        return
    rows = customers_to_rows(customers)
    print("\n" + "-" * 150)
    print(f"{'STT':<5}{'Mã KH':<10}{'Tên khách hàng':<25}{'Loại KH':<15}{'SĐT':<15}{'Email':<28}{'Sản phẩm':<14}{'Gói DV':<14}{'Trạng thái':<15}{'Công nợ':<15}")
    print("-" * 150)
    for row in rows:
        print(f"{row.get('STT',''):<5}{row.get('Mã KH',''):<10}{row.get('Tên khách hàng',''):<25}{row.get('Loại KH',''):<15}{row.get('SĐT',''):<15}{row.get('Email',''):<28}{row.get('Sản phẩm',''):<14}{row.get('Gói DV',''):<14}{row.get('Trạng thái',''):<15}{row.get('Công nợ',''):<15}")
    print("-" * 150)

def print_detail(customer: Optional[Dict[str, Any]]) -> None:
    if not customer:
        print("Không có thông tin khách hàng.")
        return
    c = enrich_customer(customer)
    print("\nTHÔNG TIN CHI TIẾT KHÁCH HÀNG")
    print("-" * 70)
    fields = [
        ("Mã khách hàng", c.get("customer_id", "")),
        ("Tên khách hàng", c.get("customer_name", "")),
        ("Loại khách hàng", c.get("customer_type", "")),
        ("Số điện thoại", c.get("phone", "")),
        ("Email", c.get("email", "")),
        ("Địa chỉ", c.get("address", "")),
        ("Người đại diện", c.get("representative") or ""),
        ("Mã số thuế", c.get("tax_code") or ""),
        ("Sản phẩm", c.get("product_service", "")),
        ("Gói dịch vụ", c.get("service_package", "")),
        ("Thời hạn sử dụng", c.get("usage_duration_type", "")),
        ("Ngày bắt đầu", c.get("start_date", "")),
        ("Ngày hết hạn", c.get("expiry_date", "")),
        ("Trạng thái dịch vụ", c.get("service_status", "")),
        ("Trạng thái thanh toán", c.get("payment_status", "")),
        ("Công nợ", f"{float(c.get('balance',0) or 0):,.0f} VND"),
        ("Ghi chú", c.get("notes", "")),
        ("created_at", c.get("created_at", "")),
        ("updated_at", c.get("updated_at", "")),
        ("is_deleted", c.get("is_deleted", False)),
        ("deleted_at", c.get("deleted_at") or ""),
    ]
    for label, value in fields:
        print(f"{label:<25}: {value}")
    print("-" * 70)

def select_customer_from_table(active_list: List[Dict[str, Any]], all_customers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Hiển thị bảng và cho chọn khách hàng bằng STT hoặc mã KH."""
    print_table(active_list)
    while True:
        choice = input("Nhập STT hoặc mã khách hàng cần chọn [Enter để hủy]: ").strip().upper()
        if choice == "":
            return None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(active_list):
                return find_customer_by_id(all_customers, active_list[index - 1].get("customer_id", ""))
        customer = find_customer_by_id(all_customers, choice)
        if customer and not customer.get("is_deleted", False):
            return customer
        print("⚠️ Lựa chọn không hợp lệ. Vui lòng nhập đúng STT hoặc mã khách hàng trong bảng.")
        
def show_update_field_menu(data: Dict[str, Any]) -> None:
    """Hiển thị bảng các trường có thể sửa trong code thuần."""
    print("\nBẢNG THÔNG TIN CÓ THỂ CẬP NHẬT")
    print("-" * 90)
    print(f"{'STT':<6}{'Trường thông tin':<28}{'Giá trị hiện tại'}")
    print("-" * 90)
    rows = [
        ("1", "Tên khách hàng", data.get("customer_name", "")),
        ("2", "Loại khách hàng", data.get("customer_type", "")),
        ("3", "Số điện thoại", data.get("phone", "")),
        ("4", "Email", data.get("email", "")),
        ("5", "Địa chỉ", data.get("address", "")),
        ("6", "Người đại diện", data.get("representative") or ""),
        ("7", "Mã số thuế", data.get("tax_code") or ""),
        ("8", "Sản phẩm cung cấp", data.get("product_service", "")),
        ("9", "Gói dịch vụ", data.get("service_package", "")),
        ("10", "Thời hạn/ngày sử dụng", f"{data.get('usage_duration_type','')} | {data.get('start_date','')} → {data.get('expiry_date','')}"),
        ("11", "Công nợ", f"{float(data.get('balance', 0) or 0):,.0f} VND"),
        ("12", "Ghi chú", data.get("notes", "")),
    ]
    for no, label, value in rows:
        print(f"{no:<6}{label:<28}{value}")
    print("-" * 90)
    print("13. Lưu cập nhật")
    print("0. Hủy cập nhật")

def add_customer_cli() -> None:
    customers = load_customers()
    new_id = generate_next_customer_id(customers)
    print(f"\nMã khách hàng được sinh tự động: {new_id}")

    customer_name = prompt_valid("customer_name", "Tên khách hàng")
    customer_type = choose_from_list("Loại khách hàng", CUSTOMER_TYPES)
    phone = prompt_valid("phone", "Số điện thoại")
    email = prompt_valid("email", "Email")
    address = prompt_valid("address", "Địa chỉ")
    representative = prompt_valid("representative", "Người đại diện", context={"customer_type": customer_type})
    tax_code = prompt_valid("tax_code", "Mã số thuế", context={"customer_type": customer_type})
    product_service = choose_from_list("Sản phẩm cung cấp", PRODUCTS)
    service_package = choose_from_list("Gói dịch vụ", PACKAGES)

    duplicate_error = get_customer_duplicate_error(
        {"customer_name": customer_name, "phone": phone, "product_service": product_service, "service_package": service_package},
        customers,
    )
    if duplicate_error:
        print(f"⚠️ {duplicate_error}")
        return

    usage_duration_type = choose_from_list("Thời hạn sử dụng", USAGE_DURATION_TYPES)
    start_date_value, expiry_date_value = prompt_date_range(usage_duration_type)
    balance = prompt_balance(0)
    notes = input("Ghi chú: ").strip()

    record = build_customer_record(new_id, customer_name, customer_type, phone, email, address, representative, tax_code, product_service, service_package, usage_duration_type, start_date_value, expiry_date_value, balance, notes)
    errors = validate_customer_record(record, customers)
    if errors:
        print_errors(errors)
        return

    customers.append(record)
    save_customers(customers)
    print(f"\n✅ Thêm khách hàng {new_id} thành công! Dữ liệu đã lưu. ")
    print_detail(record)


def update_customer_cli() -> None:
   
    customers = load_customers()
    active_list = active_customers(customers)
    if not active_list:
        print("Không có khách hàng đang hoạt động để cập nhật.")
        return

    print("\nDANH SÁCH KHÁCH HÀNG ĐANG HOẠT ĐỘNG")
    current = select_customer_from_table(active_list, customers)
    if not current:
        print("Đã hủy thao tác cập nhật.")
        return

    data = dict(enrich_customer(current))
    print_detail(data)

    while True:
        show_update_field_menu(data)
        choice = input("Chọn STT trường thông tin muốn sửa: ").strip()

        if choice == "0":
            print("Đã hủy cập nhật.")
            return

        elif choice == "1":
            data["customer_name"] = prompt_valid("customer_name", "Tên khách hàng", data.get("customer_name", ""), allow_empty_default=True)

        elif choice == "2":
            data["customer_type"] = choose_from_list("Loại khách hàng", CUSTOMER_TYPES, data.get("customer_type", "Cá nhân"))
            rep_error = validate_field("representative", data.get("representative") or "", {"customer_type": data["customer_type"]})
            tax_error = validate_field("tax_code", data.get("tax_code") or "", {"customer_type": data["customer_type"]})
            if rep_error:
                print(f"⚠️ {rep_error}")
            if tax_error:
                print(f"⚠️ {tax_error}")

        elif choice == "3":
            data["phone"] = prompt_valid("phone", "Số điện thoại", data.get("phone", ""), allow_empty_default=True)

        elif choice == "4":
            data["email"] = prompt_valid("email", "Email", data.get("email", ""), allow_empty_default=True)

        elif choice == "5":
            data["address"] = prompt_valid("address", "Địa chỉ", data.get("address", ""), allow_empty_default=True)

        elif choice == "6":
            data["representative"] = prompt_valid(
                "representative",
                "Người đại diện",
                data.get("representative") or "",
                {"customer_type": data.get("customer_type", "")},
                allow_empty_default=True,
            )

        elif choice == "7":
            data["tax_code"] = prompt_valid(
                "tax_code",
                "Mã số thuế",
                data.get("tax_code") or "",
                {"customer_type": data.get("customer_type", "")},
                allow_empty_default=True,
            )

        elif choice == "8":
            data["product_service"] = choose_from_list("Sản phẩm cung cấp", PRODUCTS, data.get("product_service", PRODUCTS[0]))

        elif choice == "9":
            data["service_package"] = choose_from_list("Gói dịch vụ", PACKAGES, data.get("service_package", PACKAGES[0]))

        elif choice == "10":
            data["usage_duration_type"] = choose_from_list("Thời hạn sử dụng", USAGE_DURATION_TYPES, data.get("usage_duration_type", "Có thời hạn"))
            start_date_value, expiry_date_value = prompt_date_range(
                data["usage_duration_type"],
                data.get("start_date", ""),
                data.get("expiry_date", ""),
            )
            data["start_date_value"] = start_date_value
            data["expiry_date_value"] = expiry_date_value
            data["start_date"] = start_date_value.strftime("%Y-%m-%d") if start_date_value else ""
            data["expiry_date"] = expiry_date_value.strftime("%Y-%m-%d") if expiry_date_value else "Vĩnh viễn"

        elif choice == "11":
            data["balance"] = prompt_balance(float(data.get("balance", 0) or 0))

        elif choice == "12":
            data["notes"] = input(f"Ghi chú [{data.get('notes','')}]: ").strip() or data.get("notes", "")

        elif choice == "13":
            if data.get("usage_duration_type") == "Có thời hạn":
                start_date_value = data.get("start_date_value") or parse_date(data.get("start_date", ""))
                expiry_date_value = data.get("expiry_date_value") or parse_date(data.get("expiry_date", ""))
            else:
                start_date_value = None
                expiry_date_value = None

            updated = build_customer_record(
                current.get("customer_id", ""),
                data.get("customer_name", ""),
                data.get("customer_type", ""),
                data.get("phone", ""),
                data.get("email", ""),
                data.get("address", ""),
                data.get("representative") or "",
                data.get("tax_code") or "",
                data.get("product_service", ""),
                data.get("service_package", ""),
                data.get("usage_duration_type", "Có thời hạn"),
                start_date_value,
                expiry_date_value,
                data.get("balance", 0),
                data.get("notes", ""),
                created_at=current.get("created_at"),
                is_deleted=current.get("is_deleted", False),
                deleted_at=current.get("deleted_at"),
            )
            
            errors = validate_customer_record(updated, customers, current_id=current.get("customer_id"))
            if errors:
                print_errors(errors)
                continue

            confirm = input("Xác nhận lưu cập nhật? [y/N]: ").strip().lower()
            if confirm != "y":
                print("Chưa lưu thay đổi.")
                continue

            replace_customer_by_id(customers, current.get("customer_id", ""), updated)
            save_customers(customers)
            print("✅ Cập nhật khách hàng thành công! Dữ liệu đã lưu vào data/customers.json.")
            print_detail(updated)
            return
        else:
            print("⚠️ Lựa chọn không hợp lệ. Vui lòng chọn lại.")
            continue

        print("✅ Đã cập nhật tạm thời trường vừa chọn. Chọn 13 để lưu vào file JSON.")

def search_customer_cli() -> None:
    customers = load_customers()
    keyword = input("Nhập từ khóa tìm kiếm: ").strip()
    status_filter = choose_from_list("Trạng thái", SERVICE_STATUS_ALL, "Tất cả")
    include_deleted = input("Bao gồm khách hàng đã xóa? [y/N]: ").strip().lower() == "y"
    results, message = search_customers(customers, keyword, status_filter, include_deleted)
    if message and not results:
        print(message)
        return
    print(f"Kết quả tìm kiếm: {len(results)} bản ghi")
    print_table(results)

def delete_customer_cli() -> None:
    customers = load_customers()
    active_list = active_customers(customers)
    if not active_list:
        print("Không có khách hàng đang hoạt động để xóa.")
        return
    print_table(active_list)
    customer_id = input("Nhập mã khách hàng cần xóa: ").strip().upper()
    customer = find_customer_by_id(customers, customer_id)
    print_detail(customer)
    if input("Xác nhận xóa mềm khách hàng này? [y/N]: ").strip().lower() != "y":
        print("Đã hủy thao tác xóa.")
        return
    ok, message = soft_delete_customer(customers, customer_id)
    if ok:
        save_customers(customers)
        print(f"✅ {message}")
        print("Dữ liệu đã lưu vào data/customers.json.")
    else:
        print(f"⚠️ {message}")

def list_customer_cli() -> None:
    customers = load_customers()
    result = [enrich_customer(c) for c in active_customers(customers)]
    if not result:
        print("Không có khách hàng nào trên hệ thống.")
        return
    print(f"Tổng số khách hàng đang hoạt động: {len(result)}")
    print_table(result)
    if input("Xem chi tiết một khách hàng? [y/N]: ").strip().lower() == "y":
        customer_id = input("Nhập mã khách hàng: ").strip().upper()
        print_detail(find_customer_by_id(result, customer_id))

def print_menu() -> None:
    print("\n" + "=" * 70)
    print("CHƯƠNG TRÌNH QUẢN LÝ KHÁCH HÀNG MISA")
    print("=" * 70)
    print("1. Nhập thông tin khách hàng")
    print("2. Cập nhật thông tin khách hàng")
    print("3. Tìm kiếm thông tin khách hàng")
    print("4. Xóa thông tin khách hàng")
    print("5. Xem danh sách thông tin khách hàng")
    print("0. Thoát")
    print("=" * 70)


def main() -> None:
    actions = {"1": add_customer_cli, "2": update_customer_cli, "3": search_customer_cli, "4": delete_customer_cli, "5": list_customer_cli}
    while True:
        print_menu()
        choice = input("Chọn chức năng: ").strip()
        if choice == "0":
            print("Kết thúc chương trình.")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Lựa chọn không hợp lệ. Vui lòng chọn lại.")

if __name__ == "__main__":
    main()
