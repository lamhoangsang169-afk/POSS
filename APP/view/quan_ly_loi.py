# APP/view/quan_ly_loi.py
import streamlit as st
import pandas as pd

def render_quan_ly_loi(current_menu_name):
    st.header("🛠️ Quản Lý Lỗi / Sự Cố")
    st.markdown("Tại đây bạn có thể ghi nhận, theo dõi và xử lý các lỗi hoặc sự cố phát sinh trong quá trình sản xuất.")
    
    # Ví dụ form hoặc bảng quản lý lỗi
    with st.form("form_them_loi"):
        ngay_loi = st.date_input("Ngày phát sinh lỗi")
        noi_dung_loi = st.text_area("Mô tả chi tiết sự cố / lỗi")
        nguoi_bao_cao = st.text_input("Người báo cáo")
        
        submitted = st.form_submit_button("💾 Lưu Báo Cáo Lỗi", use_container_width=True)
        if submitted:
            st.success("✅ Đã ghi nhận báo cáo lỗi thành công!")
