# APP/view/quan_ly_loi.py
import streamlit as st
import pandas as pd
import datetime

def render_quan_ly_loi(current_menu_name):
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.header("6. Quản Lý Lỗi Sản Xuất")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_loi"):
            st.cache_data.clear()
            st.rerun()

    # Khởi tạo danh sách loại lỗi mặc định trong session_state nếu chưa có
    if "ds_loai_loi" not in st.session_state:
        st.session_state.ds_loai_loi = ["Khác", "Lỗi nguyên vật liệu", "Lỗi thao tác", "Lỗi máy móc / thiết bị"]

    # Khung tùy chỉnh danh mục loại lỗi (Thêm/Bớt) giống hình mẫu
    with st.expander("⚙️ Tùy Chỉnh Danh Mục Loại Lỗi (Thêm/Bớt)"):
        st.markdown("##### ➕ Thêm loại lỗi mới")
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            new_loai_loi = st.text_input("Nhập tên loại lỗi...", placeholder="Nhập tên loại lỗi...", label_visibility="collapsed")
        with col_t2:
            if st.button("Thêm Loại Lỗi", use_container_width=True):
                if new_loai_loi.strip():
                    if new_loai_loi.strip() not in st.session_state.ds_loai_loi:
                        st.session_state.ds_loai_loi.append(new_loai_loi.strip())
                        st.success(f"✅ Đã thêm loại lỗi: '{new_loai_loi.strip()}'")
                        st.rerun()
                    else:
                        st.warning("⚠️ Loại lỗi này đã tồn tại trong danh sách!")
                else:
                    st.error("⚠️ Vui lòng nhập tên loại lỗi!")

        st.markdown("##### ➖ Xóa loại lỗi không dùng")
        col_x1, col_x2 = st.columns([3, 1])
        with col_x1:
            loai_loi_can_xoa = st.selectbox("Chọn loại lỗi để xóa", st.session_state.ds_loai_loi, label_visibility="collapsed")
        with col_x2:
            if st.button("Xóa Loại Lỗi", use_container_width=True):
                if len(st.session_state.ds_loai_loi) > 1:
                    st.session_state.ds_loai_loi.remove(loai_loi_can_xoa)
                    st.success(f"✅ Đã xóa loại lỗi: '{loai_loi_can_xoa}'")
                    st.rerun()
                else:
                    st.error("⚠️ Cần giữ lại ít nhất một phân loại lỗi!")

    st.markdown("### ⚠️ Khai Báo Lỗi Phát Sinh")
    
    with st.form("form_khai_bao_loi"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ngay_phat_sinh = st.date_input("Ngày phát sinh", value=datetime.date.today())
        with col2:
            staff_options = ["--- Chọn nhân sự liên quan ---"] + st.session_state.get("staff_list", [])
            nhan_su_phat_hien = st.selectbox("Nhân sự chịu trách nhiệm/phát hiện", staff_options)
        with col3:
            # Danh sách phân loại lỗi tự động cập nhật theo các mục bạn đã thêm/bớt ở trên
            phan_loai_loi = st.selectbox("Phân loại lỗi", st.session_state.ds_loai_loi)
            
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
    st.info("Chưa có bản ghi lỗi nào trong hệ thống.")
