import streamlit as st
from database import supabase, save_rules_df_db

def render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms):
    col_rules_h1, col_rules_h2 = st.columns([3, 1])
    with col_rules_h1:
        st.header(current_menu_name)
    with col_rules_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_rules"):
            st.cache_data.clear()
            st.rerun()

    if current_user_role != "Admin" and not user_perms["perm_rules"]:
        st.warning("🔒 Bạn không có quyền truy cập hoặc chỉnh sửa định mức công việc!")
        st.dataframe(st.session_state.rules_df, use_container_width=True, hide_index=True)
    else:
        with st.form("rules_form"):
            edited_rules = st.data_editor(st.session_state.rules_df, num_rows="dynamic", use_container_width=True, hide_index=True, disabled=["stt"])
            
            st.markdown("---")
            st.markdown("##### ⚙️ Thao Tác Nâng Cao (Admin)")
            confirm_clear_all_rules = st.checkbox("⚠️ Tôi chắc chắn muốn xóa toàn bộ danh mục công việc trong hệ thống", key="chk_clear_rules")
            
            col_save_rule, col_clear_rule = st.columns(2)
            with col_save_rule:
                saved_clicked = st.form_submit_button("💾 Lưu Thay Đổi Định Mức", use_container_width=True)
            with col_clear_rule:
                clear_clicked = st.form_submit_button("🔥 Xóa Toàn Bộ Định Mức", use_container_width=True)

            if saved_clicked:
                save_rules_df_db(edited_rules)
                st.rerun()

            if clear_clicked:
                if confirm_clear_all_rules:
                    if supabase is not None:
                        try:
                            supabase.table("rules").delete().neq("id", 0).execute()
                            st.cache_data.clear()
                            st.success("Đã xóa toàn bộ danh mục định mức công việc thành công!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa toàn bộ định mức: {e}")
                else:
                    st.warning("⚠️ Vui lòng tích chọn hộp xác nhận phía trên trước khi bấm Xóa Toàn Bộ!")
