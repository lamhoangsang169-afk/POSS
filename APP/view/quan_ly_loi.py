# APP/view/quan_ly_loi.py
import streamlit as st
import pandas as pd
import datetime
import base64
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

    # Sử dụng st.form để gom nhóm và chống chớp màn hình khi chọn selectbox/nhập liệu
    with st.form("form_khai_bao_loi", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ngay_phat_sinh = st.date_input("Ngày phát sinh", value=datetime.date.today(), key="input_ngay_loi")
        with col2:
            staff_options = ["--- Chọn nhân sự liên quan ---"] + st.session_state.get("staff_list", [])
            nhan_su_phat_hien = st.selectbox("Nhân sự chịu trách nhiệm/phát hiện", staff_options, key="select_nhan_su_loi")
        with col3:
            phan_loai_loi = st.selectbox("Phân loại lỗi", ds_loai_loi_hien_tai if isinstance(ds_loai_loi_hien_tai, list) else ["Sản phẩm hỏng"], key="select_phan_loai_loi")
            
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            so_luong_loi = st.number_input("Số lượng sản phẩm lỗi", min_value=1, value=1, step=1, key="num_so_luong_loi")
        with col_s2:
            ghi_chu_loi = st.text_input("Ghi chú nguyên nhân / Biện pháp xử lý", placeholder="Nhập nguyên nhân và hướng khắc phục...", key="txt_ghi_chu_loi")
            
        # Nút submit của form
        submitted = st.form_submit_button("🚨 Ghi Nhận Lỗi Sản Xuất", use_container_width=True)

    # Đặt file_uploader ngay dưới form để người dùng chọn ảnh đính kèm ổn định
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
                    try:
                        img_bytes = img_file.read()
                        encoded_str = base64.b64encode(img_bytes).decode("utf-8")
                        mime_type = img_file.type if img_file.type else "image/jpeg"
                        b64_data_uri = f"data:{mime_type};base64,{encoded_str}"
                        compressed_image_list.append(b64_data_uri)
                    except Exception as e:
                        st.error(f"Lỗi đọc file ảnh: {e}")
            
            images_string = "|||".join(compressed_image_list) if compressed_image_list else ""
            
            # Ghi dữ liệu xuống Supabase
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

    # --- PHẦN TÙY CHỈNH DANH MỤC LỖI (THÊM/BỚT) ---
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
                .log-card {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin-bottom: 10px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                }
                .log-card-text {
                    font-size: 14px;
                    color: #333333;
                    line-height: 1.5;
                }
                .error-thumb-img {
                    width: 70px;
                    height: 70px;
                    object-fit: cover;
                    border-radius: 6px;
                    border: 1px solid #ccc;
                    margin-bottom: 5px;
                }
            </style>
            """, 
            unsafe_allow_html=True
        )

        for idx, row in df_loi.iterrows():
            stt_hien_thi = row.get('db_id', idx+1)
            ngay_val = row.get('Ngày', '')
            nhan_su_val = row.get('Nhân Sự', '')
            phan_loai_val = row.get('Phân Loại Lỗi', '')
            so_luong_val = row.get('Số Lượng', 1)
            ghi_chu_val = row.get('Ghi Chú', '')
            
            img_data_str = row.get("Số Ảnh Đính Kèm", "")

            col_info, col_imgs = st.columns([4, 1.2])

            with col_info:
                st.markdown(
                    f"""
                    <div class="log-card">
                        <div class="log-card-text">
                            <b>STT: {stt_hien_thi}</b> | 📅 <b>Ngày:</b> {ngay_val} | 👤 <b>Nhân sự:</b> {nhan_su_val}<br>
                            📌 <b>Loại lỗi:</b> <span style="color: #d9534f; font-weight: bold;">{phan_loai_val}</span> | 📦 <b>Số lượng:</b> {so_luong_val} Cái<br>
                            💬 <i>Ghi chú:</i> {ghi_chu_val if ghi_chu_val else "Không có ghi chú"}
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

            with col_imgs:
                if img_data_str and isinstance(img_data_str, str) and len(img_data_str.strip()) > 20 and "data:image" in img_data_str:
                    img_list = img_data_str.split("|||")
                    img_cols = st.columns(min(len(img_list), 3))
                    for i, b64_img in enumerate(img_list):
                        with img_cols[i % len(img_cols)]:
                            st.markdown(
                                f'<img src="{b64_img}" class="error-thumb-img" title="Ảnh đính kèm lỗi">', 
                                unsafe_allow_html=True
                            )
                else:
                    st.caption("🖼️ Không có ảnh.")
            
            st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
    else:
        st.info("Chưa có bản ghi lỗi nào trong hệ thống.")
