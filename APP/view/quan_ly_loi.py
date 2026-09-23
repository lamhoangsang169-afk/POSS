# APP/view/quan_ly_loi.py
import streamlit as st
import pandas as pd
import datetime
from utils import compress_image_to_base64
# Import các hàm database riêng cho phần lỗi để không ảnh hưởng file khác
from database import get_error_logs_db, add_error_log_db

def render_quan_ly_loi(current_menu_name):
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.header("6. Quản Lý Lỗi Sản Xuất")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_loi"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("### ⚠️ Khai Báo Lỗi Phát Sinh")
    
    # Khởi tạo danh mục loại lỗi
    if "ds_loai_loi" not in st.session_state:
        st.session_state.ds_loai_loi = ["Sản phẩm hỏng", "Lỗi nguyên vật liệu", "Lỗi thao tác", "Lỗi máy móc / thiết bị", "Khác"]

    with st.form("form_khai_bao_loi", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ngay_phat_sinh = st.date_input("Ngày phát sinh", value=datetime.date.today())
        with col2:
            staff_options = ["--- Chọn nhân sự liên quan ---"] + st.session_state.get("staff_list", [])
            nhan_su_phat_hien = st.selectbox("Nhân sự chịu trách nhiệm/phát hiện", staff_options)
        with col3:
            phan_loai_loi = st.selectbox("Phân loại lỗi", st.session_state.ds_loai_loi)
            
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            so_luong_loi = st.number_input("Số lượng sản phẩm lỗi", min_value=1, value=1, step=1)
        with col_s2:
            ghi_chu_loi = st.text_input("Ghi chú nguyên nhân / Biện pháp xử lý", placeholder="Nhập nguyên nhân và hướng khắc phục...")
            
        uploaded_images = st.file_uploader(
            "🖼️ Tải lên hình ảnh đính kèm sự cố (Có thể chọn nhiều ảnh)", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True, 
            key="uploader_loi_images"
        )
            
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚨 Ghi Nhận Lỗi Sản Xuất", use_container_width=True)
        
        if submitted:
            if nhan_su_phat_hien == "--- Chọn nhân sự liên quan ---":
                st.warning("⚠️ Vui lòng chọn nhân sự liên quan!")
            else:
                compressed_image_list = []
                if uploaded_images:
                    for img_file in uploaded_images:
                        compressed_b64 = compress_image_to_base64(img_file, max_size=(800, 800), quality=70)
                        if compressed_b64:
                            compressed_image_list.append(compressed_b64)
                
                # Lưu trực tiếp xuống cơ sở dữ liệu Supabase thay vì chỉ lưu session_state
                response = add_error_log_db(
                    ngay=ngay_phat_sinh,
                    nhan_su=nhan_su_phat_hien,
                    phan_loai_loi=phan_loai_loi,
                    so_luong=so_luong_loi,
                    ghi_chu=ghi_chu_loi,
                    so_anh_dinh_kem=len(compressed_image_list)
                )
                
                if response is not None:
                    st.cache_data.clear() # Xóa cache để tải lại dữ liệu mới nhất
                    st.success(f"✅ Đã lưu báo cáo lỗi lên Database thành công! (Xử lý {len(compressed_image_list)} ảnh đính kèm)")
                    st.rerun()

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
                    st.error("⚠️ Vui lòng nhập tên loại lỗi!") # Đã sửa lỗi chính tả nhỏ ở đây

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

    st.markdown("---")
    st.subheader("📋 Danh Sách Lỗi Đã Khai Báo")
    
    # Tải trực tiếp dữ liệu từ Database thay vì đọc session_state
    df_loi = get_error_logs_db()
    
    if not df_loi.empty:
        # Thêm cột STT tự tăng trực quan
        df_loi.insert(0, "STT", range(1, len(df_loi) + 1))
        # Ẩn cột mã ID hệ thống nếu không cần thiết hiển thị
        display_columns = [col for col in df_loi.columns if col != "db_id"]
        st.dataframe(df_loi[display_columns], use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có bản ghi lỗi nào trong hệ thống.")
