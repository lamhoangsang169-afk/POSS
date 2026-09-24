# APP/view/quan_ly_loi.py
import streamlit as st
import pandas as pd
import datetime
from utils import compress_image_to_base64
import database as db

def render_quan_ly_loi(current_menu_name):
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.header("6. Quản Lý Lỗi Sản Xuất")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_loi"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("### ⚠️ Khai Báo Lỗi Phát Sinh")
    
    # Tải danh mục loại lỗi từ Database Supabase
    ds_loai_loi_hien_tai = db.get_error_categories_db()

    with st.form("form_khai_bao_loi", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ngay_phat_sinh = st.date_input("Ngày phát sinh", value=datetime.date.today())
        with col2:
            staff_options = ["--- Chọn nhân sự liên quan ---"] + st.session_state.get("staff_list", [])
            nhan_su_phat_hien = st.selectbox("Nhân sự chịu trách nhiệm/phát hiện", staff_options)
        with col3:
            phan_loai_loi = st.selectbox("Phân loại lỗi", ds_loai_loi_hien_tai if isinstance(ds_loai_loi_hien_tai, list) else ["Sản phẩm hỏng"])
            
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            so_luong_loi = st.number_input("Số lượng sản phẩm lỗi", min_value=1, value=1, step=1)
        with col_s2:
            ghi_chu_loi = st.text_input("Ghi chú nguyên nhân / Biện pháp xử lý", placeholder="Nhập nguyên nhân và hướng khắc phục...")
            
        # Đưa file_uploader ra ngoài form hoặc xử lý riêng bên dưới form để tránh bị mất buffer file
        submitted = st.form_submit_button("🚨 Ghi Nhận Lỗi Sản Xuất", use_container_width=True)

    # Đặt file_uploader ra ngoài form để bắt file tải lên chính xác 100%
    uploaded_images = st.file_uploader(
        "🖼️ Tải lên hình ảnh đính kèm sự cố (Có thể chọn nhiều ảnh)", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True, 
        key="uploader_loi_images"
    )

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
            
            # Ghép các chuỗi base64 lại với nhau bằng dấu phân cách "|||"
            images_string = "|||".join(compressed_image_list) if compressed_image_list else ""
            
            # Lưu xuống Database Supabase
            response = db.add_error_log_with_images_db(
                ngay=ngay_phat_sinh,
                nhan_su=nhan_su_phat_hien,
                phan_loai_loi=phan_loai_loi,
                so_luong=so_luong_loi,
                ghi_chu=ghi_chu_loi,
                images_base64_str=images_string
            )
            
            if response is not None:
                st.cache_data.clear()
                st.success(f"✅ Đã ghi nhận báo cáo lỗi và lưu thành công {len(compressed_image_list)} ảnh đính kèm lên Database!")
                st.rerun()

    # --- PHẦN TÙY CHỈNH DANH MỤC LỖI (ĐÃ ĐỒNG BỘ DB) ---
    with st.expander("⚙️ Tùy Chỉnh Danh Mục Loại Lỗi (Thêm/Bớt)"):
        current_cats = list(db.get_error_categories_db())
        
        st.markdown("##### ➕ Thêm loại lỗi mới")
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            new_loai_loi = st.text_input("Nhập tên loại lỗi...", placeholder="Nhập tên loại lỗi...", label_visibility="collapsed", key="input_new_loi")
        with col_t2:
            if st.button("Thêm Loại Lỗi", use_container_width=True, key="btn_add_loi_cat"):
                if new_loai_loi.strip():
                    if new_loai_loi.strip() not in current_cats:
                        current_cats.append(new_loai_loi.strip())
                        db.save_error_categories_db(current_cats)
                        st.cache_data.clear()
                        st.success(f"✅ Đã thêm loại lỗi: '{new_loai_loi.strip()}' vào Database!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Loại lỗi này đã tồn tại!")
                else:
                    st.error("⚠️ Vui lòng nhập tên loại lỗi!")

        st.markdown("##### ➖ Xóa loại lỗi không dùng")
        col_x1, col_x2 = st.columns([3, 1])
        with col_x1:
            loai_loi_can_xoa = st.selectbox("Chọn loại lỗi để xóa", current_cats, label_visibility="collapsed", key="select_del_loi")
        with col_x2:
            if st.button("Xóa Loại Lỗi", use_container_width=True, key="btn_del_loi_cat"):
                if len(current_cats) > 1:
                    current_cats.remove(loai_loi_can_xoa)
                    db.save_error_categories_db(current_cats)
                    st.cache_data.clear()
                    st.success(f"✅ Đã xóa loại lỗi: '{loai_loi_can_xoa}' khỏi Database!")
                    st.rerun()
                else:
                    st.error("⚠️ Cần giữ lại ít nhất một phân loại lỗi!")

    st.markdown("---")
    st.subheader("📋 Danh Sách Lỗi Đã Khai Báo")
    
    # Tải dữ liệu từ Database
    df_loi = db.get_error_logs_db()
    
    if not df_loi.empty:
        st.markdown(
            """
            <style>
                .error-img-thumb {
                    width: 60px;
                    height: 60px;
                    object-fit: cover;
                    border-radius: 6px;
                    margin-right: 6px;
                    border: 1px solid #ccc;
                }
            </style>
            """, 
            unsafe_allow_html=True
        )

        for idx, row in df_loi.iterrows():
            st.markdown(f"**STT: {row.get('db_id', idx+1)}** | **Ngày:** {row.get('Ngày')} | **Nhân sự:** {row.get('Nhân Sự')} | **Loại lỗi:** {row.get('Phân Loại Lỗi')} | **Số lượng:** {row.get('Số Lượng')}")
            st.markdown(f"*Ghi chú:* {row.get('Ghi Chú', '')}")
            
            # Đọc và hiển thị ảnh đính kèm từ cột chuỗi base64
            img_data_str = row.get("Số Ảnh Đính Kèm", "")
            if img_data_str and isinstance(img_data_str, str) and "data:image" in img_data_str:
                img_list = img_data_str.split("|||")
                cols_img = st.columns(min(len(img_list), 6))
                for i, b64_img in enumerate(img_list):
                    with cols_img[i % len(cols_img)]:
                        st.markdown(
                            f'<img src="{b64_img}" class="error-img-thumb" title="Ảnh đính kèm lỗi">', 
                            unsafe_allow_html=True
                        )
            else:
                st.caption("🖼️ Không có hình ảnh đính kèm.")
            st.markdown("---")
    else:
        st.info("Chưa có bản ghi lỗi nào trong hệ thống.")
