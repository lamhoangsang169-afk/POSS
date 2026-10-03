# view/nhap_san_luong.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd

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
db_module = load_module_from_path("database", db_path)

# Lấy các hàm từ database.py
get_production_logs_db = db_module.get_production_logs_db
get_production_logs_by_date_range = db_module.get_production_logs_by_date_range
get_rules_db = db_module.get_rules_db
update_production_log_deleted_status = db_module.update_production_log_deleted_status
update_production_log_record_db = getattr(db_module, "update_production_log_record_db", None)
supabase = db_module.supabase

def render_nhap_san_luong(current_menu_name, current_user_role, user_perms):
    st.subheader(f"📋 {current_menu_name}")
    st.markdown("---")

    # Bộ lọc ngày tháng & tìm kiếm dữ liệu lịch sử sản lượng
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        start_date = st.date_input("Từ ngày", value=pd.to_datetime("today").date() - pd.Timedelta(days=7))
    with col_f2:
        end_date = st.date_input("Đến ngày", value=pd.to_datetime("today").date())
    with col_f3:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_filter = st.button("🔍 Lọc dữ liệu", use_container_width=True)

    # Tải dữ liệu sản lượng
    if btn_filter:
        df_logs = get_production_logs_by_date_range(start_date, end_date)
    else:
        df_logs = get_production_logs_db(is_deleted=False, limit_rows=100)

    if df_logs.empty:
        st.info("📭 Không có dữ liệu sản lượng nào trong khoảng thời gian này.")
        return

    st.success(f"📅 Khoảng ngày có: {len(df_logs)} bản ghi")

    # Hiển thị danh sách bản ghi dưới dạng danh thiếp kèm nút sửa nhanh
    for idx, row in df_logs.iterrows():
        display_stt = row.get("STT", idx + 1)
        ngay_val = row.get("Ngày", "")
        gio_val = row.get("Thời Gian", "")
        nhan_su_val = row.get("Nhân Sự", "")
        hang_muc_val = row.get("Hạng Mục Công Việc", "")
        so_luong_val = row.get("Số Lượng", 0)
        tong_diem_val = row.get("Tổng Điểm", 0)
        ghi_chu_val = row.get("Ghi Chú", "Không có ghi chú")
        img_url = row.get("Hình Ảnh", "")

        with st.container():
            col_info, col_img = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"""
                    **STT: {display_stt}** | 📅 `{ngay_val}` ⏰ `{gio_val}` | 👤 **{nhan_su_val}**<br>
                    📌 {hang_muc_val} | 📦 **{so_luong_val}** (⭐ **{tong_diem_val}** điểm)<br>
                    💬 *{ghi_chu_val if pd.notna(ghi_chu_val) and str(ghi_chu_val).strip() != '' else 'Không có ghi chú'}*
                    """,
                    unsafe_allow_html=True
                )
            with col_img:
                if pd.notna(img_url) and str(img_url).strip():
                    first_img = str(img_url).split(",")[0].strip()
                    try:
                        st.image(first_img, width=80)
                    except:
                        st.write("Ảnh lỗi")
                else:
                    st.caption("Không ảnh")

            # === TÍCH HỢP NÚT SỬA NHANH TRỰC TIẾP CHO TỪNG BẢN GHI ===
            if current_user_role == "Admin" or user_perms.get("perm_edit", True):
                with st.expander(f"✏️ Sửa nhanh bản ghi STT {display_stt}"):
                    with st.form(key=f"edit_form_{row.get('db_id', idx)}"):
                        all_rules_df = get_rules_db()
                        task_list = all_rules_df["Hạng Mục Công Việc"].tolist() if not all_rules_df.empty and "Hạng Mục Công Việc" in all_rules_df.columns else [hang_muc_val]
                        
                        default_idx = task_list.index(hang_muc_val) if hang_muc_val in task_list else 0
                        
                        new_task = st.selectbox("Chọn lại hạng mục công việc", task_list, index=default_idx, key=f"edit_task_{row.get('db_id', idx)}")
                        new_qty = st.number_input("Số lượng thực tế mới", min_value=0.0, value=float(so_luong_val), step=1.0, key=f"edit_qty_{row.get('db_id', idx)}")
                        cur_note = ghi_chu_val if pd.notna(ghi_chu_val) else ""
                        new_note = st.text_input("Ghi chú mới", value=cur_note, key=f"edit_note_{row.get('db_id', idx)}")
                        
                        submitted_edit = st.form_submit_button("💾 Lưu Cập Nhật", use_container_width=True)
                        if submitted_edit:
                            if update_production_log_record_db is not None:
                                update_production_log_record_db(row.get('db_id'), new_task, new_qty, new_note)
                                st.success("✅ Cập nhật bản ghi thành công!")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("⚠️ Không tìm thấy hàm cập nhật trong `database.py`!")

        st.markdown("---")
