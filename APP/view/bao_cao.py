# view/thu_muc_bao_cao.py
import streamlit as st
import pandas as pd
import datetime

# Sử dụng import trực tiếp từ module database đã được cấu hình đường dẫn gốc sẵn
from database import update_production_log_deleted_status

def render_thu_muc_bao_cao(current_menu_name):
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.subheader(f"📂 {current_menu_name}")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_folder"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

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

    selected_file_ids = []

    for idx, f in enumerate(active_files, 1):
        with st.container(border=True):
            st.markdown(f"**STT: {idx}** | 📄 **File:** `{f['name']}`")
            st.markdown(f"🔗 [Mở liên kết trực tiếp]({f['url']})")
            
            check_key = f"chk_file_{f['db_id']}_{idx}"
            is_checked = st.checkbox(f"Chọn báo cáo STT {idx}", key=check_key)
            if is_checked:
                selected_file_ids.append(f["db_id"])

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🗑️ Chuyển Các Báo Cáo Đã Chọn Vào Thùng Rác", use_container_width=True, key="btn_move_trash_files"):
        if not selected_file_ids:
            st.error("⚠️ Vui lòng tích chọn vào ô 'Chọn báo cáo' của tệp bạn muốn chuyển vào Thùng Rác!")
        else:
            for f in cloud_files:
                if f["db_id"] in selected_file_ids:
                    f["is_deleted"] = True
            
            st.success("✅ Đã di chuyển các báo cáo được chọn vào Thùng Rác hệ thống thành công!")
            st.rerun()
