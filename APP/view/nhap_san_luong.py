# view/nhap_san_luong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime
import requests

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
update_production_log_record_db = getattr(db_module, "update_production_log_record_db", None)


# ==================== HÀM PHỤ TRỢ: LẤY DUNG LƯỢNG ẢNH AN TOÀN ====================
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
        elif os.path.exists(u):
            length = os.path.getsize(u)
            if length >= 1024 * 1024:
                return f"~{length / (1024 * 1024):.1f} MB"
            return f"~{max(1, int(length / 1024))} KB"
    except Exception:
        pass
    return "~150 KB"


# ==================== FRAGMENT LỌC TỨC THÌ & TỐI ƯU GIAO DIỆN GIỜ ====================
@st.fragment
def render_production_table_fragment(raw_input_df, current_user_role, user_perms):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_date = now_vn.date()
    
    # === TỰ ĐỘNG CẬP NHẬT NGÀY VỀ HÔM NAY NẾU LÀ NGÀY MỚI HOẶC BẤM LÀM MỚI ===
    if "last_checked_date" not in st.session_state or st.session_state.last_checked_date != today_date:
        st.session_state.last_checked_date = today_date
        st.session_state.f_start_live = today_date
        st.session_state.f_end_live = today_date
    
    col_title_1, col_title_2 = st.columns([3, 1])
    with col_title_1:
        st.markdown("<h3 style='color: #1e3a8a;'>Danh Sách Sản Lượng & Hình Ảnh</h3>", unsafe_allow_html=True)
    with col_title_2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_input_frag"):
            st.session_state.f_start_live = today_date
            st.session_state.f_end_live = today_date
            st.cache_data.clear()
            st.rerun()

    if raw_input_df.empty:
        st.info("Chưa có dữ liệu sản lượng.")
        return

    # SẮP XẾP 6 CỘT BỐ CỤC BỘ LỌC
    f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.1, 1.1, 1.4, 1.3, 1.3, 1.2])
    
    with f_col1:
        start_filter_date = st.date_input("Từ ngày", value=st.session_state.get("f_start_live", today_date), key="f_start_live")
    with f_col2:
        end_filter_date = st.date_input("Đến ngày", value=st.session_state.get("f_end_live", today_date), key="f_end_live")
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

    # --- LẤY DANH SÁCH HẠNG MỤC ĐỊNH MỨC CHO FORM SỬA ---
    try:
        rules_df = get_rules_db()
    except Exception:
        rules_df = pd.DataFrame()
    raw_tasks = rules_df["Hạng Mục Công Việc"].tolist() if not rules_df.empty and "Hạng Mục Công Việc" in rules_df.columns else []
    danh_sach_hang_muc = [str(t).strip() for t in raw_tasks if pd.notna(t) and str(t).strip() and str(t).strip().lower() not in ["nan", "none"]]
    if not danh_sach_hang_muc: 
        danh_sach_hang_muc = ["Chưa có dữ liệu định mức"]

    # --- BƯỚC 1: LỌC TRƯỚC DỮ LIỆU ĐỂ ĐỒNG BỘ DANH MỤC HẠNG MỤC THEO NHÂN SỰ ---
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

    # --- BƯỚC 2: LỌC HOÀN CHỈNH ĐỂ HIỂN THỊ BẢNG ---
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

    if filter_task != "Tất cả":
        total_qty_task = filtered_df["Số Lượng"].sum() if not filtered_df.empty else 0
        unit_name = filtered_df["Đơn Vị"].values[0] if not filtered_df.empty and "Đơn Vị" in filtered_df.columns else "Cái"
        st.markdown(f'<div style="background: rgba(59, 130, 246, 0.15); padding: 12px 18px; border-radius: 8px; border: 2px solid #3b82f6; margin-bottom: 15px; font-size: 1rem; font-weight: bold; text-align: center;">📊 Tổng số lượng của hạng mục <span style="color: #ff4b4b;">"{filter_task}"</span>: <span style="font-size: 1.2rem; color: #1d4ed8;">{total_qty_task:,.0f}</span> {unit_name}</div>', unsafe_allow_html=True)

    if not paginated_df.empty:
        can_delete_data = (current_user_role == "Admin" or user_perms.get("perm_input", False))

        if can_delete_data:
            with st.container(border=True):
                col_btn_1, col_btn_2 = st.columns(2)
                with col_btn_1:
                    clicked_delete_selected = st.button("🗑️ Xóa các dòng đã chọn", use_container_width=True, type="primary", key="btn_del_selected_action")
                with col_btn_2:
                    confirm_delete_all = st.checkbox("Xác nhận xóa tất cả trang này", key="chk_confirm_delete_all_frag")
                    clicked_delete_all = st.button("🗑️ Xóa tất cả trang này", use_container_width=True, key="btn_del_all_action")

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
                    
                    sub_c1, sub_c2 = st.columns([1.2, 1])
                    with sub_c1:
                        if st.checkbox(f"Chọn xóa STT {display_stt}", key=f"chk_f_{row['db_id']}"):
                            selected_ids_to_delete.append(row['db_id'])
                    with sub_c2:
                        with st.popover(f"✏️ Sửa bản ghi STT {display_stt}", use_container_width=True):
                            st.markdown(f"##### ✏️ Chỉnh Sửa Bản Ghi STT {display_stt}")
                            curr_task = row.get('Hạng Mục Công Việc', danh_sach_hang_muc[0])
                            task_idx = danh_sach_hang_muc.index(curr_task) if curr_task in danh_sach_hang_muc else 0
                            
                            edit_task = st.selectbox("Hạng mục công việc", danh_sach_hang_muc, index=task_idx, key=f"edit_task_{row['db_id']}")
                            edit_qty = st.number_input("Số lượng", min_value=0, value=int(row['Số Lượng']) if pd.notna(row['Số Lượng']) else 0, step=1, key=f"edit_qty_{row['db_id']}")
                            edit_note = st.text_input("Ghi chú", value=str(row['Ghi Chú']) if pd.notna(row['Ghi Chú']) and str(row['Ghi Chú']).lower() != 'nan' else "", key=f"edit_note_{row['db_id']}")
                            
                            if st.button("💾 Lưu Cập Nhật", key=f"btn_save_edit_{row['db_id']}", use_container_width=True):
                                if update_production_log_record_db is not None:
                                    update_production_log_record_db(row['db_id'], edit_task, edit_qty, edit_note)
                                    st.cache_data.clear()
                                    st.success("✅ Cập nhật bản ghi thành công!")
                                    st.rerun()
                                else:
                                    st.error("❌ Không tìm thấy hàm cập nhật database.")
                        
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
                                            
                                            size_str = get_cached_image_size(u)
                                            st.markdown(f"<div style='text-align: center; font-size: 0.72rem; color: #64748b; margin-top: -4px;'>{size_str}</div>", unsafe_allow_html=True)
                                        except Exception:
                                            st.caption("❌ Lỗi hiển thị")
                    else:
                        st.markdown("<small style='color: gray;'>Không ảnh</small>", unsafe_allow_html=True)

                st.markdown("---")

            if clicked_delete_selected:
                if selected_ids_to_delete:
                    update_production_log_deleted_status(selected_ids_to_delete, True)
                    st.success("Đã chuyển các dòng đã chọn vào thùng rác thành công!")
                    st.rerun()
                else:
                    st.warning("⚠️ Vui lòng tích chọn ít nhất một dòng cần xóa!")

            if clicked_delete_all:
                if confirm_delete_all:
                    all_paginated_ids = paginated_df["db_id"].tolist()
                    if all_paginated_ids:
                        update_
