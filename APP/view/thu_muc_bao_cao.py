# view/thu_muc_bao_cao.py
import os
import sys
import importlib.util
import streamlit as st

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

# Nạp database.py từ thư mục gốc dự án
db_path = os.path.join(root_project_dir, "database.py")
db_module = load_module_from_path("database", db_path)

# Trích xuất hàm cần thiết từ module đã nạp
load_folders_db = db_module.load_folders_db

def render_thu_muc_bao_cao(current_menu_name):
    st.subheader(f"📂 {current_menu_name}")
    
    # Tải danh sách thư mục từ database
    folders_data = load_folders_db()
    
    if folders_data:
        st.success("📂 Đã tải danh sách thư mục báo cáo thành công.")
        for folder in folders_data:
            with st.expander(folder.get("folder_name", "Thư mục không tên")):
                for item in folder.get("items", []):
                    st.write(f"📄 {item.get('name', 'Tài liệu chưa đặt tên')}")
    else:
        st.info("Chưa có cấu trúc thư mục báo cáo nào được thiết lập.")
