# APP/view/quan_ly_loi.py
import streamlit as st
import pandas as pd
import datetime
import base64
import database as db

def render_quan_ly_loi(current_menu_name):
    # Khởi tạo các biến session state để lưu trạng thái bộ lọc tránh bị mất khi F5 hoặc thao tác
    if "loi_start_date" not in st.session_state:
        st.session_state.loi_start_date = datetime.date.today() - datetime.timedelta(days=30)
    if "loi_end_date" not in st.session_state:
        st.session_state.loi_end_date = datetime.date.today()
    if "loi_filter_ns" not in st.session_state:
        st.session_state.loi_filter_ns = "Tất cả"
    if "loi_filter_cat" not in st.session_state:
        st.session_state.loi_filter_cat = "Tất cả"
    if "loi_page_num" not in st.session_state:
        st.session_state.loi_page_num = 1

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
            ngay_phat_sinh = st.date_input("Ngày phát sinh", value=datetime.date.today(), key="input_ngay_loi")
        with col2:
            staff_options = ["--- Vui lòng chọn nhân sự ---"] + st.session_state.get("staff_list", [])
            nhan_su_phat_hien = st.selectbox("Nhân sự chịu trách nhiệm/phát hiện", staff_options, key="select_nhan_su_loi")
        with col3:
            phan_loai_loi = st.selectbox("Phân loại lỗi", ds_loai_loi_hien_tai if isinstance(ds_loai_loi_hien_tai, list) else ["Sản phẩm hỏng"], key="select_phan_loai_loi")
            
        uploaded_images = st.file_uploader(
            "Tải ảnh đính kèm (Tối đa nhiều ảnh)", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True, 
            key="uploader_loi_images"
        )
            
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            so_luong_loi = st.number_input("Số lượng", min_value=0, value=0, step=1, key="num_so_luong_loi")
        with col_s2:
            ghi_chu_loi = st.text_input("Ghi chú", placeholder="Nhập ghi chú nguyên nhân / hướng khắc phục...", key="txt_ghi_chu_loi")
            
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚨 Ghi Nhận Lỗi Sản Xuất", use_container_width=True)

    if submitted:
        if nhan_su_phat_hien == "--- Vui lòng chọn nhân sự ---":
            st.warning("⚠️ Vui lòng chọn nhân sự liên quan!")
        elif so_luong_loi <= 0:
            st.warning("⚠️ Vui lòng nhập số lượng sản phẩm lỗi lớn hơn 0!")
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

    # --- PHẦN TÙY CHỈNH DANH MỤC LỖI ---
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
    st.subheader("📋 Danh Sách Lỗi & Bộ Lọc Nâng Cao")
    
    # --- BỘ LỌC ĐƯỢC ĐẶT CHUNG TRÊN 1 HÀNG GỒM 5 CỘT ---
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
    with f_col1:
        st.session_state.loi_start_date = st.date_input("Từ ngày", value=st.session_state.loi_start_date, key="widget_loi_start")
    with f_col2:
        st.session_state.loi_end_date = st.date_input("Đến ngày", value=st.session_state.loi_end_date, key="widget_loi_end")
    with f_col3:
        staff_filter_opts = ["Tất cả"] + st.session_state.get("staff_list", [])
        curr_ns_idx = staff_filter_opts.index(st.session_state.loi_filter_ns) if st.session_state.loi_filter_ns in staff_filter_opts else 0
        st.session_state.loi_filter_ns = st.selectbox("Lọc theo Nhân Sự", staff_filter_opts, index=curr_ns_idx, key="widget_loi_ns")
    with f_col4:
        cat_filter_opts = ["Tất cả"] + list(ds_loai_loi_hien_tai)
        curr_cat_idx = cat_filter_opts.index(st.session_state.loi_filter_cat) if st.session_state.loi_filter_cat in cat_filter_opts else 0
        st.session_state.loi_filter_cat = st.selectbox("Lọc theo Phân Loại Lỗi", cat_filter_opts, index=curr_cat_idx, key="widget_loi_cat")
    with f_col5:
        st.session_state.loi_page_num = st.number_input("Trang hiển thị", min_value=1, value=st.session_state.loi_page_num, step=1, key="widget_loi_pagenum")

    if st.session_state.loi_start_date > st.session_state.loi_end_date:
        st.error("⚠️ Ngày bắt đầu không thể lớn hơn ngày kết thúc!")
        return

    # Tải dữ liệu lỗi từ Database
    df_loi = db.get_error_logs_db(limit_rows=2000)
    
    if not df_loi.empty:
        df_loi["Ngày_DT"] = pd.to_datetime(df_loi["Ngày"], errors="coerce").dt.date
        
        filtered_df = df_loi[(df_loi["Ngày_DT"] >= st.session_state.loi_start_date) & (df_loi["Ngày_DT"] <= st.session_state.loi_end_date)]
        
        if st.session_state.loi_filter_ns != "Tất cả":
            filtered_df = filtered_df[filtered_df["Nhân Sự"] == st.session_state.loi_filter_ns]
            
        if st.session_state.loi_filter_cat != "Tất cả":
            filtered_df = filtered_df[filtered_df["Phân Loại Lỗi"] == st.session_state.loi_filter_cat]

        total_records = len(filtered_df)
        st.info(f"📅 Khoảng ngày có: {total_records} bản ghi lỗi")

        if total_records > 0:
            page_size = 10  # Mặc định hiển thị 10 dòng mỗi trang
            total_pages = max(1, (total_records + page_size - 1) // page_size)
            
            if st.session_state.loi_page_num > total_pages:
                st.session_state.loi_page_num = total_pages

            start_idx = (st.session_state.loi_page_num - 1) * page_size
            end_idx = start_idx + page_size
            page_df = filtered_df.iloc[start_idx:end_idx].reset_index(drop=True)

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

            # --- CÁC NÚT THAO TÁC NẰM PHÍA TRÊN DANH SÁCH ---
            st.markdown("---")
            selected_db_ids = []
            
            col_act1, col_act2 = st.columns([2, 2])
            with col_act1:
                btn_del_selected = st.button("🗑️ Xóa các dòng đã chọn", use_container_width=True, type="primary")
            with col_act2:
                confirm_del_all = st.checkbox("Xác nhận xóa tất cả bản ghi trong trang này", value=False, key="chk_confirm_del_page")
                btn_del_all = st.button("🗑️ Xóa tất cả trang này", use_container_width=True)
            st.markdown("---")

            # Duyệt danh sách hiển thị
            for idx, row in page_df.iterrows():
                db_id = row.get('db_id')
                stt_hien_thi = start_idx + idx + 1
                ngay_val = row.get('Ngày', '')
                nhan_su_val = row.get('Nhân Sự', '')
                phan_loai_val = row.get('Phân Loại Lỗi', '')
                so_luong_val = row.get('Số Lượng', 0)
                ghi_chu_val = row.get('Ghi Chú', '')
                img_data_str = row.get("Số Ảnh Đính Kèm", "")

                col_chk, col_info, col_imgs = st.columns([0.4, 3.8, 1.2])

                with col_chk:
                    is_selected = st.checkbox("Chọn", value=False, key=f"chk_loi_{db_id}", label_visibility="collapsed")
                    if is_selected:
                        selected_db_ids.append(db_id)

                with col_info:
                    st.markdown(
                        f"""
                        <div class="log-card">
                            <div class="log-card-text">
                                <b>STT: {stt_hien_thi} (ID: {db_id})</b> | 📅 <b>Ngày:</b> {ngay_val} | 👤 <b>Nhân sự:</b> {nhan_su_val}<br>
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
                                # Tích hợp nút Fullscreen (⤢) bằng popover
                                with st.popover("⤢", help="Fullscreen"):
                                    st.markdown("##### 🔍 Chi Tiết Ảnh Lỗi")
                                    try:
                                        header, encoded = b64_img.split(",", 1)
                                        img_bytes = base64.b64decode(encoded)
                                        st.image(img_bytes, use_container_width=True)
                                    except Exception:
                                        st.error("Không thể tải ảnh phóng to.")
                                
                                st.markdown(
                                    f'<img src="{b64_img}" class="error-thumb-img" title="Ảnh đính kèm lỗi">', 
                                    unsafe_allow_html=True
                                )
                    else:
                        st.caption("🖼️ Không có ảnh.")
                
                st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

            # Xử lý sự kiện xóa
            if btn_del_selected:
                if selected_db_ids:
                    try:
                        for del_id in selected_db_ids:
                            db.supabase.table("error_logs").delete().eq("id", del_id).execute()
                        st.cache_data.clear()
                        st.success(f"✅ Đã xóa thành công {len(selected_db_ids)} bản ghi lỗi đã chọn!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xóa bản ghi: {e}")
                else:
                    st.warning("⚠️ Vui lòng tích chọn ít nhất một dòng ở danh sách bên dưới để xóa!")

            if btn_del_all:
                if confirm_del_all:
                    page_ids = page_df["db_id"].tolist()
                    if page_ids:
                        try:
                            for del_id in page_ids:
                                db.supabase.table("error_logs").delete().eq("id", del_id).execute()
                            st.cache_data.clear()
                            st.success(f"✅ Đã xóa toàn bộ {len(page_ids)} bản ghi trong trang này!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa: {e}")
                else:
                    st.warning("⚠️ Vui lòng tích vào ô 'Xác nhận xóa tất cả bản ghi trong trang này'!")
        else:
            st.info("Không có bản ghi lỗi nào trong khoảng thời gian và bộ lọc đã chọn.")
    else:
        st.info("Chưa có bản ghi lỗi nào trong hệ thống.")
