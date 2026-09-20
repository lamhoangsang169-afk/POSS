# view/nhap_san_luong.py
import os
import sys

# ==================== ĐIỀU HƯỚNG ĐƯỜNG DẪN ĐỘNG (SỬA LỖI WINDOWS & LINUX) ====================
current_file_dir = os.path.dirname(os.path.abspath(__file__))
root_project_dir = os.path.dirname(os.path.dirname(current_file_dir))

if root_project_dir not in sys.path:
    sys.path.insert(0, root_project_dir)

import streamlit as st
import pandas as pd
import datetime

# Thay đổi cách gọi từ thư mục gốc thông qua việc nạp module cha
try:
    from database import (
        get_production_logs_db,
        add_production_log_db,
        update_production_log_deleted_status,
        upload_multiple_images_to_storage,
        get_attendance_db
    )
    from utils import VN_TIMEZONE
except ImportError:
    # Phương án dự phòng cưỡng ép nạp trực tiếp module từ thư mục chạy hệ thống
    sys.path.append(os.getcwd())
    from database import (
        get_production_logs_db,
        add_production_log_db,
        update_production_log_deleted_status,
        upload_multiple_images_to_storage,
        get_attendance_db
    )
    from utils import VN_TIMEZONE

def render_nhap_san_luong(current_menu_name, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = str(now_vn.date())
    
    st.subheader(f"{current_menu_name} ({today_str})")

    if current_user_role != "Admin" and not user_perms.get("perm_input", False):
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem**. Bạn có thể theo dõi bảng danh sách bên dưới nhưng không được phép thêm hoặc chỉnh sửa dữ liệu.")
    else:
        att_df_check = get_attendance_db()
        checked_in_set = set()
        if not att_df_check.empty:
            checked_in_set = set(att_df_check[att_df_check["Giờ Ra Ca"] == "Chưa kết thúc"]["Nhân Sự"].tolist())

        active_staff = [s for s in st.session_state.get("staff_list", []) if s in checked_in_set]

        if not active_staff:
            st.warning(f"⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)** hoặc các ca trước chưa kết thúc. Vui lòng thực hiện Check-in trước khi nhập sản lượng!")
        else:
            req_img = st.session_state.get("require_image", True)
            req_qty = st.session_state.get("require_quantity", True)
            
            with st.form("entry_form"):
                f_col1, f_col2, f_col3 = st.columns(3)
                with f_col1: ngay = st.date_input("Ngày làm việc", now_vn.date(), disabled=True)
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
                with f_col4: so_luong = st.number_input("Số lượng thực tế", min_value=0, value=0, step=1)
                with f_col5: ghi_chu = st.text_input("Ghi chú", "")
                    
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
                        he_so = float(row_rule["Hệ Số Điểm"].values[0]) if not row_rule.empty else 1.0
                        don_vi = row_rule["Đơn Vị"].values[0] if not row_rule.empty else "Cái"
                        tong_diem = so_luong * he_so
                        
                        img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                        current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                        
                        add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                        st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**! Tổng điểm: **{tong_diem} điểm**")
                        st.rerun()

    st.markdown("---")
    
    col_title_1, col_title_2 = st.columns([3, 1])
    with col_title_1:
        st.subheader("Danh Sách Sản Lượng & Hình Ảnh")
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()
    
    input_df = get_production_logs_db(is_deleted=False, limit_rows=150)
    if not input_df.empty:
        st.dataframe(input_df, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu sản lượng.")
