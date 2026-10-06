# view/nhap_san_luong.py
import streamlit as st
import pandas as pd
import datetime
import requests

from database import (
    get_production_logs_db, 
    add_production_log_db, 
    update_production_log_deleted_status,
    upload_multiple_images_to_storage, 
    get_attendance_db, 
    get_rules_db,
    update_production_log_record_db
)
import utils

VN_TIMEZONE = utils.VN_TIMEZONE

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_image_size(u):
    try:
        if u.startswith("http://") or u.startswith("https://"):
            res = requests.head(u, timeout=0.8)
            length = int(res.headers.get('Content-Length', 0))
            if length > 0:
                if length >= 1024 * 1024:
                    return f"~{length / (1024 * 1024):.1f} MB"
                return f"~{max(1, int(length / 1024))} KB"
    except Exception:
        pass
    return "~150 KB"

@st.fragment
def render_production_table_fragment(raw_input_df, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    
    col_title_1, col_title_2 = st.columns([3, 1])
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input_frag"):
            st.cache_data.clear()
            st.rerun()

    if raw_input_df.empty:
        st.info("Chưa có dữ liệu sản lượng.")
        return

    f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.1, 1.1, 1.4, 1.3, 1.3, 1.2])
    
    with f_col1:
        start_filter_date = st.date_input("Từ ngày", value=now_vn.date(), key="f_start_live")
    with f_col2:
        end_filter_date = st.date_input("Đến ngày", value=now_vn.date(), key="f_end_live")
    with f_col3:
        enable_hour_filter = st.checkbox("Lọc theo Giờ", value=False, key="f_hour_live")
        if enable_hour_filter:
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                start_t = st.time_input("Từ", value=datetime.time(7, 30), label_visibility="collapsed", key="f_start_t_live")
            with t_col2:
                end_t = st.time_input("Đến", value=datetime.time(17, 0), label_visibility="collapsed", key="f_end_t_live")
        else:
            start_t, end_t = None, None
            
    with f_col4:
        all_staff_opts = ["Tất cả"] + sorted(raw_input_df["Nhân Sự"].dropna().unique().tolist())
        filter_staff = st.selectbox("Lọc theo Nhân Sự", all_staff_opts, key="f_staff_live")

    df_pre_filter = raw_input_df.copy()
    df_pre_filter["Ngày_DT"] = pd.to_datetime(df_pre_filter["Ngày"], errors='coerce').dt.date
    df_pre_filter = df_pre_filter[(df_pre_filter["Ngày_DT"] >= start_filter_date) & (df_pre_filter["Ngày_DT"] <= end_filter_date)]
    
    if filter_staff != "Tất cả": 
        df_pre_filter = df_pre_filter[df_pre_filter["Nhân Sự"] == filter_staff]

    if enable_hour_filter and start_t and end_t:
        def check_time_pre(t_str):
            try:
                t_val = datetime.datetime.strptime(str(t_str).strip(), "%H:%M:%S").time()
                return start_t <= t_val <= end_t
            except:
                return True
        df_pre_filter = df_pre_filter[df_pre_filter["Thời Gian"].apply(check_time_pre)]

    dynamic_tasks = sorted(df_pre_filter["Hạng Mục Công Việc"].dropna().unique().tolist()) if not df_pre_filter.empty else []
    all_task_opts = ["Tất cả"] + dynamic_tasks

    if st.session_state.get("f_task_live") not in all_task_opts:
        st.session_state["f_task_live"] = "Tất cả"

    with f_col5:
        filter_task = st.selectbox("Lọc theo Hạng Mục", all_task_opts, key="f_task_live")

    filtered_df = df_pre_filter.copy()
    if filter_task != "Tất cả": 
        filtered_df = filtered_df[filtered_df["Hạng Mục Công Việc"] == filter_task]
        
    total_rows = len(filtered_df)
    st.markdown(f"<div style='background: rgba(254, 243, 199, 0.6); padding: 8px 12px; border-radius: 6px; border: 1px solid #f59e0b; margin-bottom: 15px; font-weight: bold; color: #b45309;'>📅 Khoảng ngày có: {total_rows} bản ghi</div>", unsafe_allow_html=True)

    rows_per_page = 10
    total_pages = max(1, (total_rows - 1) // rows_per_page + 1)

    with f_col6:
        current_page = st.number_input(f"Trang hiển thị ({total_pages} tr | {total_rows} bản ghi)", min_value=1, max_value=total_pages, value=1, step=1, key="pagination_page_num_frag")

    start_idx = (current_page - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]

    try:
        rules_df_curr = get_rules_db()
        raw_t_list = rules_df_curr["Hạng Mục Công Việc"].tolist() if not rules_df_curr.empty and "Hạng Mục Công Việc" in rules_df_curr.columns else []
        danh_sach_hang_muc_edit = [str(t).strip() for t in raw_t_list if pd.notna(t) and str(t).strip()]
    except:
        danh_sach_hang_muc_edit = [filter_task] if filter_task != "Tất cả" else []

    if not paginated_df.empty:
        can_delete_data = (current_user_role == "Admin" or user_perms.get("perm_input", False))
        selected_ids_to_delete = []

        if can_delete_data:
            with st.form("delete_production_form_frag"):
                st.markdown("<div style='background: rgba(255, 255, 255, 0.7); padding: 10px; border-radius: 8px; border: 1px solid #cbd5e1; margin-bottom: 15px;'>", unsafe_allow_html=True)
                col_btn_1, col_btn_2 = st.columns(2)
                with col_btn_1:
                    submitted_delete_selected = st.form_submit_button("🗑 Xóa các dòng đã chọn", use_container_width=True, type="primary")
                with col_btn_2:
                    confirm_delete_all = st.checkbox("Xác nhận xóa tất cả trang này", key="chk_confirm_delete_all_frag")
                    submitted_delete_all = st.form_submit_button("🗑️ Xóa tất cả trang này", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                for idx, row in paginated_df.iterrows():
                    display_stt = total_rows - (start_idx + paginated_df.index.get_loc(idx))
                    if st.checkbox(f"Chọn xóa bản ghi STT {display_stt} ({row['Nhân Sự']} - {row['Hạng Mục Công Việc']})", key=f"chk_f_{row['db_id']}"):
                        selected_ids_to_delete.append(row['db_id'])

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

            st.markdown("---")

        for idx, row in paginated_df.iterrows():
            display_stt = total_rows - (start_idx + paginated_df.index.get_loc(idx))
            record_id = row['db_id']
            
            row_c1, row_c2 = st.columns([4, 1])
            with row_c1:
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.85); padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 4px; font-size: 0.85rem;">
                    <b>STT: {display_stt}</b> &nbsp;|&nbsp; 📅 {row['Ngày']} ⏰ {row['Thời Gian']} &nbsp;|&nbsp; 👤 <b>{row['Nhân Sự']}</b><br>
                    📌 {row['Hạng Mục Công Việc']} &nbsp;|&nbsp; 📦 <b>{row['Số Lượng']} {row['Đơn Vị']}</b> (⭐ <b>{row['Tổng Điểm']}</b> điểm)<br>
                    💬 <i>{row['Ghi Chú'] if pd.notna(row['Ghi Chú']) and str(row['Ghi Chú']).strip() else 'Không có ghi chú'}</i>
                </div>
                """, unsafe_allow_html=True)
                
                edit_state_key = f"editing_{record_id}"
                if edit_state_key not in st.session_state:
                    st.session_state[edit_state_key] = False

                col_b1, col_b2 = st.columns([1, 4])
                with col_b1:
                    if st.button("✏️ Sửa", key=f"btn_toggle_{record_id}"):
                        st.session_state[edit_state_key] = not st.session_state[edit_state_key]
                        st.rerun()

                if st.session_state[edit_state_key]:
                    with st.container():
                        st.markdown(f"<div style='background: rgba(239, 246, 255, 0.9); padding: 10px; border-radius: 6px; border: 1px solid #3b82f6; margin-top: 5px;'>", unsafe_allow_html=True)
                        st.markdown(f"**Đang chỉnh sửa bản ghi STT {display_stt}:**")
                        
                        curr_task = row.get('Hạng Mục Công Việc', danh_sach_hang_muc_edit[0] if danh_sach_hang_muc_edit else "")
                        try:
                            t_idx = danh_sach_hang_muc_edit.index(curr_task)
                        except:
                            t_idx = 0
                            
                        new_task = st.selectbox("Hạng mục mới", danh_sach_hang_muc_edit if danh_sach_hang_muc_edit else [curr_task], index=t_idx, key=f"edit_t_{record_id}")
                        new_qty = st.number_input("Số lượng mới", min_value=0, value=int(row.get('Số Lượng', 0)), step=1, key=f"edit_q_{record_id}")
                        new_note = st.text_input("Ghi chú mới", value=str(row.get('Ghi Chú', '') if pd.notna(row.get('Ghi Chú')) else ''), key=f"edit_n_{record_id}")
                        
                        col_sub1, col_sub2 = st.columns(2)
                        with col_sub1:
                            if st.button("💾 Lưu thay đổi", key=f"save_edit_{record_id}", type="primary", use_container_width=True):
                                update_production_log_record_db(
                                    db_id=record_id,
                                    hang_muc=new_task,
                                    so_luong=new_qty,
                                    ghi_chu=new_note
                                )
                                st.session_state[edit_state_key] = False
                                st.cache_data.clear()
                                st.success("✅ Cập nhật thành công!")
                                st.rerun()
                        with col_sub2:
                            if st.button("❌ Đóng", key=f"cancel_edit_{record_id}", use_container_width=True):
                                st.session_state[edit_state_key] = False
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    
            with row_c2:
                img_url_val = row.get("Hình Ảnh", "")
                if img_url_val and isinstance(img_url_val, str) and img_url_val.strip():
                    urls = [u.strip() for u in img_url_val.split(",") if u.strip()]
                    if urls:
                        num_cols = min(len(urls), 4)
                        sub_cols = st.columns(num_cols, gap="small")
                        for i, u in enumerate(urls):
                            if i < len(sub_cols):
                                with sub_cols[i]:
                                    try:
                                        if u.startswith("http://") or u.startswith("https://"):
                                            with st.popover("🔍", help="Xem ảnh lớn"): 
                                                st.image(u, use_container_width=True)
                                            st.image(u, width=40)
                                        elif os.path.exists(u):
                                            with st.popover("🔍", help="Xem ảnh lớn"): 
                                                st.image(u, use_container_width=True)
                                            st.image(u, width=40)
                                        else:
                                            st.caption("⚠️ Không tìm thấy ảnh")
                                    except Exception:
                                        st.caption("❌ Lỗi hiển thị")

            st.markdown("---")
    else:
        st.info("Không tìm thấy bản ghi nào khớp bộ lọc.")

def render_nhap_san_luong(current_menu_name, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = str(now_vn.date())
    
    st.subheader(f"{current_menu_name} ({today_str})")

    is_admin = (current_user_role == "Admin" or user_perms.get("perm_input", False))
    
    att_df_check = get_attendance_db()
    active_staff = []
    if not att_df_check.empty and "Giờ Ra Ca" in att_df_check.columns:
        active_rows = att_df_check[att_df_check["Giờ Ra Ca"].astype(str).str.lower().str.contains("chưa kết thúc|nan|none|^$", na=True)]
        if not active_rows.empty and "Nhân Sự" in active_rows.columns:
            active_staff = active_rows["Nhân Sự"].dropna().unique().tolist()

    if not is_admin:
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem**.")
    elif not active_staff:
        st.warning(f"⚠️ Hiện tại chưa có nhân sự nào **Check-in (Vào ca)**!")
    else:
        try:
            rules_df = get_rules_db()
            st.session_state["rules_df"] = rules_df
        except Exception:
            rules_df = st.session_state.get("rules_df", pd.DataFrame())

        raw_tasks = rules_df["Hạng Mục Công Việc"].tolist() if not rules_df.empty and "Hạng Mục Công Việc" in rules_df.columns else []
        danh_sach_hang_muc = [str(t).strip() for t in raw_tasks if pd.notna(t) and str(t).strip() and str(t).strip().lower() not in ["nan", "none"]]
        if not danh_sach_hang_muc: 
            danh_sach_hang_muc = ["Chưa có dữ liệu định mức"]

        if "file_uploader_version" not in st.session_state:
            st.session_state.file_uploader_version = 0

        if st.session_state.get("should_reset_form", False):
            st.session_state.widget_staff_select = "--- Vui lòng chọn nhân sự ---"
            st.session_state.widget_task_select = danh_sach_hang_muc[0]
            st.session_state.file_uploader_version += 1
            st.session_state.should_reset_form = False

        if "widget_staff_select" not in st.session_state:
            st.session_state.widget_staff_select = "--- Vui lòng chọn nhân sự ---"

        if "widget_task_select" not in st.session_state or st.session_state.widget_task_select not in danh_sach_hang_muc:
            st.session_state.widget_task_select = danh_sach_hang_muc[0]

        with st.form("entry_form"):
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: 
                st.date_input("Ngày làm việc", now_vn.date(), disabled=True)
            with f_col2:
                staff_options = ["--- Vui lòng chọn nhân sự ---"] + active_staff
                nhan_su = st.selectbox("Nhân sự thực hiện", staff_options, key="widget_staff_select")
            with f_col3:
                hang_muc = st.selectbox("Hạng mục công việc", danh_sach_hang_muc, key="widget_task_select")
                
            uploader_key = f"record_img_{st.session_state.file_uploader_version}"
            record_images = st.file_uploader("Tải ảnh đính kèm (Tối đa 4 ảnh)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key=uploader_key)
                
            f_col4, f_col5 = st.columns(2)
            with f_col4: so_luong = st.number_input("Số lượng thực tế", min_value=0, value=0, step=1)
            with f_col5: ghi_chu = st.text_input("Ghi chú", "")
                
            submitted = st.form_submit_button("📊 Báo Cáo Sản Lượng", use_container_width=True)

            if submitted:
                if nhan_su == "--- Vui lòng chọn nhân sự ---":
                    st.warning("⚠️ Vui lòng chọn nhân sự thực hiện!")
                elif hang_muc == "Chưa có dữ liệu định mức":
                    st.warning("⚠️ Vui lòng chọn hạng mục công việc hợp lệ!")
                elif not record_images:
                    st.warning("⚠️ Vui lòng đính kèm ít nhất 1 hình ảnh minh chứng trước khi gửi báo cáo sản lượng!")
                else:
                    he_so = 1.0
                    don_vi = "Cái"
                    
                    if not rules_df.empty:
                        task_col = None
                        for col in ["Hạng Mục Công Việc", "hang_muc_cong_viec", "hang_muc"]:
                            if col in rules_df.columns:
                                task_col = col
                                break
                        
                        if task_col:
                            target_val = str(hang_muc).strip().lower()
                            matched = rules_df[rules_df[task_col].astype(str).str.strip().str.lower() == target_val]
                            if not matched.empty:
                                for hs_col in ["Hệ Số Điểm", "he_so_diem", "he_so", "diem"]:
                                    if hs_col in matched.columns:
                                        val_raw = matched[hs_col].values[0]
                                        if pd.notna(val_raw) and str(val_raw).strip() != "":
                                            try:
                                                cleaned_val = str(val_raw).replace(",", ".").strip()
                                                he_so = float(cleaned_val)
                                            except Exception:
                                                pass
                                            break
                                for dv_col in ["Đơn Vị", "don_vi", "unit"]:
                                    if dv_col in matched.columns:
                                        val_dv = matched[dv_col].values[0]
                                        if pd.notna(val_dv) and str(val_dv).strip() != "":
                                            don_vi = str(val_dv)
                                        break

                    tong_diem = float(so_luong) * float(he_so)
                    img_urls = upload_multiple_images_to_storage(record_images) if record_images else ""
                    current_time_str = datetime.datetime.now(VN_TIMEZONE).strftime("%H:%M:%S")
                    
                    add_production_log_db(today_str, current_time_str, nhan_su, hang_muc, img_urls, don_vi, so_luong, he_so, tong_diem, ghi_chu)
                    
                    st.session_state.should_reset_form = True
                    st.success(f"✅ Ghi nhận thành công cho **{nhan_su}**!")
                    st.rerun()

    st.markdown("---")

    raw_input_df = get_production_logs_db(is_deleted=False, limit_rows=2000)
    render_production_table_fragment(raw_input_df, current_user_role, user_perms)
