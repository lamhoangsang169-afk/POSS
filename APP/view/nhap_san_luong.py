# view/nhap_san_luong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime

# ==================== NẠP MODULE ĐỘNG THEO ĐƯỜNG DẪN TUYỆT ĐỐI ====================
current_file_dir = os.path.dirname(os.path.abspath(__file__))
root_project_dir = os.path.dirname(os.path.dirname(current_file_dir))

def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

db_path = os.path.join(root_project_dir, "database.py")
utils_path = os.path.join(root_project_dir, "utils.py")

db_module = load_module_from_path("database", db_path)
utils_module = load_module_from_path("utils", utils_path)

VN_TIMEZONE = utils_module.VN_TIMEZONE
get_production_logs_db = db_module.get_production_logs_db
add_production_log_db = db_module.add_production_log_db
update_production_log_deleted_status = db_module.update_production_log_deleted_status
upload_multiple_images_to_storage = db_module.upload_multiple_images_to_storage
get_attendance_db = db_module.get_attendance_db
get_rules_db = db_module.get_rules_db

def render_nhap_san_luong(current_menu_name, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = str(now_vn.date())
    
    st.subheader(f"{current_menu_name} ({today_str})")

    # ==================== PHẦN 1: FORM NHẬP SẢN LƯỢNG PHÍA TRÊN ====================
    is_admin = (current_user_role == "Admin" or user_perms.get("perm_input", False))
    
    att_df_check = get_attendance_db()
    active_staff = []
    if not att_df_check.empty and "Giờ Ra Ca" in att_df_check.columns:
        active_rows = att_df_check[att_df_check["Giờ Ra Ca"].astype(str).str.lower().str.contains("chưa kết thúc|nan|none|^$", na=True)]
        if not active_rows.empty and "Nhân Sự" in active_rows.columns:
            active_staff = active_rows["Nhân Sự"].dropna().unique().tolist()

    if not is_admin:
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem**. Bạn có thể theo dõi bảng danh sách bên dưới nhưng không được phép thêm hoặc chỉnh sửa dữ liệu.")
    elif not active_staff:
        st.warning(f"⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)**. Vui lòng thực hiện Check-in trước khi nhập sản lượng!")
    else:
        req_img = st.session_state.get("require_image", True)
        req_qty = st.session_state.get("require_quantity", True)
        
        with st.form("entry_form"):
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: st.date_input("Ngày làm việc", now_vn.date(), disabled=True)
            with f_col2:
                staff_options = ["--- Vui lòng chọn nhân sự ---"] + active_staff
                nhan_su = st.selectbox("Nhân sự thực hiện", staff_options)
            with f_col3:
                rules_df = st.session_state.get("rules_df", pd.DataFrame())
                if rules_df.empty:
                    try:
                        rules_df = get_rules_db()
                        st.session_state["rules_df"] = rules_df
                    except Exception:
                        pass

                raw_tasks = rules_df["Hạng Mục Công Việc"].tolist() if not rules_df.empty and "Hạng Mục Công Việc" in rules_df.columns else []
                danh_sach_hang_muc = [str(t).strip() for t in raw_tasks if pd.notna(t) and str(t).strip() and str(t).strip().lower() not in ["nan", "none"]]
                if not danh_sach_hang_muc: 
                    danh_sach_hang_muc = ["Chưa có dữ liệu định mức"]
                hang_muc = st.selectbox("Hạng mục công việc", danh_sach_hang_muc)
                
            record_images = st.file_uploader("Tải ảnh đính kèm (Tối đa 4 ảnh)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="record_img")
                    
            f_col4, f_col5 = st.columns(2)
            with f_col4: so_luong = st.number_input("Số lượng thực tế", min_value=0, value=0, step=1)
            with f_col5: ghi_chu = st.text_input("Ghi chú", "")
                
            submitted = st.form_submit_button("📊 Báo Cáo Sản Lượng", use_container_width=True)

            if submitted and nhan_su != "--- Vui lòng chọn nhân sự ---" and hang_muc != "Chưa có dữ liệu định mức":
                row_rule = rules_df[rules_df["Hạng Mục Công Việc"] == hang_muc] if not rules_df.empty else pd.DataFrame()
                he_so = float(row_rule["Hệ Số Điểm"].values[0]) if not row_rule.empty and "Hệ Số Điểm" in row_rule.columns else 1.0
                don_vi = str(row_rule["Đơn Vị"].values[0]) if not row_rule.empty and "Đơn Vị" in row_rule.columns else "Cái"
                tong_diem = so_luong * he_so
                
                img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                
                add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**!")
                st.cache_data.clear()
                st.rerun()

    st.markdown("---")

    # ==================== PHẦN 2: DANH SÁCH SẢN LƯỢNG & HÌNH ẢNH ====================
    col_title_1, col_title_2 = st.columns([3, 1])
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input"):
            st.cache_data.clear()
            st.rerun()

    raw_input_df = get_production_logs_db(is_deleted=False, limit_rows=1000)

    if not raw_input_df.empty:
        f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.2, 1.2, 1.0, 1.1, 1.1, 1.0])
        
        with f_col1:
            # === ĐẶT MẶC ĐỊNH LÀ NGÀY THỰC TẾ (HÔM NAY) HOẶC LẤY TRƯỚC ĐÓ 30 NGÀY TÙY Ý ===
            default_start = now_vn.date()
            start_filter_date = st.date_input("Từ ngày", default_start, key="f_start_date")
        with f_col2:
            end_filter_date = st.date_input("Đến ngày", now_vn.date(), key="f_end_date")
        with f_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            enable_hour_filter = st.checkbox("Lọc theo Giờ", value=False, key="f_by_time")
            if enable_hour_filter:
                t_sub1, t_sub2 = st.columns(2)
                with t_sub1: start_t = st.time_input("Từ", datetime.time(7, 30), label_visibility="collapsed", key="f_start_t")
                with t_sub2: end_t = st.time_input("Đến", datetime.time(17, 0), label_visibility="collapsed", key="f_end_t")
            else:
                start_t, end_t = None, None
                
        all_staff = ["Tất cả"] + sorted(raw_input_df["Nhân Sự"].dropna().unique().tolist())
        with f_col4:
            filter_staff = st.selectbox("Lọc theo Nhân Sự", all_staff, key="f_staff")
            
        temp_filtered_df = raw_input_df.copy()
        temp_filtered_df["Ngày_DT"] = pd.to_datetime(temp_filtered_df["Ngày"], errors='coerce').dt.date
        temp_filtered_df = temp_filtered_df[(temp_filtered_df["Ngày_DT"] >= start_filter_date) & (temp_filtered_df["Ngày_DT"] <= end_filter_date)]
        
        if filter_staff != "Tất cả": 
            temp_filtered_df = temp_filtered_df[temp_filtered_df["Nhân Sự"] == filter_staff]

        if enable_hour_filter and start_t and end_t:
            def check_time_in_range(t_str):
                try:
                    t_val = datetime.datetime.strptime(str(t_str).strip(), "%H:%M:%S").time()
                    return start_t <= t_val <= end_t
                except:
                    return True
            temp_filtered_df = temp_filtered_df[temp_filtered_df["Thời Gian"].apply(check_time_in_range)]

        available_tasks = ["Tất cả"] + sorted(temp_filtered_df["Hạng Mục Công Việc"].dropna().unique().tolist()) if not temp_filtered_df.empty else ["Tất cả"]
        with f_col5:
            filter_task = st.selectbox("Lọc theo Hạng Mục", available_tasks, key="f_task")
        
        filtered_df = temp_filtered_df.copy()
        if filter_task != "Tất cả": 
            filtered_df = filtered_df[filtered_df["Hạng Mục Công Việc"] == filter_task]
            
        total_rows = len(filtered_df)
        st.markdown(f"<div style='background: rgba(254, 243, 199, 0.6); padding: 8px 12px; border-radius: 6px; border: 1px solid #f59e0b; margin-bottom: 15px; font-weight: bold; color: #b45309;'>📅 Khoảng ngày có: {total_rows} bản ghi</div>", unsafe_allow_html=True)

        rows_per_page = 10
        total_pages = (total_rows - 1) // rows_per_page + 1 if total_rows > 0 else 1

        with f_col6:
            current_page = st.number_input(f"Trang hiển thị ({total_pages} tr)", min_value=1, max_value=max(total_pages, 1), value=1, step=1, key="pagination_page_num")

        start_idx = (current_page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        paginated_df = filtered_df.iloc[start_idx:end_idx]

        if filter_task != "Tất cả":
            total_qty_task = filtered_df["Số Lượng"].sum() if not filtered_df.empty else 0
            unit_name = filtered_df["Đơn Vị"].values[0] if not filtered_df.empty and "Đơn Vị" in filtered_df.columns else "Cái"
            st.markdown(f'<div style="background: rgba(59, 130, 246, 0.15); padding: 12px 18px; border-radius: 8px; border: 2px solid #3b82f6; margin-bottom: 15px; font-size: 1rem; font-weight: bold; text-align: center;">📊 Tổng số lượng của hạng mục <span style="color: #ff4b4b;">"{filter_task}"</span>: <span style="font-size: 1.2rem; color: #1d4ed8;">{total_qty_task:,.0f}</span> {unit_name}</div>', unsafe_allow_html=True)

        if not paginated_df.empty:
            can_delete_data = (current_user_role == "Admin" or user_perms.get("perm_input", False))

            if can_delete_data:
                with st.form("delete_production_form"):
                    st.markdown("<div style='background: rgba(255, 255, 255, 0.7); padding: 10px; border-radius: 8px; border: 1px solid #cbd5e1; margin-bottom: 15px;'>", unsafe_allow_html=True)
                    col_btn_1, col_btn_2 = st.columns(2)
                    with col_btn_1:
                        submitted_delete_selected = st.form_submit_button("🗑️ Xóa các dòng đã chọn", use_container_width=True, type="primary")
                    with col_btn_2:
                        confirm_delete_all = st.checkbox("Xác nhận xóa tất cả trang này", key="chk_confirm_delete_all")
                        submitted_delete_all = st.form_submit_button("🗑️ Xóa tất cả trang này", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    selected_ids_to_delete = []
                    for idx, row in paginated_df.iterrows():
                        display_stt = total_rows - (start_idx + paginated_df.index.get_loc(idx))
                        
                        row_c1, row_c2 = st.columns([4, 1])
                        with row_c1:
                            st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.85); padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 4px; font-size: 0.85rem;">
                                <b>STT: {display_stt}</b> &nbsp;|&nbsp; 📅 {row['Ngày']} ⏰ {row['Thời Gian']} &nbsp;|&nbsp; 👤 <b>{row['Nhân Sự']}</b><br>
                                📌 {row['Hạng Mục Công Việc']} &nbsp;|&nbsp; 📦 <b>{row['Số Lượng']} {row['Đơn Vị']}</b> (⭐ <b>{row['Tổng Điểm']}</b> điểm)<br>
                                💬 <i>{row['Ghi Chú'] if pd.notna(row['Ghi Chú']) and str(row['Ghi Chú']).strip() else 'Không có ghi chú'}</i>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.checkbox(f"Chọn xóa bản ghi STT {display_stt}", key=f"chk_{row['db_id']}"):
                                selected_ids_to_delete.append(row['db_id'])
                                
                        with row_c2:
                            img_url_val = row.get("Hình Ảnh", "")
                            if img_url_val and isinstance(img_url_val, str) and img_url_val.strip():
                                urls = [u.strip() for u in img_url_val.split(",") if u.strip()]
                                if urls:
                                    sub_cols = st.columns(min(len(urls), 4), gap="small")
                                    for i, u in enumerate(urls):
                                        with sub_cols[i]:
                                            with st.popover("🔍", help="Xem ảnh lớn"): 
                                                st.image(u, use_container_width=True)
                                            st.image(u, width=40)
                            else:
                                st.markdown("<small style='color: gray;'>Không ảnh</small>", unsafe_allow_html=True)

                        st.markdown("---")

                    if submitted_delete_selected:
                        if selected_ids_to_delete:
                            update_production_log_deleted_status(selected_ids_to_delete, True)
                            st.success("Đã chuyển các dòng đã chọn vào thùng rác thành công!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Vui lòng tích chọn ít nhất một dòng cần xóa!")

                    if submitted_delete_all:
                        if confirm_delete_all:
                            all_paginated_ids = paginated_df["db_id"].tolist()
                            if all_paginated_ids:
                                update_production_log_deleted_status(all_paginated_ids, True)
                                st.success("Đã chuyển toàn bộ bản ghi đang hiển thị ở trang này vào thùng rác!")
                                st.rerun()
                        else:
                            st.warning("⚠️ Vui lòng tích chọn xác nhận trước khi bấm xóa tất cả!")
            else:
                for idx, row in paginated_df.iterrows():
                    display_stt = total_rows - (start_idx + paginated_df.index.get_loc(idx))
                    
                    row_c1, row_c2 = st.columns([4, 1])
                    with row_c1:
                        st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.85); padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 4px; font-size: 0.85rem;">
                            <b>STT: {display_stt}</b> &nbsp;|&nbsp; 📅 {row['Ngày']} ⏰ {row['Thời Gian']} &nbsp;|&nbsp; 👤 <b>{row['Nhân Sự']}</b><br>
                            📌 {row['Hạng Mục Công Việc']} &nbsp;|&nbsp; 📦 <b>{row['Số Lượng']} {row['Đơn Vị']}</b> (⭐ <b>{row['Tổng Điểm']}</b> điểm)<br>
                            💬 <i>{row['Ghi Chú'] if pd.notna(row['Ghi Chú']) and str(row['Ghi Chú']).strip() else 'Không có ghi chú'}</i>
                        </div>
                        """, unsafe_allow_html=True)
                    with row_c2:
                        img_url_val = row.get("Hình Ảnh", "")
                        if img_url_val and isinstance(img_url_val, str) and img_url_val.strip():
                            urls = [u.strip() for u in img_url_val.split(",") if u.strip()]
                            if urls:
                                sub_cols = st.columns(min(len(urls), 4), gap="small")
                                for i, u in enumerate(urls):
                                   with sub_cols[i]:
                                       try:
            with st.popover("🔍", help="Xem ảnh lớn"): 
                st.image(u, use_container_width=True)
            st.image(u, width=40)
        except Exception:
            st.markdown("<small style='color: red;'>Lỗi tải ảnh</small>", unsafe_allow_html=True)
                        else:
                            st.markdown("<small style='color: gray;'>Không ảnh</small>", unsafe_allow_html=True)
                    st.markdown("---")
        else:
            st.info("Không tìm thấy bản ghi nào khớp bộ lọc.")
    else:
        st.info("Chưa có dữ liệu sản lượng.")
