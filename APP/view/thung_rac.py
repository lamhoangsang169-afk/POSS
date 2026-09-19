import streamlit as st
from database import (
    get_production_logs_db,
    update_production_log_deleted_status,
    permanent_delete_db
)

def render_thung_rac(current_menu_name, current_user_role):
    col_trash_h1, col_trash_h2 = st.columns([3, 1])
    with col_trash_h1:
        st.header(current_menu_name)
    with col_trash_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_trash"):
            st.cache_data.clear()
            st.rerun()

    if current_user_role != "Admin":
        st.warning("🔒 Tính năng thùng rác và xóa vĩnh viễn chỉ dành cho Quản trị viên (Admin).")
    else:
        trash_df = get_production_logs_db(is_deleted=True, limit_rows=100)
        
        st.subheader("🗑️ Thùng Rác: Bản Ghi Sản Lượng")
        if not trash_df.empty:
            with st.form("trash_form"):
                for idx, row in trash_df.iterrows():
                    st.markdown(f'<div style="background: rgba(255,255,255,0.85); padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 4px; font-size: 0.85rem;"><b>STT: {row['STT']}</b> | 📅 {row['Ngày']} | 👤 <b>{row['Nhân Sự']}</b> | 📌 {row['Hạng Mục Công Việc']} ({row['Số Lượng']} {row['Đơn Vị']})</div>', unsafe_allow_html=True)
                    trash_df.loc[idx, "Chọn"] = st.checkbox(f"Chọn sản lượng STT {row['STT']}", key=f"t_{row['db_id']}")
                    
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("📥 Khôi Phục Đã Chọn", use_container_width=True):
                        ids = trash_df[trash_df["Chọn"] == True]["db_id"].tolist()
                        if ids:
                            update_production_log_deleted_status(ids, False)
                            st.success("Đã khôi phục thành công!")
                            st.rerun()
                with c2:
                    if st.form_submit_button("🔥 Xóa Vĩnh Viễn Đã Chọn", use_container_width=True):
                        ids = trash_df[trash_df["Chọn"] == True]["db_id"].tolist()
                        if ids:
                            permanent_delete_db(ids)
                            st.success("Đã xóa vĩnh viễn!")
                            st.rerun()
        else:
            st.info("Thùng rác sản lượng trống.")
