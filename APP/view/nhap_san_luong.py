# view/nhap_san_luong.py
import os
import sys
import streamlit as st
import pandas as pd
import datetime
import requests

# Import trực tiếp các module từ hệ thống đã cấu hình sys.path
from utils import VN_TIMEZONE
from database import (
    get_production_logs_db,
    add_production_log_db,
    update_production_log_deleted_status,
    upload_multiple_images_to_storage,
    get_attendance_db,
    get_rules_db,
    update_production_log_record_db
)

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


# ==================== FRAGMENT LỌC TỨC THÌ & TỐI ƯU GIAO DIỆN GIỜ ====================
@st.fragment
def render_production_table_fragment(raw_input_df, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_date = now_vn.date()
    
    if "last_checked_date" not in st.session_state or st.session_state.last_checked_date != today_date:
        st.session_state.last_checked_date = today_date
        st.session_state.f_start_live = today_date
        st.session_state.f_end_live = today_date
    
    col_title_1, col_title_2 = st.columns([3, 1])
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input_frag"):
            st.session_state.f_start_live = today_date
            st.session_state.f_end_live = today_date
            st.cache_data.clear()
            st.rerun()

    if raw_input_df.empty:
        st.info("Chưa có dữ liệu sản lượng.")
        return

    f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.1, 1.1, 1.4, 1.3, 1.3, 1.2])
    
    with f_col1:
        start_filter_date = st.date_input("Từ ngày", value=st.session_state.get("f_start_live", today_date), key="f_start_live")
    with f_col2:
        end_filter_date = st.date_input("Đến ngày", value=st.session_state.get("f_end_live", today_date), key="f_end_live")
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

    try:
        rules_df = get_rules_db()
    except Exception:
        rules_df = pd.DataFrame()
    raw_tasks = rules_df["Hạng Mục Công Việc"].tolist() if not rules_df.empty and "Hạng Mục Công Việc" in rules_df.columns else []
    danh_sach_hang_muc = [str(t).strip() for t in raw_tasks if pd.notna(t) and str(t).strip() and str(t).strip().lower() not in ["nan", "none"]]
    if not danh_s
