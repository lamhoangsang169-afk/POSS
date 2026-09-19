import streamlit as st

# Import từ thư mục phieu_giao_dien
from phieu_giao_dien import (
    nhap_san_luong,
    cham_cong,
    bao_cao,
    thu_muc_bao_cao,
    dinh_muc_cong_viec,
    thung_rac
)

@st.fragment
def render_main_content(current_menu_name):
    # ==================== ĐIỀU HƯỚNG CÁC TRANG NGHIỆP VỤ ====================
    if current_menu_name in ["1. Nhập Sản Lượng", "input_production"]:
        nhap_san_luong.render(user_perms)
        
    elif current_menu_name == "⏱️ Chấm Công Ca Làm Việc":
        cham_cong.render(user_perms)
        
    elif current_menu_name in ["📊 Báo Cáo & Biểu Đồ", "report"]:
        bao_cao.render(user_perms)
        
    elif current_menu_name in ["📂 Thư Mục Báo Cáo", "report_folder"]:
        thu_muc_bao_cao.render(user_perms)
        
    elif current_menu_name in ["📋 Định Mức Công Việc", "rules"]:
        dinh_muc_cong_viec.render(user_perms)
        
    elif current_menu_name in ["🗑️ Thùng Rác", "trash"]:
        thung_rac.render(user_perms)
