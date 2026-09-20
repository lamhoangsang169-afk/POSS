# view/thu_muc_bao_cao.py
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
db_module = load_module_from_path("database", db_path)

# Nạp hàm cập nhật trạng thái xóa từ module database
update_production_log_deleted_status = db_module.update_production_log_deleted_status

def render_thu_muc_bao_cao(current_menu_name):
    # Tiêu đề nghiệp vụ và Nút làm mới căn lề chuẩn xác theo giao diện cũ của bạn
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.subheader(f"📂 {current_menu_name}")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_folder"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Khởi tạo dữ liệu file lưu vết mẫu trong Session State nếu hệ thống trống trải
    if "cloud_folders" not in st.session_state or not st.session_state["cloud_folders"]:
        st.session_state["cloud_folders"] = [
            {
                "db_id": 1,
                "name": "bao_cao_san_luong_2026-09-14_den_2026-09-20.csv",
                "url": "https://streamlit.io",
                "is_deleted": False
            }
        ]

    cloud_files = st.session_state["cloud_folders"]
    active_files = [f for f in cloud_files if not f.get("is_deleted", False)]

    if not active_files:
        st.info("Thư mục báo cáo trống hoặc tất cả báo cáo đã được chuyển vào Thùng Rác.")
        return

    # Danh sách lưu các ID được người dùng tích chọn
    selected_file_ids = []

    # === THIẾT KẾ KHỐI CONTAINER CHỨA FILE GIỐNG BẢN CŨ CỦA BẠN ===
    for idx, f in enumerate(active_files, 1):
        with st.container(border=True):
            st.markdown(f"**STT: {idx}** | 📄 **File:** `{f['name']}`")
            st.markdown(f"🔗 [Mở liên kết trực tiếp]({f['url']})")
            
            # Ô tích chọn nằm ngay phía dưới thông tin tệp
            check_key = f"chk_file_{f['db_id']}_{idx}"
            is_checked = st.checkbox(f"Chọn báo cáo STT {idx}", key=check_key)
            if is_checked:
                selected_file_ids.append(f["db_id"])

    st.markdown("<br>", unsafe_allow_html=True)

    # === NÚT HÀNH ĐỘNG DƯỚI CÙNG TRẢI DÀI TOÀN BỘ CHIỀU RỘNG ===
    if st.button("🗑️ Chuyển Các Báo Cáo Đã Chọn Vào Thùng Rác", use_container_width=True, key="btn_move_trash_files"):
        if not selected_file_ids:
            st.error("⚠️ Vui lòng tích chọn vào ô 'Chọn báo cáo' của tệp bạn muốn chuyển vào Thùng Rác!")
        else:
            # Tiến hành cập nhật trạng thái lưu vết trong bộ nhớ tạm
            for f in cloud_files:
                if f["db_id"] in selected_file_ids:
                    f["is_deleted"] = True
            
            st.success("✅ Đã di chuyển các báo cáo được chọn vào Thùng Rác hệ thống thành công!")
            st.rerun()
