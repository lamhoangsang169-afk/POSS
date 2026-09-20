# view/nhap_san_luong.py
import streamlit as st
import pandas as pd
import datetime
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

    # ==================== PHẦN 1: FORM NHẬP SẢN LƯỢNG (GIỮ NGUYÊN GỐC BAN ĐẦU) ====================
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
    
    # ==================== PHẦN 2: DANH SÁCH BẢN GHI THEO THIẾT KẾ UX HÌNH MẪU ====================
    col_title_1, col_title_2 = st.columns([3, 1])
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a; margin: 0;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()
    
    # Tải lượng dữ liệu lớn an toàn để hỗ trợ phân trang cho 476 bản ghi
    input_df = get_production_logs_db(is_deleted=False, limit_rows=1000)
    
    if not input_df.empty:
        # Bộ lọc ngang tích hợp phân trang góc phải chuẩn tỉ lệ UX hình mẫu
        filter_col1, filter_col2, filter_col3, filter_col4, filter_col5, filter_col6 = st.columns([1.2, 1.2, 0.8, 1.5, 1.5, 1.5])
        
        with filter_col1:
            start_filter_date = st.date_input("Từ ngày", now_vn.date() - datetime.timedelta(days=30), key="f_start_date")
        with filter_col2:
            end_filter_date = st.date_input("Đến ngày", now_vn.date(), key="f_end_date")
        with filter_col3:
            st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
            filter_by_time = st.checkbox("Lọc theo Giờ", key="f_by_time")
            
        all_staffs = ["Tất cả"] + sorted(input_df["Nhân Sự"].dropna().unique().tolist()) if "Nhân Sự" in input_df.columns else ["Tất cả"]
        all_tasks = ["Tất cả"] + sorted(input_df["Hạng Mục Công Việc"].dropna().unique().tolist()) if "Hạng Mục Công Việc" in input_df.columns else ["Tất cả"]
        
        with filter_col4:
            selected_staff = st.selectbox("Lọc theo Nhân Sự", all_staffs, key="f_staff")
        with filter_col5:
            selected_task = st.selectbox("Lọc theo Hạng Mục", all_tasks, key="f_task")

        # Tiến hành lọc dữ liệu an toàn dựa trên chuỗi chữ của Google Sheets
        filtered_df = input_df.copy()
        
        if "Ngày" in filtered_df.columns:
            try:
                # Ép ngày an toàn, nếu lỗi chuỗi thì bỏ qua bộ lọc ngày để giữ dữ liệu gốc hiển thị
                parsed_dates = pd.to_datetime(filtered_df["Ngày"], errors='coerce').dt.date
                nas = parsed_dates.isna()
                if nas.any():
                    parsed_dates[nas] = pd.to_datetime(filtered_df.loc[nas, "Ngày"], format='%d/%m/%Y', errors='coerce').dt.date
                
                temp_df = filtered_df[(parsed_dates >= start_filter_date) & (parsed_dates <= end_filter_date)]
                if not temp_df.empty:
                    filtered_df = temp_df
            except:
                pass
        
        if filter_by_time and "Thời Gian" in filtered_df.columns:
            try:
                current_hour_str = f"{now_vn.hour:02d}:"
                filtered_df = filtered_df[filtered_df["Thời Gian"].astype(str).str.contains(current_hour_str, na=False)]
            except:
                pass

        if selected_staff != "Tất cả" and "Nhân Sự" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Nhân Sự"] == selected_staff]
        if selected_task != "Tất cả" and "Hạng Mục Công Việc" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Hạng Mục Công Việc"] == selected_task]

        total_records = len(filtered_df)
        st.warning(f"📋 Trong khoảng ngày có: **{total_records} bản ghi**")

        if total_records > 0:
            # QUẢN LÝ PHÂN TRANG (PAGINATION)
            records_per_page = 10
            total_pages = (total_records + records_per_page - 1) // records_per_page
            
            with filter_col6:
                page_number = st.number_input(f"Trang hiển thị (1/{total_pages})", min_value=1, max_value=total_pages, value=1, step=1, key="num_page_selector")
            
            start_idx = (page_number - 1) * records_per_page
            end_idx = min(start_idx + records_per_page, total_records)
            page_df = filtered_df.iloc[start_idx:end_idx]

            selected_to_delete = []

            # Khối nút bấm thao tác xóa dành cho Quản trị viên (Admin)
            if current_user_role == "Admin":
                st.markdown("<br>", unsafe_allow_html=True)
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    btn_delete_selected = st.button("🗑️ Xóa các dòng đã chọn", use_container_width=True, type="primary", key="btn_del_selected_final")
                with btn_c2:
                    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
                    confirm_all = st.checkbox("Xác nhận xóa tất cả các trang này", key="chk_confirm_all_del")
                
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
