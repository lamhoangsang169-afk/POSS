# APP/view/quan_ly_loi.py
import streamlit as st
import pandas as pd
import datetime

def render_quan_ly_loi(current_menu_name):
    # Tiêu đề trang khớp với hình mẫu
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.header("6. Quản Lý Lỗi Sản Xuất")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_loi"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("### ⚠️ Khai Báo Lỗi Phát Sinh")
    
    with st.form("form_khai_bao_loi"):
        # Hàng thứ nhất gồm 3 cột
        col1, col2, col3 = st.columns(3)
        with col1:
            ngay_phat_sinh = st.date_input("Ngày phát sinh", value=datetime.date.today())
        with col2:
            # Lấy danh sách nhân sự từ session nếu có, hoặc danh sách mẫu
            staff_options = ["--- Chọn nhân sự liên quan ---"] + st.session_state.get("staff_list", [])
            nhan_su_phat_hien = st.selectbox("Nhân sự chịu trách nhiệm/phát hiện", staff_options)
        with col3:
            phan_loai_loi = st.selectbox("Phân loại lỗi", ["Khác", "Lỗi nguyên vật liệu", "Lỗi thao tác", "Lỗi máy móc / thiết bị"])
            
        # Hàng thứ hai gồm 2 cột
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            so_luong_loi = st.number_input("Số lượng sản phẩm lỗi", min_value=1, value=1, step=1)
        with col_s2:
            ghi_chu_loi = st.text_input("Ghi chú nguyên nhân / Biện pháp xử lý", placeholder="Nhập nguyên nhân và hướng khắc phục...")
            
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚨 Ghi Nhận Lỗi Sản Xuất", use_container_width=True)
        if submitted:
            if nhan_su_phat_hien == "--- Chọn nhân sự liên quan ---":
                st.warning("⚠️ Vui lòng chọn nhân sự liên quan!")
            else:
                st.success("✅ Đã ghi nhận báo cáo lỗi sản xuất thành công!")

    st.markdown("---")
    st.subheader("📋 Danh Sách Lỗi Đã Khai Báo")
    
    # Hiển thị thông báo khi chưa có dữ liệu hoặc bảng dữ liệu trống
    st.info("Chưa có bản ghi lỗi nào trong hệ thống.")
