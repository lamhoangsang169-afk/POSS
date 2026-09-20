# view/nhap_san_luong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime

# ==================== NẠP MODULE ĐỘNG THEO ĐƯỜNG DẪN TUYỆT ĐỐO ====================
current_file_dir = os.path.dirname(os.path.abspath(__file__))
root_project_dir = os.path.dirname(os.path.dirname(current_file_dir))

def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

db_path = os.path.join(root_project_dir, "database.py")
utils_path = os.path.join(root_project_dir, "utils.py")

db_module = load_module_from_path("database", db_path)
utils_module = load_module_from_path("utils", utils_path)

VN_TIMEZONE = utils_module.VN_TIMEZONE
get_production_logs_db = db_module.get_production_logs_db
add_production_log_db = db_module.add_production_log_db
update_production_log_deleted_status = db_module.update_production_log_deleted_status
upload_multiple_images_to_storage = db_module.upload_multiple_images_to_storage
get_attendance_db = db_module.get_attendance_db

def render_nhap_san_luong(current_menu_name, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = str(now_vn.date())
    
    st.subheader(f"{current_menu_name} ({today_str})")

    # ==================== PHẦN 1: FORM NHẬP SẢN LƯỢNG PHÍA TRÊN ====================
    is_admin = (current_user_role == "Admin" or user_perms.get("perm_input", False))
    
    att_df_check = get_attendance_db()
    active_staff = []
    if not att_df_check.empty and "Giờ Ra Ca" in att_df_check.columns:
        active_rows = att_df_check[att_df_check["Giờ Ra Ca"].astype(str).str.lower().str.contains("chưa kết thúc|nan|none|^$", na=True)]
        if not active_rows.empty and "Nhân Sự" in active_rows.columns:
            active_staff = active_rows["Nhân Sự"].dropna().unique().tolist()

    if not is_admin:
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem**.")
    elif not active_staff:
        st.warning(f"⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)**. Vui lòng thực hiện Check-in trước khi nhập sản lượng!")
    else:
        with st.form("entry_form"):
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: st.date_input("Ngày làm việc", now_vn.date(), disabled=True)
            with f_col2:
                staff_options = ["--- Vui lòng chọn nhân sự ---"] + active_staff
                nhan_su = st.selectbox("Nhân sự thực hiện", staff_options)
            with f_col3:
                rules_df = st.session_state.get("rules_df", pd.DataFrame())
                raw_tasks = rules_df["Hạng Mục Công Việc"].tolist() if not rules_df.empty and "Hạng Mục Công Việc" in rules_df.columns else []
                danh_sach_hang_muc = [str(t).strip() for t in raw_tasks if pd.notna(t) and str(t).strip()]
                if not danh_sach_hang_muc: danh_sach_hang_muc = ["Chưa có dữ liệu định mức"]
                hang_muc = st.selectbox("Hạng mục công việc", danh_sach_hang_muc)
                
            record_images = st.file_uploader("Tải ảnh đính kèm (Tối đa 4 ảnh)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="record_img")
                    
            f_col4, f_col5 = st.columns(2)
            with f_col4: so_luong = st.number_input("Số lượng thực tế", min_value=0, value=0, step=1)
            with f_col5: ghi_chu = st.text_input("Ghi chú", "")
                
            submitted = st.form_submit_button("📊 Báo Cáo Sản Lượng", use_container_width=True)

            if submitted and nhan_su != "--- Vui lòng chọn nhân sự ---" and hang_muc != "Chưa có dữ liệu định mức":
                row_rule = rules_df[rules_df["Hạng Mục Công Việc"] == hang_muc] if not rules_df.empty else pd.DataFrame()
                he_so = float(row_rule["Hệ Số Điểm"].values) if not row_rule.empty and "Hệ Số Điểm" in row_rule.columns else 1.0
                don_vi = str(row_rule["Đơn Vị"].values) if not row_rule.empty and "Đơn Vị" in row_rule.columns else "Cái"
                tong_diem = so_luong * he_so
                
                img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                
                add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**!")
                st.cache_data.clear()
                st.rerun()

    st.markdown("---")

    # ==================== PHẦN 2: DANH SÁCH SẢN LƯỢNG & HÌNH ẢNH (CHUẨN 100% THEO HÌNH) ====================
    # Thiết kế tiêu đề và nút Làm mới nằm song song thẳng hàng ngang như ảnh
    title_col1, title_col2 = st.columns([3, 1])
    with title_col1:
        st.markdown("<h2 style='color: #1e3a8a; margin-top: 0px;'>Danh Sách Sản Lượng & Hình Ảnh</h2>", unsafe_allow_html=True)
    with title_col2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()

    raw_input_df = get_production_logs_db(is_deleted=False, limit_rows=1000)

    if not raw_input_df.empty:
        # Bộ lọc hàng ngang 5 cột đều nhau đúng theo cấu trúc ảnh của bạn
        filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1.2, 1.2, 0.8, 1.5, 1.5])
        
        with filter_col1:
            start_filter_date = st.date_input("Từ ngày", datetime.date(2026, 8, 14), key="f_start_date")
        with filter_col2:
            end_filter_date = st.date_input("Đến ngày", datetime.date(2026, 9, 20), key="f_end_date")
        with filter_col3:
            st.markdown("<br style='margin-top: 25px;'>", unsafe_allow_html=True)
            filter_by_time = st.checkbox("Lọc theo Giờ", key="f_by_time")
            
        all_staffs = ["Tất cả"] + sorted(raw_input_df["Nhân Sự"].dropna().unique().tolist())
        all_tasks = ["Tất cả"] + sorted(raw_input_df["Hạng Mục Công Việc"].dropna().unique().tolist())
        
        with filter_col4:
            selected_staff = st.selectbox("Lọc theo Nhân Sự", all_staffs, key="f_staff")
        with filter_col5:
            selected_task = st.selectbox("Lọc theo Hạng Mục", all_tasks, key="f_task")

        # Tiến hành lọc logic
        filtered_df = raw_input_df.copy()
        filtered_df["Ngày_DT"] = pd.to_datetime(filtered_df["Ngày"], errors='coerce').dt.date
        filtered_df = filtered_df[(filtered_df["Ngày_DT"] >= start_filter_date) & (filtered_df["Ngày_DT"] <= end_filter_date)]
        
        if selected_staff != "Tất cả":
            filtered_df = filtered_df[filtered_df["Nhân Sự"] == selected_staff]
        if selected_task != "Tất cả":
            filtered_df = filtered_df[filtered_df["Hạng Mục Công Việc"] == selected_task]

        total_records = len(filtered_df)
        
        # Dòng thông báo màu vàng có icon kẹp giấy đúng hệt như hình mẫu mẫu
        st.warning(f"📋 Trong khoảng ngày có: **{total_records} bản ghi**")

        if total_records > 0:
            # Thuật toán phân trang ngầm để quản lý lưới
            records_per_page = 15
            total_pages = (total_records + records_per_page - 1) // records_per_page
            page_number = st.sidebar.number_input(f"Trang dữ liệu (1/{total_pages})", min_value=1, max_value=total_pages, value=1, step=1)
            
            start_idx = (page_number - 1) * records_per_page
            end_idx = min(start_idx + records_per_page, total_records)
            page_df = filtered_df.iloc[start_idx:end_idx]

            selected_to_delete = []

            # --- KHỐI THAO TÁC XÓA HÀNG LOẠT (ĐÚNG KIỂU CHỮ & BIỂU TƯỢNG TRONG ẢNH) ---
            if current_user_role == "Admin":
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                # Nút 1: Xóa các dòng đã chọn trải dài toàn màn hình ở phía trên
                if st.button("❌ Xóa các dòng đã chọn", use_container_width=True, key="btn_del_selected"):
                    if selected_to_delete:
                        update_production_log_deleted_status(selected_to_delete, True)
                        st.success(f"✅ Đã di chuyển thành công {len(selected_to_delete)} bản ghi vào Thùng rác!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("⚠️ Vui lòng tích chọn ô xóa ở từng thẻ phía dưới trước khi bấm nút này!")

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                # Hàng phụ gồm Checkbox xác nhận và nút Xóa cả trang song song nhau
                del_c1, del_c2 = st.columns([1.5, 1.5])
                with del_c1:
                    st.markdown("<div style='margin-top: 5px;'>", unsafe_allow_html=True)
                    confirm_all = st.checkbox("Xác nhận xóa tất cả cả trang này", key="chk_confirm_all_del")
                    st.markdown("</div>", unsafe_allow_html=True)
                with del_c2:
                    if st.button("🗑️ Xóa tất cả cả trang này", use_container_width=True, key="btn_del_page_all"):
                        if not confirm_all:
                            st.error("⚠️ Bạn phải tích chọn ô 'Xác nhận xóa tất cả cả trang này' trước khi thực hiện!")
                        else:
                            all_page_ids = page_df["db_id"].tolist()
                            update_production_log_deleted_status(all_page_ids, True)
                            st.success("✅ Đã chuyển toàn bộ bản ghi trên trang này vào Thùng rác!")
                            st.cache_data.clear()
                            st.rerun()

