import streamlit as st
import datetime
from utils import VN_TIMEZONE, calculate_exact_minutes
from database import (
    supabase,
    get_attendance_db,
    add_attendance_db,
    delete_attendance_db
)

def render_cham_cong(current_menu_name, current_user_role):
    col_att_h1, col_att_h2 = st.columns([3, 1])
    with col_att_h1:
        st.header(current_menu_name)
    with col_att_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_att"):
            st.cache_data.clear()
            st.rerun()

    now_vn = datetime.datetime.now(VN_TIMEZONE)
    
    att_df = get_attendance_db()
    checked_in_set = set(att_df[att_df["Giờ Ra Ca"] == "Chưa kết thúc"]["Nhân Sự"].tolist()) if not att_df.empty else set()

    staff_lines = ""
    for s in st.session_state.staff_list:
        if s in checked_in_set: staff_lines += f"🟢 <b>{s}</b> - Đang Làm Việc<br>"
        else: staff_lines += f"🔴 <b>{s}</b> - Không hoạt động<br>"
    st.markdown(f"<div style='background: rgba(255,255,255,0.7); padding: 10px; border-radius: 6px; margin-bottom: 15px;'>{staff_lines}</div>", unsafe_allow_html=True)

    with st.form("attendance_form"):
        f1, f2, f3 = st.columns(3)
        with f1: att_date = st.date_input("Ngày", now_vn.date())
        with f2:
            att_staff_options = ["--- Vui lòng chọn nhân sự ---"] + st.session_state.staff_list
            att_staff = st.selectbox("Nhân sự", att_staff_options)
        with f3: att_note = st.text_input("Ghi chú ca", "")
        
        b1, b2 = st.columns(2)
        with b1: check_in = st.form_submit_button("🟢 Check-in (Vào ca)", use_container_width=True)
        with b2: check_out = st.form_submit_button("🔴 Check-out (Kết thúc)", use_container_width=True)
        
        time_str = now_vn.strftime("%H:%M:%S")
        if check_in:
            if att_staff == "--- Vui lòng chọn nhân sự ---":
                st.session_state["att_msg"] = ("warning", "⚠️ Vui lòng chọn đúng tên nhân sự!")
            elif att_staff in checked_in_set:
                st.session_state["att_msg"] = ("warning", f"⚠️ Nhân sự {att_staff} đang trong ca làm việc!")
            else:
                add_attendance_db(att_date, att_staff, time_str, "Chưa kết thúc", 0, att_note)
                st.session_state["att_msg"] = ("success", f"✅ Check-in thành công cho **{att_staff}** lúc **{time_str}**!")
                st.rerun()
        if check_out:
            if att_staff == "--- Vui lòng chọn nhân sự ---":
                st.session_state["att_msg"] = ("warning", "⚠️ Vui lòng chọn đúng tên nhân sự!")
            else:
                res_check = supabase.table("attendance").select("*").eq("nhan_su", att_staff).eq("gio_ra_ca", "Chưa kết thúc").execute() if supabase else None
                if res_check and res_check.data:
                    target_row = res_check.data[0]
                    row_id = target_row["id"]
                    ngay_vao = target_row["ngay"]
                    gio_vao_ca = target_row.get("gio_vao_ca", "00:00:00")
                    so_phut_thuc_te = calculate_exact_minutes(ngay_vao, gio_vao_ca, str(att_date), time_str)
                    old_note = target_row.get("ghi_chu", "")
                    final_note = f"{old_note} | {att_note}" if old_note and att_note else (old_note or att_note)
                    
                    supabase.table("attendance").update({
                        "gio_ra_ca": time_str, "so_phut_lam_viec": int(so_phut_thuc_te), "ghi_chu": final_note
                    }).eq("id", row_id).execute()
                    st.cache_data.clear()
                    st.session_state["att_msg"] = ("success", f"✅ Check-out thành công cho **{att_staff}** (Tổng: **{so_phut_thuc_te} phút**)!")
                else:
                    st.session_state["att_msg"] = ("warning", f"⚠️ Không tìm thấy mốc Vào ca nào đang mở cho **{att_staff}**!")
                st.rerun()

    if "att_msg" in st.session_state:
        m_type, m_text = st.session_state["att_msg"]
        if m_type == "success": st.success(m_text)
        else: st.warning(m_text)
        del st.session_state["att_msg"]

    st.markdown("---")
    st.subheader("📋 Lịch Sử Chấm Công")
    if not att_df.empty:
        st.dataframe(att_df.drop(columns=["db_id"]), use_container_width=True, hide_index=True)
        if current_user_role == "Admin":
            with st.form("delete_att_form"):
                st.markdown("##### 🗑️ Xóa Bản Ghi Chấm Công Lỗi")
                confirm_del_all_att = st.checkbox("⚠️ Tôi chắc chắn muốn xóa TOÀN BỘ lịch sử chấm công", key="chk_confirm_del_all_att")
                
                att_col1, att_col2 = st.columns(2)
                with att_col1: submitted_delete_selected = st.form_submit_button("Xóa Các Dòng Đã Chọn", use_container_width=True)
                with att_col2: submitted_delete_all = st.form_submit_button("🔥 Xóa Toàn Bộ Lịch Sử Chấm Công", use_container_width=True, type="primary")

                att_ids_to_del = []
                for idx, r in att_df.iterrows():
                    if st.checkbox(f"Xóa dòng STT {r['STT']} - {r['Nhân Sự']} ({r['Ngày']} | {r['Giờ Vào Ca']} -> {r['Giờ Ra Ca']})", key=f"del_att_{r['db_id']}"):
                        att_ids_to_del.append(r['db_id'])

                if submitted_delete_selected:
                    if att_ids_to_del:
                        delete_attendance_db(att_ids_to_del)
                        st.success("Đã xóa các bản ghi chấm công đã chọn thành công!")
                        st.rerun()
                    else:
                        st.warning("Vui lòng tích chọn ít nhất một dòng cần xóa!")

                if submitted_delete_all:
                    if confirm_del_all_att:
                        all_att_ids = att_df["db_id"].tolist()
                        if all_att_ids:
                            delete_attendance_db(all_att_ids)
                            st.success("Đã xóa toàn bộ lịch sử chấm công thành công!")
                            st.rerun()
                    else:
                        st.warning("⚠️ Vui lòng tích chọn hộp xác nhận an toàn trước khi bấm Xóa Toàn Bộ!")
