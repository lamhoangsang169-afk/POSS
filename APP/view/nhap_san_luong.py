# view/nhap_san_luong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime
import requests

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
get_rules_db = db_module.get_rules_db
update_production_log_record_db = db_module.update_production_log_record_db


# ==================== HÀM PHỤ TRỢ: LẤY DUNG LƯỢNG ẢNH AN TOÀN ====================
@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_image_size(u):
    try:
        if u.startswith("http://") or u.startswith("https://"):
            res = requests.head(u, timeout=0.8)
            length = int(res.headers.get('Content-Length', 0))
            if length > 0:
                if length >= 1024 * 1024:
                    return f"~{length / (1024 * 1024):.1f} MB"
                return f"~{max(1, int(length / 1024))} KB"
        elif os.path.exists(u):
            length = os.path.getsize(u)
            if length >= 1024 * 1024:
                return f"~{length / (1024 * 1024):.1f} MB"
            return f"~{max(1, int(length / 1024))} KB"
    except Exception:
        pass
    return "~150 KB"


# ==================== HỘP THOẠI CHỈNH SỬA BẢN GHI SẢN LƯỢNG ====================
@st.dialog("✏️ Chỉnh Sửa Bản Ghi Sản Lượng")
def show_edit_dialog(row_data, danh_sach_hang_muc):
    st.markdown(f"**Đang sửa bản ghi STT: {row_data.get('STT')} - Nhân sự: {row_data.get('Nhân Sự')}**")
    
    current_task = row_data.get('Hạng Mục Công Việc', danh_sach_hang_muc[0])
    try:
        task_idx = danh_sach_hang_muc.index(current_task)
    except ValueError:
        task_idx = 0
        
    new_hang_muc = st.selectbox("Hạng mục công việc mới", danh_sach_hang_muc, index=task_idx, key=f"edit_task_{row_data['db_id']}")
    new_so_luong = st.number_input("Số lượng thực tế mới", min_value=0, value=int(row_data.get('Số Lượng', 0)), step=1, key=f"edit_qty_{row_data['db_id']}")
    new_ghi_chu = st.text_input("Ghi chú mới", value=str(row_data.get('Ghi Chú', '') if pd.notna(row_data.get('Ghi Chú')) else ''), key=f"edit_note_{row_data['db_id']}")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if st.button("💾 Lưu Thay Đổi", use_container_width=True, type="primary"):
            update_production_log_record_db(
                db_id=row_data['db_id'],
                hang_muc=new_hang_muc,
                so_luong=new_so_luong,
                ghi_chu=new_ghi_chu
            )
            st.cache_data.clear()
            st.success("✅ Cập nhật bản ghi thành công!")
            st.rerun()
    with col_e2:
        if st.button("❌ Hủy", use_container_width=True):
            st.rerun()


# ==================== FRAGMENT LỌC TỨC THÌ & TỐI ƯU GIAO DIỆN GIỜ ====================
@st.fragment
def render_production_table_fragment(raw_input_df, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    
    col_title_1, col_title_2 = st.columns([3, 1])
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input_frag"):
            st.cache_data.clear()
            st.rerun()

    if raw_input_df.empty:
        st.info("Chưa có dữ liệu sản lượng.")
        return

    # SẮP XẾP 6 CỘT BỐ CỤC BỘ LỌC
    f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.1, 1.1, 1.4, 1.3, 1.3, 1.2])
    
    with f_col1:
        start_filter_date = st.date_input("Từ ngày", value=now_vn.date(), key="f_start_live")
    with f_col2:
        end_filter_date = st.date_input("Đến ngày", value=now_vn.date(), key="f_end_live")
    with f_col3:
        enable_hour_filter = st.checkbox("Lọc theo Giờ", value=False, key="f_hour_live")
        if enable_hour_filter:
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                start_t = st.time_input("Từ", value=datetime.time(7, 30), label_visibility="collapsed", key="f_start_t_live")
            with t_col2:
                end_t = st.time_input("Đến", value=datetime.time(17, 0), label_visibility="collapsed", key="f_end_t_live")
        else:
            start_t, end_t = None, None
            
    with f_col4:
        all_staff_opts = ["Tất cả"] + sorted(raw_input_df["Nhân Sự"].dropna().unique().tolist())
        filter_staff = st.selectbox("Lọc theo Nhân Sự", all_staff_opts, key="f_staff_live")

    # --- BƯỚC 1: LỌC TRƯỚC DỮ LIỆU ĐỂ ĐỒNG BỘ DANH MỤC HẠNG MỤC THEO NHÂN SỰ ---
    df_pre_filter = raw_input_df.copy()
    df_pre_filter["Ngày_DT"] = pd.to_datetime(df_pre_filter["Ngày"], errors='coerce').dt.date
    df_pre_filter = df_pre_filter[(df_pre_filter["Ngày_DT"] >= start_filter_date) & (df_pre_filter["Ngày_DT"] <= end_filter_date)]
    
    if filter_staff != "Tất cả": 
        df_pre_filter = df_pre_filter[df_pre_filter["Nhân Sự"] == filter_staff]

    if enable_hour_filter and start_t and end_t:
        def check_time_pre(t_str):
            try:
                t_val = datetime.datetime.strptime(str(t_str).strip(), "%H:%M:%S").time()
                return start_t <= t_val <= end_t
            except:
                return True
        df_pre_filter = df_pre_filter[df_pre_filter["Thời Gian"].apply(check_time_pre)]

    dynamic_tasks = sorted(df_pre_filter["Hạng Mục Công Việc"].dropna().unique().tolist()) if not df_pre_filter.empty else []
    all_task_opts = ["Tất cả"] + dynamic_tasks

    if st.session_state.get("f_task_live") not in all_task_opts:
        st.session_state["f_task_live"] = "Tất cả"

    with f_col5:
        filter_task = st.selectbox("Lọc theo Hạng Mục", all_task_opts, key="f_task_live")

    # --- BƯỚC 2: LỌC HOÀN CHỈNH ĐỂ HIỂN THỊ BẢNG ---
    filtered_df = df_pre_filter.copy()
    if filter_task != "Tất cả": 
        filtered_df = filtered_df[filtered_df["Hạng Mục Công Việc"] == filter_task]
        
    total_rows = len(filtered_df)
    st.markdown(f"<div style='background: rgba(254, 243, 199, 0.6); padding: 8px 12px; border-radius: 6px; border: 1px solid #f59e0b; margin-bottom: 15px; font-weight: bold; color: #b45309;'>📅 Khoảng ngày có: {total_rows} bản ghi</div>", unsafe_allow_html=True)

    rows_per_page = 10
    total_pages = max(1, (total_rows - 1)
