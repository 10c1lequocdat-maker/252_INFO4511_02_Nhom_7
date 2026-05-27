# 🧾 Hệ thống Quản lý Khách hàng Công ty Cổ phần MISA

> Đề tài bài tập lớn học phần Lập trình Python  
> 🚀 Giao diện web: **Streamlit**  
> 💻 Giao diện dòng lệnh: **Python thuần**  
> 📁 Lưu trữ dữ liệu: **File JSON**  
> 🧩 Tổ chức chương trình: Theo **hàm và module**

---

## 📌 Mục tiêu đề tài

Xây dựng chương trình quản lý khách hàng của Công ty Cổ phần MISA nhằm hỗ trợ nhập mới, cập nhật, tìm kiếm, xóa mềm và xem danh sách khách hàng.

---

## 🧱 Cấu trúc thư mục

```text
252_INFO4511_02_Nhom_7
├── app.py                      # Giao diện web chính bằng Streamlit
├── codethuan.py                # Giao diện dòng lệnh Python thuần
├── config.toml                 # File cấu hình giao diện Streamlit
├── requirements.txt            # Danh sách thư viện cần cài đặt
├── README.md                   # Tài liệu mô tả và hướng dẫn sử dụng
│
├── data/
│   └── customers.json          # File lưu trữ dữ liệu khách hàng
│
└── modules/
    ├── customer_service.py     # Toàn bộ hàm nghiệp vụ và ràng buộc
    └── storage.py              # Hàm đọc / ghi dữ liệu JSON
```

---

## 🚀 Cách chạy web app

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

---

## 💻 Cách chạy bản Python thuần

```bash
python codethuan.py
```

---

## 🧩 Nguyên tắc tổ chức code

- `modules/customer_service.py`: chứa toàn bộ logic nghiệp vụ, ràng buộc, kiểm tra dữ liệu, tạo bản ghi, tìm kiếm, xóa mềm.
- `modules/storage.py`: chỉ đọc/ghi dữ liệu trong `data/customers.json`.
- `app.py`: chỉ hiển thị giao diện Streamlit và gọi hàm trong module.
- `codethuan.py`: chỉ hiển thị menu dòng lệnh, nhập/xuất dữ liệu và gọi hàm trong module.

---

## ✅ Quy tắc nghiệp vụ

- Tự động sinh mã khách hàng dạng `KH001`, `KH002`, ...
- Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng 0.
- Email nếu nhập phải đúng định dạng cơ bản.
- Mã số thuế nếu nhập phải gồm 10, 12 hoặc 13 chữ số.
- Khách hàng doanh nghiệp bắt buộc có người đại diện và mã số thuế.
- Ngày hết hạn phải lớn hơn ngày bắt đầu.
- Công nợ không được nhỏ hơn 0.
- Khi xóa, hệ thống xóa mềm bằng `is_deleted = True`.
- Không cho xóa khách hàng đang hoạt động/sắp hết hạn hoặc còn công nợ.

---

## 📎 Ghi chú

Đây là sản phẩm phục vụ mục đích học tập và nghiên cứu, không phải phần mềm chính thức của Công ty Cổ phần MISA.
