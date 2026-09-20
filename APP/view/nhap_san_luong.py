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

def find_column_case_insensitive(df, target_names):
    """Tìm tên cột thực tế trong DataFrame không phân biệt hoa thường hoặc dấu gạch dưới"""
    if df.empty:
        return ""
    cols = [str(c).strip().lower() for c in df.columns]
    for target in target_names:
        target_clean = target.strip().lower()
        if target_clean in cols:
            idx = cols.index(target_clean)
            return df.columns[idx]
        target_no_space = target_clean.replace(" ", "").replace("_", "")
        for i, c in enumerate(cols):
            c_clean = c.replace(" ", "").replace("_", "")
            if target_no_space == c_clean:
                return df.columns[i]
    return df.columns[0] if len(df.columns) > 0 else ""

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
            st.warning("⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)** hoặc các ca trước chưa kết thúc. Vui lòng thực hiện Check-in trước khi nhập sản lượng!")
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
                        he_so = float(row_rule["Hệ Số Điểm"].values) if not row_rule.empty else 1.0
                        don_vi = row_rule["Đơn Vị"].values if not row_rule.empty else "Cái"
                        tong_diem = so_luong * he_so
                        
                        img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                        current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                        
                        add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                        st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**! Tổng điểm: **{tong_diem} điểm**")
                        st.rerun()

    st.markdown("---")
    
    # ==================== PHẦN 2: DANH SÁCH BẢN GHI THEO THIẾT KẾ UX HÌNH MẪU ====================
    col_title_1, col_title_2 = st.columns(2)
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a; margin: 0;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()
    
    # Gọi chính xác hàm đọc cơ sở dữ liệu theo cấu trúc phân tham số ổn định nhất của bạn
    input_df = get_production_logs_db(is_deleted=False, limit_rows=150)
    if input_df is None or input_df.empty:
        try:
            input_df = get_production_logs_db()
        except:
            input_df = pd.DataFrame()

    # Khởi tạo bộ ánh xạ cột động chống lệch dữ liệu từ Google Sheets
    col_ngay = find_column_case_insensitive(input_df, ["Ngày", "ngay", "ngày làm việc", "Ngày làm việc"])
    col_gio = find_column_case_insensitive(input_df, ["Thời Gian", "thoi_gian", "giờ", "gio", "Thời gian"])
    col_nhan_su = find_column_case_insensitive(input_df, ["Nhân Sự", "nhan_su", "nhân sự thực hiện", "Nhân sự"])
    col_hang_muc = find_column_case_insensitive(input_df, ["Hạng Mục Công Việc", "hang_muc_cong_viec", "hạng mục", "hang_muc", "Hạng mục"])
    col_so_luong = find_column_case_insensitive(input_df, ["Số Lượng Thực Tế", "Số Lượng", "so_luong", "qty", "Số lượng"])
    col_don_vi = find_column_case_insensitive(input_df, ["Đơn Vị", "don_vi", "unit", "Đơn vị"])
    col_tong_diem = find_column_case_insensitive(input_df, ["Tổng Điểm", "tong_diem", "điểm", "diem", "Tổng điểm"])
    col_ghi_chu = find_column_case_insensitive(input_df, ["Ghi Chú", "ghi_chu", "note", "Ghi chú"])
    col_hinh_anh = find_column_case_insensitive(input_df, ["Hình Ảnh", "hinh_anh", "img_urls", "Hình ảnh"])

    # Vẽ giao diện bộ lọc thanh ngang chuẩn tỉ lệ UX hình mẫu của bạn
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5, filter_col6 = st.columns([1.2, 1.2, 0.8, 1.5, 1.5, 1.5])
    
    with filter_col1:
        start_filter_date = st.date_input("Từ ngày", now_vn.date() - datetime.timedelta(days=30), key="f_start_date")
    with filter_col2:
        end_filter_date = st.date_input("Đến ngày", now_vn.date(), key="f_end_date")
    with filter_col3:
        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
        filter_by_time = st.checkbox("Lọc theo Giờ", key="f_by_time")
        
    all_staffs = ["Tất cả"] + sorted(input_df[col_nhan_su].dropna().unique().tolist()) if (not input_df.empty and col_nhan_su and col_nhan_su in input_df.columns) else ["Tất cả"]
    all_tasks = ["Tất cả"] + sorted(input_df[col_hang_muc].dropna().unique().tolist()) if (not input_df.empty and col_hang_muc and col_hang_muc in input_df.columns) else ["Tất cả"]
    
    with filter_col4:
        selected_staff = st.selectbox("Lọc theo Nhân Sự", all_staffs, key="f_staff")
    with filter_col5:
        selected_task = st.selectbox("Lọc theo Hạng Mục", all_tasks, key="f_task")

    filtered_df = input_df.copy()
    
    # === SỬA ĐỔI QUAN TRỌNG: Khối lọc chuỗi vector hóa bảo toàn dữ liệu 100%, không lo rớt bản ghi ===
    if not filtered_df.empty:
        if col_ngay and col_ngay in filtered_df.columns:
            try:
                date_series = filtered_df[col_ngay].astype(str).str.strip()
                # Thử tạo các định dạng chuỗi văn bản phổ biến để khớp mẫu bộ lọc ngày
                s_str1, e_str1 = start_filter_date.strftime('%Y-%m-%d'), end_filter_date.strftime('%Y-%m-%d')
                s_str2, e_str2 = start_filter_date.strftime('%d/%m/%Y'), end_filter_date.strftime('%d/%m/%Y')
                
                # Quét và giữ lại toàn bộ dòng thỏa mãn một trong các cấu trúc ngày văn bản
                cond = (date_series >= s_str1) & (date_series <= e_str1) | (date_series >= s_str2) & (date_series <= e_str2)
                temp_df = filtered_df[cond]
                if not temp_df.empty:
                    filtered_df = temp_df
            except:
                pass
        
