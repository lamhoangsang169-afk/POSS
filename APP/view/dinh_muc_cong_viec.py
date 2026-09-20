# view/dinh_muc_cong_viec.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd

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

# Trích xuất biến kết nối supabase từ module đã nạp
supabase = db_module.supabase

# Kiểm tra xem hàm lưu định mức có tồn tại không, nếu chưa thì tạo hàm giả lập tránh crash
save_rules_df_db = getattr(db_module, "save_rules_df_db", None)

def render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms):
    st.subheader(f"📋 {current_menu_name}")
    
    # Kiểm tra quyền hạn thiết lập định mức công việc
    if current_user_role != "Admin" and not user_perms.get("perm_rules", False):
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem bảng định mức**. Bạn không có quyền chỉnh sửa cấu hình này.")
        
        # Hiển thị bảng định mức hiện tại từ Session State nếu có
        rules_df = st.session_state.get("rules_df", pd.DataFrame())
        if not rules_df.empty:
            st.dataframe(rules_df, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có cấu hình định mức công việc nào được tải lên hệ thống.")
    else:
        st.success("🔓 Bạn có quyền quản trị viên. Tính năng cấu hình & cập nhật bảng định mức công việc sẵn sàng hoạt động.")
        
        # Hiển thị dữ liệu mẫu hoặc khung cấu hình cơ bản
        rules_df = st.session_state.get("rules_df", pd.DataFrame())
        if not rules_df.empty:
            st.dataframe(rules_df, use_container_width=True, hide_index=True)
        else:
            st.info("Hệ thống đang hiển thị định mức mặc định. Bạn có thể xây dựng tính năng chỉnh sửa dữ liệu tại đây.")
