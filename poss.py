import streamlit as st

# ==================== IMPORT CÁC TRANG NGHIỆP VỤ THEO ĐƯỜNG DẪN CHUẨN ====================
from APP.view import nhap_san_luong
from APP.view import cham_cong
from APP.view import bao_cao
from APP.view import thu_muc_bao_cao
from APP.view import dinh_muc_cong_viec
from APP.view import thung_rac

# Giả lập biến quyền user_perms và vai trò user_role để tránh lỗi crash nếu chưa định nghĩa
if "user_perms" not in st.session_state:
    st.session_state["user_perms"] = {"perm_input": True, "perm_rules": True}
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "Admin"

user_perms = st.session_state["user_perms"]
current_user_role = st.session_state["user_role"]

@st.fragment
def render_main_content(current_menu_name):
    # ==================== ĐIỀU HƯỚNG CÁC TRANG NGHIỆP VỤ ====================
    if current_menu_name in ["1. Nhập Sản Lượng", "input_production"]:
        nhap_san_luong.render_nhap_san_luong(current_menu_name, current_user_role, user_perms)
        
    elif current_menu_name == "⏱️ Chấm Công Ca Làm Việc":
        cham_cong.render_cham_cong(current_menu_name, current_user_role)
        
    elif current_menu_name in ["📊 Báo Cáo & Biểu Đồ", "report"]:
        bao_cao.render_bao_cao(current_menu_name)
        
    elif current_menu_name in ["📂 Thư Mục Báo Cáo", "report_folder"]:
        thu_muc_bao_cao.render_thu_muc_bao_cao(current_menu_name)
        
    elif current_menu_name in ["📋 Định Mức Công Việc", "rules"]:
        dinh_muc_cong_viec.render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms)
        
    elif current_menu_name in ["🗑️ Thùng Rác", "trash"]:
        thung_rac.render_thung_rac(current_menu_name, current_user_role)
