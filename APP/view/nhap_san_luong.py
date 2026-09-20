# view/nhap_san_luong.py
import os
import sys
import datetime
import pandas as pd
import streamlit as st

# ==================== ĐỒNG BỘ ĐƯỜNG DẪN IMPORT SYSTEM ====================
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from utils import VN_TIMEZONE
from database import (
    get_production_logs_db,
    add_production_log_db,
    update_production_log_deleted_status,
    upload_multiple_images_to_storage,
    get_attendance_db
)

def render_nhap_san_luong(current_menu_name, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = str(now_vn.date())
    
    st.subheader(f"{current_menu_name} ({today_str})")

    # --- KHỐI 1: FORM CẬP NHẬT SẢN LƯỢNG (GIỮ NGUYÊN LOGIC GỐC CỦA BẠN) ---
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
        st.warning("⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)** hoặc các ca trước chưa kết thúc. Vui lòng thực hiện Check-in trước khi nhập sản lượng!")
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
    
    # ==================== PHẦN 2: DANH SÁCH SẢN LƯỢNG & HÌNH ẢNH ====================
    col_title_1, col_title_2 = st.columns(2)
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()
    
    input_df = get_production_logs_db(is_deleted=False, limit_rows=1000)
    
    if not input_df.empty:
        # Bộ lọc hàng ngang
        filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1.2, 1.2, 0.8, 1.5, 1.5])
        
        with filter_col1: start_filter_date = st.date_input("Từ ngày", datetime.date(2026, 8, 14), key="f_start_date")
        with filter_col2: end_filter_date = st.date_input("Đến ngày", datetime.date(2026, 9, 20), key="f_end_date")
        with filter_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            filter_by_time = st.checkbox("Lọc theo Giờ", key="f_by_time")
            
        col_nhan_su = next((c for c in input_df.columns if str(c).lower().strip() in ["nhân sự", "nhan_su"]), "Nhân Sự")
        col_hang_muc = next((c for c in input_df.columns if "hạng mục" in str(c).lower() or "hang_muc" in str(c).lower()), "Hạng Mục Công Việc")
        
        all_staffs = ["Tất cả"] + sorted(input_df[col_nhan_su].dropna().unique().tolist()) if col_nhan_su in input_df.columns else ["Tất cả"]
        all_tasks = ["Tất cả"] + sorted(input_df[col_hang_muc].dropna().unique().tolist()) if col_hang_muc in input_df.columns else ["Tất cả"]
        
        with filter_col4: selected_staff = st.selectbox("Lọc theo Nhân Sự", all_staffs, key="f_staff")
        with filter_col5: selected_task = st.selectbox("Lọc theo Hạng Mục", all_tasks, key="f_task")

        filtered_df = input_df.copy()
        
        # 1. Lọc theo khoảng ngày
        col_ngay = next((c for c in filtered_df.columns if str(c).lower().strip() in ["ngày", "ngay"]), "")
        if col_ngay:
            filtered_df["Ngày_DT"] = pd.to_datetime(filtered_df[col_ngay], errors='coerce').dt.date
            filtered_df = filtered_df[(filtered_df["Ngày_DT"] >= start_filter_date) & (filtered_df["Ngày_DT"] <= end_filter_date)]
        
        # 2. Lọc theo giờ
        col_gio = next((c for c in filtered_df.columns if str(c).lower().strip() in ["thời gian", "giờ", "gio", "thoi_gian"]), "")
        if filter_by_time and col_gio:
            current_hour = now_vn.hour
            filtered_df["Hour_Int"] = pd.to_datetime(filtered_df[col_gio], errors='coerce').dt.hour
            filtered_df = filtered_df[filtered_df["Hour_Int"] == current_hour]

        if selected_staff != "Tất cả" and col_nhan_su in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[col_nhan_su] == selected_staff]
        if selected_task != "Tất cả" and col_hang_muc in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[col_hang_muc] == selected_task]

        total_records = len(filtered_df)
        st.warning(f"📋 Trong khoảng ngày có: **{total_records} bản ghi**")

        if total_records > 0:
            selected_to_delete = []

            # THANH PHÂN TRANG (PAGINATION)
            records_per_page = 10
            total_pages = (total_records + records_per_page - 1) // records_per_page
            
            page_col1, page_col2 = st.columns(2)
            with page_col2:
                page_number = st.number_input(f"Trang (1/{total_pages})", min_value=1, max_value=total_pages, value=1, step=1, key="num_page_selector")
            
            start_idx = (page_number - 1) * records_per_page
            end_idx = min(start_idx + records_per_page, total_records)
            page_df = filtered_df.iloc[start_idx:end_idx]

            if current_user_role == "Admin":
                st.markdown("<br>", unsafe_allow_html=True)
                btn_delete_selected = st.button("🗑️ Xóa Các Bản Ghi Đã Chọn", use_container_width=True, type="primary", key="btn_del_selected_new")
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                del_c1, del_c2 = st.columns(2)
                with del_c1:
                    st.markdown("<div style='margin-top: 5px;'>", unsafe_allow_html=True)
                    confirm_all = st.checkbox("Xác nhận xóa tất cả trong này", key="chk_confirm_all_del")
                    st.markdown("</div>", unsafe_allow_html=True)
                with del_c2:
                    btn_del_all = st.button("🗑️ Xóa tất cả cả trang này", use_container_width=True, key="btn_del_page_all")

            st.markdown("<br>", unsafe_allow_html=True)

            # VÒNG LẶP HIỂN THỊ CÁC THÈ BẢN GHI
            for idx, row in page_df.iterrows():
                display_stt = start_idx + page_df.index.get_loc(idx) + 1
                id_col = "db_id" if "db_id" in filtered_df.columns else ("id" if "id" in filtered_df.columns else filtered_df.columns)
                row_id = row[id_col]
                
                with st.container(border=True):
                    main_c1, main_c2 = st.columns([4, 1])
                    
                    with main_c1:
                        val_ngay = row[col_ngay] if col_ngay else today_str
                        val_gio = row.get(col_gio, "00:00:00")
                        val_user = row.get(col_nhan_su, "")
                        val_task = row.get(col_hang_muc, "")
