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

# Lấy các hàm tương tác database từ database.py
safe_supabase_call = getattr(db_module, "safe_supabase_call", None)

def get_report_files_db():
    """Lấy danh sách file báo cáo từ Supabase"""
    if safe_supabase_call is None:
        return []
    try:
        def _query(client):
            return client.table("report_files").select("*").eq("is_deleted", False).order("id", desc=True).execute()
        res = safe_supabase_call(_query)
        return res.data if res and res.data else []
    except Exception:
        return []

def delete_report_files_db(file_ids):
    """Đánh dấu xóa các file báo cáo được chọn trên Supabase"""
    if safe_supabase_call is None or not file_ids:
        return
    try:
        def _query(client):
            return client.table("report_files").update({"is_deleted": True}).in_("id", file_ids).execute()
        safe_supabase_call(_query)
    except Exception:
        pass

def render_thu_muc_bao_cao(current_menu_name):
    # Tiêu đề nghiệp vụ và Nút làm mới
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.subheader(f"📂 {current_menu_name}")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_folder"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Lấy dữ liệu thực tế từ cơ sở dữ liệu Supabase
    active_files = get_report_files_db()

    if not active_files:
        st.info("Thư mục báo cáo trống hoặc tất cả báo cáo đã được chuyển vào Thùng Rác.")
        return

    selected_file_ids = []

    # === HIỂN THỊ DANH SÁCH FILE TỪ DATABASE ===
    for idx, f in enumerate(active_files, 1):
        file_id = f.get("id")
        file_name = f.get("name", "Báo cáo không tên")
        file_url = f.get("url", "#")
        
        with st.container(border=True):
            st.markdown(f"**STT: {idx}** | 📄 **File:** `{file_name}`")
            st.markdown(f"🔗 [Mở liên kết trực tiếp]({file_url})")
            
            # Ô tích chọn nằm ngay phía dưới thông tin tệp
            check_key = f"chk_file_{file_id}_{idx}"
            is_checked = st.checkbox(f"Chọn báo cáo STT {idx}", key=check_key)
            if is_checked:
                selected_file_ids.append(file_id)

    st.markdown("<br>", unsafe_allow_html=True)

    # === NÚT HÀNH ĐỘNG DƯỚI CÙNG ===
    if st.button("🗑️ Chuyển Các Báo Cáo Đã Chọn Vào Thùng Rác", use_container_width=True, key="btn_move_trash_files"):
        if not selected_file_ids:
            st.error("⚠️ Vui lòng tích chọn vào ô 'Chọn báo cáo' của tệp bạn muốn chuyển vào Thùng Rác!")
        else:
            delete_report_files_db(selected_file_ids)
            st.success("✅ Đã di chuyển các báo cáo được chọn vào Thùng Rác hệ thống thành công!")
            st.cache_data.clear()
            st.rerun()
