# view/cham_cong.py
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
get_attendance_db = db_module.get_attendance_db
get_active_attendance_db = getattr(db_module, "get_active_attendance_db", None)
add_attendance_log_db = db_module.add_attendance_log_db
update_attendance_checkout_db = db_module.update_attendance_checkout_db

def render_cham_cong(current_menu_name, current_user_role):
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = str(now_vn.date())
    current_time_str = now_vn.strftime("%H:%M:%S")

    # --- Tiêu đề trang và nút làm mới ---
    col_att_h1, col_att_h2 = st.columns([4, 1])
    with col_att_h1:
        st.subheader(f"⏱️ {current_menu_name}")
    with col_att_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_att"):
            st.cache_data.clear()
            st.rerun()

    # Lấy lịch sử chấm công và danh sách các ca chưa kết thúc
    att_df = get_attendance_db()
    
    if get_active_attendance_db is not None:
        active_att_df = get_active_attendance_db()
    else:
        active_att_df = att_df[att_df["Giờ Ra Ca"] == "Chưa kết thúc"] if not att_df.empty else pd.DataFrame()

    # --- 1. KHỐI TRẠNG THÁI HOẠT ĐỘNG NHÂN SỰ ---
    st.markdown("### 🔴 Trạng Thái Nhân Sự Hiện Tại")
    staff_list = st.session_state.get("staff_list", ["Nguyễn Hữu Khang Tôn Đức", "Nguyễn Đức Anh Tiến", "Trần Gia Bảo", "Gold"])
    
    active_staff_now = []
    if not active_att_df.empty and "Nhân Sự" in active_att_df.columns:
        active_staff_now = active_att_df["Nhân Sự"].dropna().unique().tolist()

    for staff in staff_list:
        if staff in active_staff_now:
            st.markdown(f"🟢 **{staff}** - Đang hoạt động (Trong ca làm việc)")
        else:
            st.markdown(f"🔴 **{staff}** - Không hoạt động")

    st.markdown("---")

    # --- 2. KHỐI FORM CHẤM CÔNG VÀO CA / RA CA ---
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Ngày", value=today_str, disabled=True)
        with c2:
            staff_options = ["--- Vui lòng chọn nhân sự ---"] + staff_list
            selected_staff = st.selectbox("Nhân sự", staff_options)
        with c3:
            ghi_chu = st.text_input("Ghi chú ra ca (Nếu có)", value="")

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🟢 Check-in (Vào ca)", use_container_width=True):
                if selected_staff == "--- Vui lòng chọn nhân sự ---":
                    st.error("⚠️ Vui lòng chọn đúng tên nhân sự trước khi Check-in!")
                elif selected_staff in active_staff_now:
                    st.warning(f"⚠️ Nhân sự **{selected_staff}** đã Check-in trước đó và chưa kết thúc ca!")
                else:
                    add_attendance_log_db(today_str, selected_staff, current_time_str)
                    st.success(f"✅ Đã Check-in thành công cho **{selected_staff}** lúc {current_time_str}!")
                    st.cache_data.clear()
                    st.rerun()

        with btn_c2:
            if st.button("🔴 Check-out (Kết thúc)", use_container_width=True):
                if selected_staff == "--- Vui lòng chọn nhân sự ---":
                    st.error("⚠️ Vui lòng chọn đúng tên nhân sự trước khi Check-out!")
                elif selected_staff not in active_staff_now:
                    st.error(f"⚠️ Nhân sự **{selected_staff}** hiện chưa bấm Vào ca, không thể bấm Kết thúc!")
                else:
                    # Lấy bản ghi ca trực đang mở gần nhất của nhân sự
                    row_open = active_att_df[active_att_df["Nhân Sự"] == selected_staff].iloc[0]
                    db_id = row_open["db_id"]
                    gio_vao_str = str(row_open["Giờ Vào Ca"]).strip()
                    ngay_vao_str = str(row_open["Ngày"]).strip()
                    
                    # Tính toán số phút làm việc chính xác (tính cả trường hợp vào ca đêm qua ngày)
                    try:
                        # Kết hợp cả ngày và giờ để xử lý ca xuyên đêm
                        dt_vao = datetime.datetime.strptime(f"{ngay_vao_str} {gio_vao_str}", "%Y-%m-%d %H:%M:%S")
                        dt_ra = now_vn.replace(tzinfo=None)
                        so_phut = int((dt_ra - dt_vao).total_seconds() / 60)
                        if so_phut < 0:
                            so_phut = 0
                    except Exception:
                        # Fallback nếu format ngày/giờ có ký tự lạ
                        try:
                            t_vao = datetime.datetime.strptime(gio_vao_str, "%H:%M:%S")
                            t_ra = datetime.datetime.strptime(current_time_str, "%H:%M:%S")
                            so_phut = max(0, int((t_ra - t_vao).total_seconds() / 60))
                        except Exception:
                            so_phut = 0

                    update_attendance_checkout_db(db_id, current_time_str, so_phut, ghi_chu)
                    st.success(f"🛑 Đã Check-out thành công cho **{selected_staff}** lúc {current_time_str}! Tổng thời gian: **{so_phut} phút**.")
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("---")

    # --- 3. KHỐI BẢNG LỊCH SỬ CHẤM CÔNG ---
    st.markdown("### 📋 Lịch Sử Chấm Công")
    if not att_df.empty:
        st.dataframe(att_df, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu lịch sử chấm công nào được ghi nhận.")
