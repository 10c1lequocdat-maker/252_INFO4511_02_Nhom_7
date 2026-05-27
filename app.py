from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from modules.customer_service import (
    CUSTOMER_TYPES, PACKAGES, PRODUCTS, SERVICE_STATUS_ALL, USAGE_DURATION_TYPES,
    active_customers, build_customer_record, customers_to_rows, enrich_customer,
    find_customer_by_id, generate_next_customer_id, parse_date, replace_customer_by_id,
    search_customers, soft_delete_customer, validate_customer_record, validate_field,
)
from modules.storage import load_customers, save_customers

st.set_page_config(page_title="Quản lý khách hàng MISA", layout="wide")

st.markdown("""
<style>
.main-title{background:linear-gradient(90deg,#0052cc,#0078d4);color:white;padding:18px 24px;border-radius:12px;text-align:center;font-size:30px;font-weight:700;margin-bottom:18px}.section-title{color:#0052cc;font-size:28px;font-weight:700;margin-bottom:16px}.detail-box{background:#f8fbff;border:1px solid #d6e4f5;border-radius:12px;padding:18px 20px;margin-top:14px}.note-box{background:#fff7e6;border:1px solid #ffd591;border-radius:10px;padding:12px 16px;margin-top:16px}.small-muted{color:#64748b;font-size:14px}div.stButton>button:first-child{border-radius:9px;font-weight:600}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">QUẢN LÝ KHÁCH HÀNG MISA</div>', unsafe_allow_html=True)
customers: List[Dict[str, Any]] = load_customers()

if "flash_success" in st.session_state:
    st.success(st.session_state.pop("flash_success"))
if "flash_error" in st.session_state:
    st.error(st.session_state.pop("flash_error"))


def show_error_once(errors: List[str], message: str | None) -> None:
    if message and message not in errors:
        errors.append(message)
        st.error(message)


def date_default(value: Any, fallback: date) -> date:
    return parse_date(value) or fallback


def render_customer_detail(customer: Dict[str, Any]) -> None:
    if not customer:
        st.info("Chưa có khách hàng để hiển thị chi tiết.")
        return
    c = enrich_customer(customer)
    st.markdown('<div class="detail-box">', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        for label, key in [
            ("Mã khách hàng", "customer_id"), ("Tên khách hàng", "customer_name"),
            ("Loại khách hàng", "customer_type"), ("Số điện thoại", "phone"),
            ("Email", "email"), ("Địa chỉ", "address"),
            ("Người đại diện", "representative"), ("Mã số thuế", "tax_code"),
        ]:
            st.write(f"**{label}:** {c.get(key) or ''}")
    with right:
        for label, key in [
            ("Sản phẩm", "product_service"), ("Gói dịch vụ", "service_package"),
            ("Thời hạn sử dụng", "usage_duration_type"), ("Ngày bắt đầu", "start_date"),
            ("Ngày hết hạn", "expiry_date"), ("Trạng thái dịch vụ", "service_status"),
            ("Trạng thái thanh toán", "payment_status"),
        ]:
            st.write(f"**{label}:** {c.get(key) or ''}")
        st.write(f"**Công nợ:** {float(c.get('balance', 0) or 0):,.0f} VND")
    st.write(f"**Ghi chú:** {c.get('notes', '')}")
    st.write(f"**created_at:** {c.get('created_at', '')} | **updated_at:** {c.get('updated_at', '')} | **deleted_at:** {c.get('deleted_at') or ''}")
    st.markdown('</div>', unsafe_allow_html=True)


with st.sidebar:
    st.markdown("## MISA")
    st.markdown("### Menu chức năng")
    menu = st.radio(
        "Chọn chức năng",
        ["Nhập thông tin khách hàng", "Cập nhật thông tin khách hàng", "Tìm kiếm thông tin khách hàng", "Xóa thông tin khách hàng", "Xem danh sách thông tin khách hàng"],
        label_visibility="collapsed",
    )


if menu == "Nhập thông tin khách hàng":
    st.markdown('<div class="section-title">Nhập thông tin khách hàng</div>', unsafe_allow_html=True)
    form_version = st.session_state.get("add_form_version", 0)
    new_id = generate_next_customer_id(customers)
    live_errors: List[str] = []
    st.info(f"Mã khách hàng được sinh tự động: **{new_id}**")

    st.subheader("1. Thông tin định danh và liên hệ")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Mã khách hàng", value=new_id, disabled=True, key=f"add_id_{form_version}")
    with c2:
        customer_name = st.text_input("Tên khách hàng *", placeholder="Nhập tên khách hàng", key=f"add_name_{form_version}")
        if customer_name:
            show_error_once(live_errors, validate_field("customer_name", customer_name))
    with c3:
        customer_type = st.selectbox("Loại khách hàng *", CUSTOMER_TYPES, key=f"add_type_{form_version}")

    c4, c5, c6 = st.columns(3)
    with c4:
        phone = st.text_input("Số điện thoại *", placeholder="Ví dụ: 0912345678", max_chars=10, key=f"add_phone_{form_version}")
        if phone:
            show_error_once(live_errors, validate_field("phone", phone))
    with c5:
        email = st.text_input("Email *", placeholder="Ví dụ: abc@gmail.com", key=f"add_email_{form_version}")
        if email:
            show_error_once(live_errors, validate_field("email", email))
    with c6:
        address = st.text_input("Địa chỉ *", placeholder="Nhập địa chỉ", max_chars=250, key=f"add_address_{form_version}")
        if address:
            show_error_once(live_errors, validate_field("address", address))

    c7, c8, c9 = st.columns(3)
    with c7:
        representative = st.text_input("Người đại diện", placeholder="Bắt buộc nếu là Doanh nghiệp", key=f"add_rep_{form_version}")
        if representative or customer_type == "Doanh nghiệp":
            msg = validate_field("representative", representative, {"customer_type": customer_type})
            if msg and representative:
                show_error_once(live_errors, msg)
            elif msg:
                st.warning(msg)
    with c8:
        tax_code = st.text_input("Mã số thuế", placeholder="10, 12 hoặc 13 chữ số", key=f"add_tax_{form_version}")
        if tax_code or customer_type == "Doanh nghiệp":
            msg = validate_field("tax_code", tax_code, {"customer_type": customer_type})
            if msg and tax_code:
                show_error_once(live_errors, msg)
            elif msg:
                st.warning(msg)
    with c9:
        st.markdown("<div class='small-muted'>Với khách hàng Cá nhân, người đại diện và mã số thuế có thể để trống.</div>", unsafe_allow_html=True)

    st.subheader("2. Thông tin dịch vụ sử dụng")
    d1, d2, d3 = st.columns(3)
    with d1:
        product_service = st.selectbox("Sản phẩm cung cấp *", PRODUCTS, key=f"add_product_{form_version}")
    with d2:
        service_package = st.selectbox("Gói dịch vụ *", PACKAGES, key=f"add_package_{form_version}")
    with d3:
        usage_duration_type = st.selectbox("Thời hạn sử dụng *", USAGE_DURATION_TYPES, key=f"add_usage_{form_version}")

    t1, t2, t3 = st.columns(3)
    if usage_duration_type == "Có thời hạn":
        with t1:
            start_date_value = st.date_input("Ngày bắt đầu *", value=date.today(), key=f"add_start_{form_version}")
        with t2:
            expiry_date_value = st.date_input("Ngày hết hạn *", value=date.today() + timedelta(days=365), key=f"add_expiry_{form_version}")
        with t3:
            msg = validate_field("date_range", None, {"usage_duration_type": usage_duration_type, "start_date": start_date_value, "expiry_date": expiry_date_value})
            if msg:
                show_error_once(live_errors, msg)
            else:
                st.success("Khoảng thời gian sử dụng hợp lệ.")
    else:
        start_date_value = None
        expiry_date_value = None
        with t1:
            st.success("Dịch vụ vĩnh viễn")
        with t2:
            st.info("Không cần nhập ngày bắt đầu/ngày hết hạn.")

    st.subheader("3. Thông tin tài chính")
    f1, f2 = st.columns([1, 2])
    with f1:
        balance = st.number_input("Công nợ (VND)", min_value=0, value=0, step=10000, format="%d", key=f"add_balance_{form_version}")
        show_error_once(live_errors, validate_field("balance", balance))
    with f2:
        notes = st.text_area("Ghi chú", max_chars=500, key=f"add_notes_{form_version}")

    save_clicked = st.button("Lưu khách hàng", type="primary")
    add_message_area = st.empty()
    if "add_success_message" in st.session_state:
        add_message_area.success(st.session_state.pop("add_success_message"))

    if save_clicked:
        record = build_customer_record(new_id, customer_name, customer_type, phone, email, address, representative, tax_code, product_service, service_package, usage_duration_type, start_date_value, expiry_date_value, balance, notes)
        errors = validate_customer_record(record, customers)
        if live_errors:
            st.error("Vui lòng sửa các lỗi đang hiển thị trước khi lưu khách hàng.")
        elif errors:
            for err in errors:
                st.error(err)
        else:
            customers.append(record)
            save_customers(customers)
            st.session_state["add_success_message"] = f"Thêm khách hàng {new_id} thành công! Dữ liệu đã được lưu vào file JSON."
            st.session_state["add_form_version"] = form_version + 1
            st.rerun()


elif menu == "Cập nhật thông tin khách hàng":
    st.markdown('<div class="section-title">Cập nhật thông tin khách hàng</div>', unsafe_allow_html=True)
    active_list = [enrich_customer(c) for c in active_customers(customers)]

    if not active_list:
        st.info("Chưa có khách hàng đang hoạt động để cập nhật.")
    else:
        st.markdown("### Bước 1: Nhập mã khách hàng cần cập nhật")
        st.caption("Nhập đúng mã khách hàng, ví dụ: KH001. Bảng bên dưới chỉ dùng để tham khảo mã khách hàng, không cần tick chọn.")

        st.dataframe(
            pd.DataFrame(customers_to_rows(active_list)),
            use_container_width=True,
            hide_index=True,
        )

        selected_id = st.text_input(
            "Nhập mã khách hàng muốn xem chi tiết/cập nhật",
            placeholder="Ví dụ: KH001",
            key="update_customer_id_input",
        ).strip().upper()

        if not selected_id:
            st.info("Vui lòng nhập mã khách hàng để xem chi tiết và cập nhật thông tin.")
            st.stop()

        current = find_customer_by_id(active_list, selected_id)

        if not current:
            deleted_or_other = find_customer_by_id(customers, selected_id)
            if deleted_or_other and deleted_or_other.get("is_deleted"):
                st.warning("Khách hàng này đã bị xóa mềm nên không thể cập nhật.")
            else:
                st.error("Không tìm thấy khách hàng đang hoạt động với mã đã nhập. Vui lòng kiểm tra lại mã khách hàng.")
            st.stop()

        c = enrich_customer(current)
        st.markdown("### Bước 2: Thông tin khách hàng được chọn")
        render_customer_detail(c)
        update_errors: List[str] = []

        st.markdown("### Bước 3: Chỉnh sửa thông tin khách hàng")

        u1, u2, u3 = st.columns(3)
        with u1:
            st.text_input("Mã khách hàng", value=c.get("customer_id", ""), disabled=True, key=f"update_id_{selected_id}")
        with u2:
            customer_name = st.text_input("Tên khách hàng *", value=c.get("customer_name", ""), key=f"update_name_{selected_id}")
            show_error_once(update_errors, validate_field("customer_name", customer_name))
        with u3:
            customer_type = st.selectbox(
                "Loại khách hàng *",
                CUSTOMER_TYPES,
                index=CUSTOMER_TYPES.index(c.get("customer_type", "Cá nhân")) if c.get("customer_type") in CUSTOMER_TYPES else 0,
                key=f"update_type_{selected_id}",
            )

        u4, u5, u6 = st.columns(3)
        with u4:
            phone = st.text_input("Số điện thoại *", value=c.get("phone", ""), max_chars=10, key=f"update_phone_{selected_id}")
            show_error_once(update_errors, validate_field("phone", phone))
        with u5:
            email = st.text_input("Email *", value=c.get("email", ""), key=f"update_email_{selected_id}")
            show_error_once(update_errors, validate_field("email", email))
        with u6:
            address = st.text_input("Địa chỉ *", value=c.get("address", ""), max_chars=250, key=f"update_address_{selected_id}")
            show_error_once(update_errors, validate_field("address", address))

        u7, u8, u9 = st.columns(3)
        with u7:
            representative = st.text_input("Người đại diện", value=c.get("representative") or "", key=f"update_rep_{selected_id}")
            msg = validate_field("representative", representative, {"customer_type": customer_type})
            if msg:
                st.warning(msg)
        with u8:
            tax_code = st.text_input("Mã số thuế", value=c.get("tax_code") or "", key=f"update_tax_{selected_id}")
            msg = validate_field("tax_code", tax_code, {"customer_type": customer_type})
            if msg and tax_code:
                show_error_once(update_errors, msg)
            elif msg:
                st.warning(msg)
        with u9:
            st.markdown("<div class='small-muted'>Mã khách hàng được khóa để bảo đảm truy vết dữ liệu.</div>", unsafe_allow_html=True)

        st.subheader("2. Thông tin dịch vụ sử dụng")
        p1, p2, p3 = st.columns(3)
        with p1:
            product_service = st.selectbox(
                "Sản phẩm cung cấp *",
                PRODUCTS,
                index=PRODUCTS.index(c.get("product_service")) if c.get("product_service") in PRODUCTS else 0,
                key=f"update_product_{selected_id}",
            )
        with p2:
            service_package = st.selectbox(
                "Gói dịch vụ *",
                PACKAGES,
                index=PACKAGES.index(c.get("service_package")) if c.get("service_package") in PACKAGES else 0,
                key=f"update_package_{selected_id}",
            )
        with p3:
            usage_duration_type = st.selectbox(
                "Thời hạn sử dụng *",
                USAGE_DURATION_TYPES,
                index=USAGE_DURATION_TYPES.index(c.get("usage_duration_type", "Có thời hạn")) if c.get("usage_duration_type") in USAGE_DURATION_TYPES else 0,
                key=f"update_usage_{selected_id}",
            )

        p4, p5, p6 = st.columns(3)
        if usage_duration_type == "Có thời hạn":
            with p4:
                start_date_value = st.date_input("Ngày bắt đầu *", value=date_default(c.get("start_date"), date.today()), key=f"update_start_{selected_id}")
            with p5:
                expiry_date_value = st.date_input("Ngày hết hạn *", value=date_default(c.get("expiry_date"), date.today() + timedelta(days=365)), key=f"update_expiry_{selected_id}")
            with p6:
                msg = validate_field(
                    "date_range",
                    None,
                    {"usage_duration_type": usage_duration_type, "start_date": start_date_value, "expiry_date": expiry_date_value},
                )
                if msg:
                    show_error_once(update_errors, msg)
                else:
                    st.success("Khoảng thời gian sử dụng hợp lệ.")
        else:
            start_date_value = None
            expiry_date_value = None
            with p4:
                st.success("Dịch vụ vĩnh viễn")
            with p5:
                st.info("Không cần nhập ngày bắt đầu/ngày hết hạn.")

        st.subheader("3. Thông tin tài chính")
        b1, b2 = st.columns([1, 2])
        with b1:
            balance = st.number_input(
                "Công nợ (VND)",
                min_value=0,
                value=int(float(c.get("balance", 0) or 0)),
                step=10000,
                format="%d",
                key=f"update_balance_{selected_id}",
            )
        with b2:
            notes = st.text_area("Ghi chú", value=c.get("notes", ""), max_chars=500, key=f"update_notes_{selected_id}")

        if st.button("Cập nhật khách hàng", type="primary"):
            updated_record = build_customer_record(
                current.get("customer_id", ""),
                customer_name,
                customer_type,
                phone,
                email,
                address,
                representative,
                tax_code,
                product_service,
                service_package,
                usage_duration_type,
                start_date_value,
                expiry_date_value,
                balance,
                notes,
                created_at=current.get("created_at"),
                is_deleted=current.get("is_deleted", False),
                deleted_at=current.get("deleted_at"),
            )
            errors = validate_customer_record(updated_record, customers, current_id=current.get("customer_id"))
            if update_errors:
                st.error("Vui lòng sửa các lỗi đang hiển thị trước khi cập nhật.")
            elif errors:
                for err in errors:
                    st.error(err)
            else:
                replace_customer_by_id(customers, selected_id, updated_record)
                save_customers(customers)
                st.session_state["flash_success"] = "Cập nhật khách hàng thành công! Dữ liệu đã được lưu vào file JSON."
                st.rerun()

elif menu == "Tìm kiếm thông tin khách hàng":
    st.markdown('<div class="section-title">Tìm kiếm thông tin khách hàng</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([3, 1, 1])
    with f1:
        keyword = st.text_input("Từ khóa", placeholder="Nhập mã, tên, SĐT hoặc email")
    with f2:
        status_filter = st.selectbox("Trạng thái", SERVICE_STATUS_ALL)
    with f3:
        include_deleted = st.checkbox("Bao gồm đã xóa")
    if st.button("Tìm kiếm", type="primary"):
        results, message = search_customers(customers, keyword, status_filter, include_deleted)
        if message and not results:
            st.warning(message) if "Tìm thấy" in message else st.info(message)
        else:
            st.markdown(f"#### Kết quả tìm kiếm: {len(results)} bản ghi")
            st.dataframe(pd.DataFrame(customers_to_rows(results)), use_container_width=True, hide_index=True)
            chosen = st.selectbox("Xem chi tiết kết quả", [f"{c['customer_id']} - {c['customer_name']}" for c in results])
            render_customer_detail(find_customer_by_id(results, chosen.split(" - ")[0]) or results[0])


elif menu == "Xóa thông tin khách hàng":
    st.markdown('<div class="section-title">Xóa thông tin khách hàng</div>', unsafe_allow_html=True)
    active_list = [enrich_customer(c) for c in active_customers(customers)]

    if not active_list:
        st.info("Không có khách hàng đang hoạt động để xóa.")
    else:
        st.markdown("### Bước 1: Nhập mã khách hàng cần xóa")
        st.caption("Nhập đúng mã khách hàng, ví dụ: KH001. Bảng bên dưới chỉ dùng để tham khảo mã khách hàng, không cần chọn từ danh sách.")

        st.dataframe(
            pd.DataFrame(customers_to_rows(active_list)),
            use_container_width=True,
            hide_index=True,
        )

        delete_id = st.text_input(
            "Nhập mã khách hàng cần xóa",
            placeholder="Ví dụ: KH001",
            key="delete_customer_id_input",
        ).strip().upper()

        if not delete_id:
            st.info("Vui lòng nhập mã khách hàng cần xóa để xem chi tiết và thực hiện thao tác xóa mềm.")
            st.stop()

        selected_customer = find_customer_by_id(active_list, delete_id)

        if not selected_customer:
            deleted_or_other = find_customer_by_id(customers, delete_id)
            if deleted_or_other and deleted_or_other.get("is_deleted"):
                st.warning("Khách hàng này đã bị xóa mềm trước đó nên không thể xóa tiếp.")
            else:
                st.error("Không tìm thấy khách hàng đang hoạt động với mã đã nhập. Vui lòng kiểm tra lại mã khách hàng.")
            st.stop()

        st.markdown("### Bước 2: Thông tin khách hàng được chọn")
        render_customer_detail(selected_customer)

        st.warning("Hệ thống sử dụng xóa mềm. Khách hàng đang Hoạt động/Sắp hết hạn hoặc còn công nợ sẽ không được xóa.")
        confirm = st.checkbox("Tôi xác nhận muốn xóa khách hàng này")

        if st.button("Xóa khách hàng", type="primary"):
            if not confirm:
                st.error("Vui lòng tick xác nhận trước khi xóa.")
            else:
                ok, msg = soft_delete_customer(customers, delete_id)
                if ok:
                    save_customers(customers)
                    st.session_state["flash_success"] = msg
                    st.rerun()
                else:
                    st.error(msg)


elif menu == "Xem danh sách thông tin khách hàng":
    st.markdown('<div class="section-title">Xem danh sách thông tin khách hàng</div>', unsafe_allow_html=True)
    active_list = [enrich_customer(c) for c in active_customers(customers)]

    if not active_list:
        st.info('Không có khách hàng nào trên hệ thống. Vui lòng sử dụng chức năng "Nhập thông tin khách hàng" để thêm dữ liệu.')
    else:
        st.markdown(f"#### Tổng số khách hàng đang hoạt động: {len(active_list)}")
        st.caption("Tick vào cột **Chọn** ở bên trái số thứ tự để xem chi tiết khách hàng. Nếu chọn nhiều dòng, hệ thống sẽ hiển thị khách hàng nằm sau cùng trong các dòng đang được chọn.")

        rows = customers_to_rows(active_list)
        table_data = [{"Chọn": False, **row} for row in rows]
        table_df = pd.DataFrame(table_data)
        disabled_columns = [col for col in table_df.columns if col != "Chọn"]

        edited_df = st.data_editor(
            table_df,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_columns,
            column_config={
                "Chọn": st.column_config.CheckboxColumn(
                    "Chọn",
                    help="Tick để xem chi tiết khách hàng",
                    default=False,
                )
            },
            key="view_customer_detail_picker_table",
        )

        selected_rows = edited_df[edited_df["Chọn"] == True]

        if selected_rows.empty:
            st.info("Vui lòng tick chọn một khách hàng trong bảng để xem thông tin chi tiết.")
        else:
            if len(selected_rows) > 1:
                st.warning("Bạn đang chọn nhiều khách hàng. Hệ thống sẽ hiển thị chi tiết khách hàng ở dòng được chọn sau cùng trong bảng.")

            selected_id = str(selected_rows.iloc[-1]["Mã KH"])
            selected_customer = find_customer_by_id(active_list, selected_id)

            st.markdown("### Thông tin chi tiết khách hàng")
            render_customer_detail(selected_customer or active_list[0])

    st.markdown('<div class="note-box">Ghi chú: Chỉ hiển thị khách hàng chưa bị xóa mềm.</div>', unsafe_allow_html=True)
