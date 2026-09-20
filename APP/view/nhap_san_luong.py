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
    if current_user_role != "Admin" and not user_perms.get("perm_input", False):
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem**. Bạn có thể theo dõi bảng danh sách bên dưới nhưng không được phép thêm hoặc chỉnh sửa dữ liệu.")
    else:
        att_df_check = get_attendance_db()
        checked_in_set = set()
        if not att_df_check.empty:
            checked_in_set = set(att_df_check[att_df_check["Giờ Ra Ca"] == "Chưa kết thúc"]["Nhân Sự"].tolist())

        active_staff = [s for s in st.session_state.get("staff_list", []) if s in checked_in_set]

        if not active_staff:
            st.warning("⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)** hoặc các ca trước chưa kết thúc. Vui lòng thực hiện Check-in trước khi nhập sản lượng!")
        else:
            req_img = st.session_state.get("require_image", True)
            req_qty = st.session_state.get("require_quantity", True)
            
            with st.form("entry_form"):
                f_col1, f_col2, f_col3 = st.columns(3)
                with f_col1: 
                    st.date_input("Ngày làm việc", now_vn.date(), disabled=True)
                with f_col2:
                    staff_options = ["--- Vui lòng chọn nhân sự ---"] + active_staff
                    nhan_su = st.selectbox("Nhân sự thực hiện", staff_options)
                with f_col3:
                    rules_df = st.session_state.get("rules_df", pd.DataFrame())
                    raw_tasks = rules_df["Hạng Mục Công Việc"].tolist() if not rules_df.empty else []
                    danh_sach_hang_muc = [str(t).strip() for t in raw_tasks if pd.notna(t) and str(t).strip() and str(t).strip().lower() not in ["nan", "none"]]
                    hang_muc = st.selectbox("Hạng mục công việc", danh_sach_hang_muc)
                    
                record_images = st.file_uploader("Tải ảnh đính kèm (Tối đa 4 ảnh)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="record_img")
                        
                f_col4, f_col5 = st.columns(2)
                with f_col4: 
                    so_luong = st.number_input("Số lượng thực tế", min_value=0, value=0, step=1)
                with f_col5: 
                    ghi_chu = st.text_input("Ghi chú", "")
                    
                submitted = st.form_submit_button("📊 Báo Cáo Sản Lượng", use_container_width=True)

                if submitted:
                    is_valid = True
                    cleaned_hang_muc = str(hang_muc).strip()
                    cleaned_ghi_chu = str(ghi_chu).strip()

                    if nhan_su == "--- Vui lòng chọn nhân sự ---":
                        is_valid = False
                        st.error("⚠️ Vui lòng chọn đúng tên nhân sự thực hiện!")
                    elif req_img and not record_images: 
                        is_valid = False
                        st.error("⚠️ Vui lòng tải lên ảnh đính kèm!")
                    elif req_qty and so_luong <= 0: 
                        is_valid = False
                        st.error("⚠️ Số lượng thực tế phải lớn hơn 0!")
                    elif record_images and len(record_images) > 4:
                        is_valid = False
                        st.error("⚠️ Bạn chỉ được phép đính kèm tối đa 4 ảnh!")
                    elif "công việc phát sinh" in cleaned_hang_muc.lower() and not cleaned_ghi_chu:
                        is_valid = False
                        st.error("⚠️ Bắt buộc phải nhập nội dung vào phần Ghi chú khi chọn 'Công việc phát sinh'!")

                    if is_valid:
                        row_rule = rules_df[rules_df["Hạng Mục Công Việc"] == hang_muc] if not rules_df.empty else pd.DataFrame()
                        he_so = float(row_rule["Hệ Số Điểm"].values) if not row_rule.empty else 1.0
                        don_vi = row_rule["Đơn Vị"].values if not row_rule.empty else "Cái"
                        tong_diem = so_luong * he_so
                        
                        img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                        current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                        
                        add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                        st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**! Tổng điểm: **{tong_diem} điểm**")
                        st.rerun()

    st.markdown("---")
    
    # --- KHỐI 2: LƯỚI THÈ SẢN LƯỢNG VÀ BỘ LỌC NGANG CHUẨN UX GIAO DIỆN ---
    col_title_1, col_title_2 = st.columns(2)
    with col_title_1:
        st.markdown("<h2 style='color: #1e3a8a; margin-top: 0px; font-size: 1.5rem;'>Danh Sách Sản Lượng & Hình Ảnh</h2>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()
    
    input_df = get_production_logs_db(is_deleted=False, limit_rows=150)
    
    if not input_df.empty:
        filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1.2, 1.2, 0.8, 1.5, 1.5])
        
        with filter_col1:
            start_filter_date = st.date_input("Từ ngày", datetime.date(2026, 8, 14), key="f_start_date")
        with filter_col2:
            end_filter_date = st.date_input("Đến ngày", datetime.date(2026, 9, 20), key="f_end_date")
        with filter_col3:
            st.markdown("<br style='margin-top: 25px;'>", unsafe_allow_html=True)
            filter_by_time = st.checkbox("Lọc theo Giờ", key="f_by_time")
            
        col_nhan_su = "Nhân Sự" if "Nhân Sự" in input_df.columns else ("nhan_su" if "nhan_su" in input_df.columns else "")
        col_hang_muc = "Hạng Mục Công Việc" if "Hạng Mục Công Việc" in input_df.columns else ("hang_muc" if "hang_muc" in input_df.columns else "")
        
        all_staffs = ["Tất cả"] + sorted(input_df[col_nhan_su].dropna().unique().tolist()) if col_nhan_su else ["Tất cả"]
        all_tasks = ["Tất cả"] + sorted(input_df[col_hang_muc].dropna().unique().tolist()) if col_hang_muc else ["Tất cả"]
        
        with filter_col4:
            selected_staff = st.selectbox("Lọc theo Nhân Sự", all_staffs, key="f_staff")
        with filter_col5:
            selected_task = st.selectbox("Lọc theo Hạng Mục", all_tasks, key="f_task")

        filtered_df = input_df.copy()
        
        col_ngay = "Ngày" if "Ngày" in filtered_df.columns else ("ngay" if "ngay" in filtered_df.columns else "")
        if col_ngay:
            filtered_df["Ngày_DT"] = pd.to_datetime(filtered_df[col_ngay], errors='coerce').dt.date
            filtered_df = filtered_df[(filtered_df["Ngày_DT"] >= start_filter_date) & (filtered_df["Ngày_DT"] <= end_filter_date)]
        
        if selected_staff != "Tất cả" and col_nhan_su:
            filtered_df = filtered_df[filtered_df[col_nhan_su] == selected_staff]
        if selected_task != "Tất cả" and col_hang_muc:
            filtered_df = filtered_df[filtered_df[col_hang_muc] == selected_task]

        total_records = len(filtered_df)
        st.warning(f"📋 Trong khoảng ngày có: **{total_records} bản ghi**")

        if total_records > 0:
            selected_to_delete = []

            if current_user_role == "Admin":
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                if st.button("❌ Xóa các dòng đã chọn", use_container_width=True, key="btn_del_selected"):
                    if selected_to_delete:
                        update_production_log_deleted_status(selected_to_delete, True)
                        st.success(f"✅ Đã di chuyển thành công {len(selected_to_delete)} bản ghi vào Thùng rác!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("⚠️ Vui lòng tích chọn ô xóa ở từng thẻ phía dưới trước khi bấm nút này!")

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
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
                            id_col = "id" if "id" in filtered_df.columns else ("db_id" if "db_id" in filtered_df.columns else filtered_df.columns)
                            all_page_ids = filtered_df[id_col].tolist()
                            update_production_log_deleted_status(all_page_ids, True)
