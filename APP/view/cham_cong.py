# view/cham_cong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime

# ==================== NẠP MODULE ĐỘNG THEO ĐƯỜNG DẪN TUYỆT ĐỐI ====================
current_file_dir = os.path.dirname(os.path.abspath(__file__))
root_project_dir = os.path.dirname(os.path.dirname(current_file_dir))

# Hàm nạp file python động bất chấp môi trường Windows/Linux
def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Nạp database.py và utils.py từ thư mục gốc dự án
db_path = os.path.join(root_project_dir, "database.py")
utils_path = os.path.join(root_project_dir, "utils.py")

db_module = load_module_from_path("database", db_path)
utils_module = load_module_from_path("utils", utils_path)

# Trích xuất các hàm và biến cần thiết từ module đã nạp
VN_TIMEZONE = utils_module.VN_TIMEZONE
get_attendance_db = db_module.get_attendance_db

# Kiểm tra xem các hàm chấm công có tồn tại trong database.py không, nếu chưa có thì tạo hàm giả lập để tránh crash
add_attendance_log_db = getattr(db_module, "add_attendance_log_db", None)
update_attendance_checkout_db = getattr(db_module, "update_attendance_checkout_db", None)

def render_cham_cong(current_menu_name, current_user_role):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = str(now_vn.date())
    current_time_str = now_vn.strftime("%H:%M:%S")

    col_att_h1, col_att_h2 = st.columns()
    with col_att_h1:
        st.subheader(f"{current_menu_name} ({today_str})")
    with col_att_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_att"):
            st.cache_data.clear()
            st.rerun()

    # Tạo giao diện Chấm công cơ bản dựa trên quyền hạn
    st.info(f"⏰ Thời gian hệ thống hiện tại: **{current_time_str}**")
    
    # Đọc danh sách chấm công hiện tại
    att_df = get_attendance_db()
    if not att_df.empty:
        st.dataframe(att_df, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu chấm công ngày hôm nay.")
