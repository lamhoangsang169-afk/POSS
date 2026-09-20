# view/bao_cao.py
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
get_production_logs_by_date_range = db_module.get_production_logs_by_date_range
get_total_production_count_db = db_module.get_total_production_count_db

def render_bao_cao(current_menu_name):
    st.subheader(f"📊 {current_menu_name}")
    
    # Tạo bộ chọn khoảng ngày báo cáo
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Từ ngày", now_vn.date() - datetime.timedelta(days=7))
    with col2:
        end_date = st.date_input("Đến ngày", now_vn.date())
        
    if start_date > end_date:
        st.error("⚠️ Ngày bắt đầu không thể lớn hơn ngày kết thúc!")
        return

    # Lấy dữ liệu báo cáo
    report_df = get_production_logs_by_date_range(start_date, end_date)
    
    if not report_df.empty:
        st.success(f"📈 Tìm thấy {len(report_df)} bản ghi sản lượng trong khoảng thời gian này.")
        st.dataframe(report_df, use_container_width=True, hide_index=True)
    else:
        st.info("Không có dữ liệu sản lượng trong khoảng thời gian được chọn.")
