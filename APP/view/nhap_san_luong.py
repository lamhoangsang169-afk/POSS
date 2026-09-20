# view/nhap_san_luong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime

# ==================== NẠP MODULE ĐỘNG THEO ĐƯỜNG DẪN TUYỆT ĐỐI (GIỮ NGUYÊN GỐC 100%) ====================
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

# ==================== HỘP THOẠI POPUP PHÓNG TO ẢNH NÂNG CAO ====================
@st.dialog("🔍 Xem Ảnh Bản Ghi Chi Tiết", width="large")
def show_zoomed_images_dialog(staff_name, task_name, img_url_string):
    st.markdown(f"👤 Nhân sự: **{staff_name}**")
    st.markdown(f"🏗️ Hạng mục: *{task_name}*")
    st.markdown("---")
    if img_url_string and str(img_url_string).strip().lower() != "nan":
        urls = [u.strip() for u in str(img_url_string).split(",") if u.strip()]
        if urls:
            for i, url in enumerate(urls):
                st.image(url, caption=f"Ảnh đính kèm {i+1} (Ảnh gốc chất lượng cao)", use_container_width=True)
        else:
            st.info("Bản ghi này không có tệp ảnh hợp lệ.")
    else:
        st.info("Không tìm thấy hình ảnh đi kèm bản ghi này.")

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
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem**. Bạn có thể theo dõi bảng danh sách bên dưới nhưng không được phép thêm hoặc chỉnh sửa dữ liệu.")
    elif not active_staff:
        st.warning(f"⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)**. Vui lòng thực hiện Check-in trước khi nhập sản lượng!")
    else:
        req_img = st.session_state.get("require_image", True)
        req_qty = st.session_state.get("require_quantity", True)
        
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
                he_so = float(row_rule["Hệ Số Điểm"].values[0]) if not row_rule.empty and "Hệ Số Điểm" in row_rule.columns else 1.0
                don_vi = str(row_rule["Đơn Vị"].values[0]) if not row_rule.empty and "Đơn Vị" in row_rule.columns else "Cái"
                tong_diem = so_luong * he_so
                
                img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                
                add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**!")
                st.cache_data.clear()
                st.rerun()

    st.markdown("---")

    # ==================== PHẦN 2: DANH SÁCH SẢN LƯỢNG & HÌNH ẢNH ====================
    col_title_1, col_title_2 = st.columns([2, 1])
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a; margin:0;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()

    # Nạp dữ liệu gốc từ Google Sheets không ép tham số lỗi
    try:
        raw_input_df = get_production_logs_db(is_deleted=False, limit_rows=1000)
    except:
        try:
            raw_input_df = get_production_logs_db()
        except:
            raw_input_df = pd.DataFrame()

    # Đưa bộ khung giao diện ra ngoài để luôn render mượt mà
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5, filter_col6 = st.columns([1.2, 1.2, 0.8, 1.5, 1.5, 1.5])
    
    with filter_col1:
        start_filter_date = st.date_input("Từ ngày", now_vn.date() - datetime.timedelta(days=30), key="f_start_date")
    with filter_col2:
        end_filter_date = st.date_input("Đến ngày", now_vn.date(), key="f_end_date")
    with filter_col3:
        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
        filter_by_time = st.checkbox("Lọc theo Giờ", key="f_by_time")
        
    all_staffs = ["Tất cả"] + sorted(raw_input_df["Nhân Sự"].dropna().unique().tolist()) if (not raw_input_df.empty and "Nhân Sự" in raw_input_df.columns) else ["Tất cả"]
    all_tasks = ["Tất cả"] + sorted(raw_input_df["Hạng Mục Công Việc"].dropna().unique().tolist()) if (not raw_input_df.empty and "Hạng Mục Công Việc" in raw_input_df.columns) else ["Tất cả"]
    
    with filter_col4:
        selected_staff = st.selectbox("Lọc theo Nhân Sự", all_staffs, key="f_staff")
    with filter_col5:
        selected_task = st.selectbox("Lọc theo Hạng Mục", all_tasks, key="f_task")

    filtered_df = raw_input_df.copy()

    # Tiến hành xử lý bộ lọc ngày an toàn chuỗi vector hóa
    if not filtered_df.empty and "Ngày" in filtered_df.columns:
        try:
            date_series = filtered_df["Ngày"].astype(str).str.strip()
            s_str1, e_str1 = start_filter_date.strftime('%Y-%m-%d'), end_filter_date.strftime('%Y-%m-%d')
            s_str2, e_str2 = start_filter_date.strftime('%d/%m/%Y'), end_filter_date.strftime('%d/%m/%Y')
            cond = (date_series >= s_str1) & (date_series <= e_str1) | (date_series >= s_str2) & (date_series <= e_str2)
            temp_df = filtered_df[cond]
            if not temp_df.empty:
                filtered_df = temp_df
        except:
            pass

    if not filtered_df.empty and filter_by_time and "Thời Gian" in filtered_df.columns:
        try:
            current_hour_str = f"{now_vn.hour:02d}:"
            filtered_df = filtered_df[filtered_df["Thời Gian"].astype(str).str.contains(current_hour_str, na=False)]
        except:
            pass

    if not filtered_df.empty and selected_staff != "Tất cả" and "Nhân Sự" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Nhân Sự"] == selected_staff]
    if not filtered_df.empty and selected_task != "Tất cả" and "Hạng Mục Công Việc" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Hạng Mục Công Việc"] == selected_task]

    total_records = len(filtered_df)
    st.warning(f"📋 Trong khoảng ngày tìm thấy: **{total_records} bản ghi**")

    # Tính toán trang phân trang lồng đồng bộ ngang hàng vào filter_col6 góc phải cực gọn
    records_per_page = 10
    total_pages = max((total_records + records_per_page - 1) // records_per_page, 1)
    with filter_col6:
        page_number = st.number_input(f"Trang hiển thị (1/{total_pages})", min_value=1, max_value=total_pages, value=1, step=1, key="num_page_selector")

    if total_records > 0 and not filtered_df.empty:
        start_idx = (page_number - 1) * records_per_page
        end_idx = min(start_idx + records_per_page, total_records)
        page_df = filtered_df.iloc[start_idx:end_idx]

        selected_to_delete = []

        # --- KHỐI THAO TÁC XÓA HÀNG LOẠT DÀNH CHO ADMIN ---
