import os
import sys
import streamlit as st

# ==================== CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG CHUẨN XÁC ====================
# Đảm bảo hệ thống nhận diện thư mục gốc chứa database.py và utils.py
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Đảm bảo hệ thống nhận diện thư mục APP/view chứa các trang nghiệp vụ
view_path = os.path.join(current_dir, "APP", "view")
if view_path not in sys.path:
    sys.path.insert(0, view_path)

# thiết lập biến môi trường để hỗ trợ các module con truy xuất ngược
os.environ["PYTHONPATH"] = current_dir

# ==================== IMPORT CÁC TRANG NGHIỆP VỤ TỪ APP/view ====================
import nhap_san_luong
import cham_cong
import bao_cao
import thu_muc_bao_cao
import dinh_muc_cong_viec
import thung_rac

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
