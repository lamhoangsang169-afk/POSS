import os
import sys
import streamlit as st
import pandas as pd

# ==================== CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG GỐC ====================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

view_path = os.path.join(current_dir, "APP", "view")
if view_path not in sys.path:
    sys.path.insert(0, view_path)

os.environ["PYTHONPATH"] = current_dir

# ==================== IMPORT CÁC TRANG NGHIỆP VỤ TỪ APP/view ====================
import nhap_san_luong
import cham_cong
import bao_cao
import thu_muc_bao_cao
import dinh_muc_cong_viec
import thung_rac
from database import get_rules_db # <--- Đã thêm import hàm lấy định mức

# Cấu hình hiển thị trang web Streamlit
st.set_page_config(page_title="Hệ Thống Quản Lý POSS", page_icon="🏭", layout="wide")

# Khởi tạo các biến quyền và vai trò mặc định trong Session State nếu chưa có
if "user_perms" not in st.session_state:
    st.session_state["user_perms"] = {"perm_input": True, "perm_rules": True}
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "Admin"

# ==================== BỔ SUNG KHỞI TẠO RULES_DF VÀO SESSION STATE ====================
if "rules_df" not in st.session_state:
    try:
        st.session_state["rules_df"] = get_rules_db()
    except Exception:
        st.session_state["rules_df"] = pd.DataFrame()

user_perms = st.session_state["user_perms"]
current_user_role = st.session_state["user_role"]

# ==================== THIẾT KẾ GIAO DIỆN THANH MENU BÊN TRÁI (SIDEBAR) ====================
st.sidebar.title("🏭 Hệ Thống POSS")
st.sidebar.write(f"👤 Vai trò: **{current_user_role}**")
st.sidebar.markdown("---")

# Tạo danh sách menu lựa chọn cho người dùng
menu_options = [
    "1. Nhập Sản Lượng",
    "⏱️ Chấm Công Ca Làm Việc",
    "📊 Báo Cáo & Biểu Đồ",
    "📂 Thư Mục Báo Cáo",
    "📋 Định Mức Công Việc",
    "🗑️ Thùng Rác"
]
choice = st.sidebar.radio("📌 Danh Mục Nghiệp Vụ", menu_options)

# ==================== ĐIỀU HƯỚNG VÀ HIỂN THỊ NỘI DUNG CHÍNH ====================
@st.fragment
def render_main_content(current_menu_name):
    if current_menu_name == "1. Nhập Sản Lượng":
        nhap_san_luong.render_nhap_san_luong(current_menu_name, current_user_role, user_perms)
        
    elif current_menu_name == "⏱️ Chấm Công Ca Làm Việc":
        cham_cong.render_cham_cong(current_menu_name, current_user_role)
        
    elif current_menu_name == "📊 Báo Cáo & Biểu Đồ":
        bao_cao.render_bao_cao(current_menu_name)
        
    elif current_menu_name == "📂 Thư Mục Báo Cáo":
        thu_muc_bao_cao.render_thu_muc_bao_cao(current_menu_name)
        
    elif current_menu_name == "📋 Định Mức Công Việc":
        dinh_muc_cong_viec.render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms)
        
    elif current_menu_name == "🗑️ Thùng Rác":
        thung_rac.render_thung_rac(current_menu_name, current_user_role)

# Kích hoạt gọi hàm hiển thị nội dung trang được chọn lên màn hình chính
render_main_content(choice)
