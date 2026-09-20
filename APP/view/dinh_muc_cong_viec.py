# view/dinh_muc_cong_viec.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd

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
db_module = load_module_from_path("database", db_path)

# Trích xuất hàm lấy định mức từ tệp database vừa cập nhật
get_rules_db = db_module.get_rules_db

def render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms):
    st.subheader(f"📋 {current_menu_name}")
    
    # 1. Khởi chạy tiến trình đọc dữ liệu trực tiếp từ bảng 'rules' của Supabase
    with st.spinner("🔄 Đang tải bảng định mức công việc..."):
        rules_df = get_rules_db()
        # Lưu vào Session State để file nhap_san_luong.py có thể dùng chung dữ liệu danh mục
        st.session_state["rules_df"] = rules_df

    # 2. Kiểm tra hiển thị giao diện theo quyền hạn
    if current_user_role != "Admin" and not user_perms.get("perm_rules", False):
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem bảng định mức**. Bạn không có quyền chỉnh sửa cấu hình này.")
    else:
        st.success("🔓 Bạn có quyền quản trị viên. Tính năng cấu hình & cập nhật bảng định mức công việc sẵn sàng hoạt động.")
        
    st.markdown("---")
    
    # 3. Kết xuất bảng dữ liệu lên màn hình giao diện chính
    if not rules_df.empty:
        st.markdown("### 📊 Danh Mục Tham Chiếu Hệ Số Điểm")
        st.dataframe(rules_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Hiện tại bảng dữ liệu 'rules' trên Supabase chưa có bản ghi nào hoặc tên các cột bị lệch. Vui lòng kiểm tra lại Database!")
