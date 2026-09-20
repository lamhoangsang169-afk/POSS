# view/nhap_san_luong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime

# ==================== NẠP MODULE ĐỘNG THEO ĐƯỜNG DẪN TUYỆT ĐỐI ====================
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

    if current_user_role != "Admin" and not user_perms.get("perm_input", False):
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem**. Bạn có thể theo dõi bảng danh sách bên dưới nhưng không được phép thêm hoặc chỉnh sửa dữ liệu.")
    else:
        # Lấy lịch sử chấm công từ database
        att_df_check = get_attendance_db()
        active_staff = []
        
        if not att_df_check.empty and "Giờ Ra Ca" in att_df_check.columns:
            active_rows = att_df_check[att_df_check["Giờ Ra Ca"].astype(str).str.lower().str.contains("chưa kết thúc|nan|none|^$", na=True)]
            if not active_rows.empty and "Nhân Sự" in active_rows.columns:
                active_staff = active_rows["Nhân Sự"].dropna().unique().tolist()

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
                    # === ĐÃ SỬA LỖI KEYERROR Ở ĐÂY: Bảo vệ code an toàn nếu thiếu tên cột ===
                    rules_df = st.session_state.get("rules_df", pd.DataFrame())
                    danh_sach_hang_muc = []
                    
                    if not rules_df.empty:
                        # Thử lấy cột chuẩn, nếu lỗi sẽ tự động tìm kiếm cột chứa chữ "hạng mục" hoặc lấy cột đầu tiên
                        target_col = None
                        for col in rules_df.columns:
                            if str(col).lower() in ["hạng mục công việc", "hang_muc_cong_viec", "hang_muc"]:
                                target_col = col
                                break
                        if not target_col:
                            target_col = rules_df.columns[0] # Lấy đại cột đầu tiên nếu không thấy
                        
                        raw_tasks = rules_df[target_col].tolist()
                        danh_sach_hang_muc = [str(t).strip() for t in raw_tasks if pd.notna(t) and str(t).strip() and str(t).strip().lower() not in ["nan", "none"]]
                    
                    if not danh_sach_hang_muc:
                        danh_sach_hang_muc = ["Chưa có dữ liệu định mức công việc"]
                        
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
                    elif hang_muc == "Chưa có dữ liệu định mức công việc":
                        is_valid = False
                        st.error("⚠️ Không thể báo cáo sản lượng do hệ thống trống danh mục định mức!")
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
                        # Tìm hệ số điểm an toàn
                        he_so = 1.0
                        don_vi = "Cái"
                        if not rules_df.empty and target_col in rules_df.columns:
                            row_rule = rules_df[rules_df[target_col] == hang_muc]
                            if not row_rule.empty:
                                # Thử tìm cột hệ số điểm động
                                for col in row_rule.columns:
                                    if "hệ số" in str(col).lower() or "he_so" in str(col).lower():
                                        he_so = float(row_rule[col].values[0]) if pd.notna(row_rule[col].values[0]) else 1.0
                                    if "đơn vị" in str(col).lower() or "don_vi" in str(col).lower():
                                        don_vi = str(row_rule[col].values[0]) if pd.notna(row_rule[col].values[0]) else "Cái"
                        
                        tong_diem = so_luong * he_so
                        img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                        current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                        
                        add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                        st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**! Tổng điểm: **{tong_diem} điểm**")
                        st.rerun()

    st.markdown("---")
    
    col_title_1, col_title_2 = st.columns(2)
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
