# ==================== ĐIỀU HƯỚNG NỘI DUNG CHÍNH (MAIN CONTENT) ====================
@st.fragment
def render_main_content(current_menu_name):
    menu_lower = current_menu_name.lower()
    
    if "nhập sản lượng" in menu_lower:
        nhap_san_luong.render_nhap_san_luong(current_menu_name, current_user_role, user_perms)
    elif "chấm công" in menu_lower:
        cham_cong.render_cham_cong(current_menu_name, current_user_role)
    elif "báo cáo" in menu_lower or "thống kê" in menu_lower:
        bao_cao.render_bao_cao(current_menu_name)
    elif "thư mục báo cáo" in menu_lower:
        thu_muc_bao_cao.render_thu_muc_bao_cao(current_menu_name)
    elif "định mức" in menu_lower or "tham chiếu" in menu_lower:
        dinh_muc_cong_viec.render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms)
    elif "quản lý lỗi" in menu_lower:
        quan_ly_loi.render_quan_ly_loi(current_menu_name)
    elif "thùng rác" in menu_lower:
        thung_rac.render_thung_rac(current_menu_name, current_user_role)
        
    # ==================== QUẢN LÝ THƯ MỤC & MENU ====================
    elif current_menu_name == "📁 Quản Lý Thư Mục & Menu":
        col_mf_h1, col_mf_h2 = st.columns([3, 1])
        with col_mf_h1:
            st.header("Quản Lý Thư Mục & Menu")
        with col_mf_h2:
            if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_mf"):
                st.cache_data.clear()
                st.rerun()

        if current_user_role != "Admin":
            st.warning("🔒 Bạn không có quyền truy cập trang quản lý cấu hình hệ thống này.")
        else:
            with st.form("manage_menu_form"):
                current_folder_name = st.session_state.folders[0]["folder_name"] if st.session_state.folders else "📌 Quản Lý Nghiệp Vụ"
                new_folder_name = st.text_input("Tên thư mục", value=current_folder_name)
                
                current_items = st.session_state.folders[0]["items"] if st.session_state.folders else []
                
                total_items_count = max(len(current_items), 6)
                updated_items = []
                for i_idx in range(total_items_count):
                    default_name = current_items[i_idx]["name"] if i_idx < len(current_items) else f"{i_idx+1}. Mục mới"
                    default_id = current_items[i_idx]["id"] if i_idx < len(current_items) else f"menu_{i_idx+1}"
                    
                    new_name = st.text_input(f"Tên hiển thị {i_idx+1}", value=default_name)
                    if new_name.strip():
                        updated_items.append({"id": default_id, "name": new_name.strip()})
                    
                submitted_mf = st.form_submit_button("💾 Lưu Thay Đổi", use_container_width=True)
                if submitted_mf:
                    new_folders_structure = [{"folder_name": new_folder_name, "items": updated_items}]
                    st.session_state.folders = new_folders_structure
                    save_folders_db(new_folders_structure)
                    st.success("✅ Đã lưu cấu hình thư mục & menu thành công!")
                    st.rerun()

    # ==================== CÀI ĐẶT GIAO DIỆN ====================
    elif current_menu_name == "🎨 Cài Đặt Giao Diện":
        col_ui_h1, col_ui_h2 = st.columns([3, 1])
        with col_ui_h1:
            st.header("Cài Đặt Giao Diện & Nhân Sự")
        with col_ui_h2:
            if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_ui"):
                st.cache_data.clear()
                st.rerun()

        if current_user_role != "Admin":
            st.warning("🔒 Chỉ Quản trị viên mới được phép cài đặt giao diện và danh sách nhân sự!")
        else:
            st.markdown("### 🎨 Tùy Chỉnh Giao Diện Trực Tiếp")
            
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                picker_bg = st.color_picker("Màu nền ứng dụng", value=st.session_state.get("bg_color", "#ffffff"))
                picker_text = st.color_picker("Màu chữ", value=st.session_state.get("text_color", "#31333F"))
            with c_col2:
                picker_primary = st.color_picker("Màu chủ đạo", value=st.session_state.get("primary_color", "#ff4b4b"))
                picker_sidebar = st.color_picker("Màu nền sidebar", value=st.session_state.get("sidebar_bg", "#f0f2f6"))
                
            slider_opacity = st.slider("Độ mờ sidebar", 0.1, 1.0, float(st.session_state.get("sidebar_opacity", 0.9)), 0.05)
            bg_file_upload = st.file_uploader("🖼️ Tải lên hình nền ứng dụng", type=["png", "jpg", "jpeg"], key="bg_uploader_direct")
            
            st.session_state.bg_color = picker_bg
            st.session_state.text_color = picker_text
            st.session_state.primary_color = picker_primary
            st.session_state.sidebar_bg = picker_sidebar
            st.session_state.sidebar_opacity = slider_opacity
            
            if bg_file_upload is not None:
                compressed_bg = compress_image_to_base64(bg_file_upload, max_size=(1920, 1080), quality=80)
                if compressed_bg:
                    st.session_state.bg_image_base64 = compressed_bg
                    
            if st.button("💾 Lưu Cài Đặt Giao Diện", use_container_width=True, type="primary"):
                save_app_settings_db({
                    "primary_color": st.session_state.primary_color, 
                    "bg_color": st.session_state.bg_color,
                    "sidebar_bg": st.session_state.sidebar_bg, 
                    "sidebar_opacity": st.session_state.sidebar_opacity,
                    "text_color": st.session_state.text_color, 
                    "bg_image_base64": st.session_state.get("bg_image_base64"),
                    "avatar_base64": st.session_state.get("avatar_base64")
                })
                st.success("✅ Đã lưu cài đặt giao diện vĩnh viễn lên cơ sở dữ liệu thành công!")
                st.rerun()

            st.markdown("---")
            st.subheader("👥 Quản Lý Danh Sách Nhân Sự")
            
            try:
                staff_df = get_staff_df_db()
                if staff_df is None or staff_df.empty:
                    staff_df = pd.DataFrame(columns=["id", "name"])
            except Exception as e:
                st.error(f"Lỗi tải dữ liệu nhân sự: {e}")
                staff_df = pd.DataFrame(columns=["id", "name"])
            
            with st.form("staff_form"):
                edited_staff = st.data_editor(
                    staff_df, 
                    num_rows="dynamic", 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "name": st.column_config.TextColumn("Họ và tên nhân sự", required=True)
                    }
                )
                
                submitted_staff = st.form_submit_button("💾 Lưu Nhân Sự", use_container_width=True)
                if submitted_staff:
                    save_staff_list_db(edited_staff)
                    st.cache_data.clear()
                    st.session_state.staff_list = get_staff_list_db()
                    st.success("✅ Đã cập nhật danh sách nhân sự thành công!")
                    st.rerun()

    # ==================== QUẢN LÝ TÀI KHOẢN & PHÂN QUYỀN ====================
    elif current_menu_name == "🛡️ Quản Lý Tài Khoản & Phân Quyền":
        col_mr_h1, col_mr_h2 = st.columns([3, 1])
        with col_mr_h1:
            st.header("🛡️ Quản Lý Tài Khoản & Phân Quyền Chi Tiết")
        with col_mr_h2:
            if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_mr"):
                st.cache_data.clear()
                st.rerun()

        if current_user_role != "Admin":
            st.warning("🔒 Chỉ Quản trị viên mới có quyền quản lý tài khoản và phân quyền!")
        else:
            st.markdown("Tại đây bạn có thể tạo tài khoản, đổi mật khẩu và cấp quyền trực tiếp cho từng nhân sự:")
            
            try:
                staff_list_names = get_staff_list_db()
                for s_name in staff_list_names:
                    chk = supabase.table("user_accounts").select("*").eq("name", s_name).execute() if supabase else None
                    if chk and not chk.data:
                        supabase.table("user_accounts").insert({
                            "name": s_name,
                            "password_hash": hash_password("123456"),
                            "role": "Staff",
                            "perm_input": False,
                            "perm_report": False,
                            "perm_attendance": True,
                            "perm_rules": False
                        }).execute()

                res_roles = supabase.table("user_accounts").select("*").execute() if supabase else None
                if res_roles and res_roles.data:
                    roles_df = pd.DataFrame(res_roles.data)
                    
                    with st.form("manage_accounts_form"):
                        edited_roles_df = st.data_editor(
                            roles_df,
                            column_config={
                                "id": st.column_config.NumberColumn("ID", disabled=True),
                                "name": st.column_config.TextColumn("Họ và tên nhân sự", disabled=True),
                                "password_hash": None,
                                "role": st.column_config.SelectboxColumn("Vai trò", options=["Admin", "Manager", "Staff"], required=True),
                                "perm_input": st.column_config.CheckboxColumn("Nhập sản lượng"),
                                "perm_report": st.column_config.CheckboxColumn("Xem báo cáo"),
                                "perm_attendance": st.column_config.CheckboxColumn("Chấm công"),
                                "perm_rules": st.column_config.CheckboxColumn("Sửa định mức")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        st.markdown("---")
                        st.markdown("##### 🔑 Đổi mật khẩu nhanh cho nhân sự")
                        col_p1, col_p2, col_p3 = st.columns([1.5, 1.5, 1])
                        with col_p1:
                            target_staff_pw = st.selectbox("Chọn nhân sự cần đổi mật khẩu", ["--- Chọn nhân sự ---"] + staff_list_names)
                        with col_p2:
                            new_staff_pass = st.text_input("Mật khẩu mới", type="password", placeholder="Nhập mật khẩu mới...")
                        with col_p3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            btn_update_pw = st.form_submit_button("Cập Nhật Mật Khẩu", use_container_width=True)

                        if btn_update_pw:
                            if target_staff_pw != "--- Chọn nhân sự ---" and new_staff_pass:
                                if len(new_staff_pass) >= 6:
                                    supabase.table("user_accounts").update({
                                        "password_hash": hash_password(new_staff_pass)
                                    }).eq("name", target_staff_pw).execute()
                                    st.success(f"✅ Đã đổi mật khẩu thành công cho **{target_staff_pw}**!")
                                else:
                                    st.error("⚠️ Mật khẩu phải có ít nhất 6 ký tự!")
                            else:
                                st.warning("⚠️ Vui lòng chọn nhân sự và nhập mật khẩu mới!")

                        if st.form_submit_button("💾 Lưu Cập Nhật Quyền Hạn Hàng Loạt", use_container_width=True):
                            for _, row in edited_roles_df.iterrows():
                                r_id = row["id"]
                                supabase.table("user_accounts").update({
                                    "role": row["role"],
                                    "perm_input": bool(row["perm_input"]),
                                    "perm_report": bool(row["perm_report"]),
                                    "perm_attendance": bool(row["perm_attendance"]),
                                    "perm_rules": bool(row["perm_rules"])
                                }).eq("id", r_id).execute()
                            st.cache_data.clear()
                            st.success("✅ Đã cập nhật quyền hạn chi tiết thành công!")
                            st.rerun()
                else:
                    st.info("Chưa có tài khoản nhân sự nào trong hệ thống.")
            except Exception as e:
                st.error(f"Lỗi quản lý tài khoản: {e}")

    # ==================== LÀM SẠCH DỮ LIỆU ====================
    elif current_menu_name == "🧹 Làm Sạch Dữ Liệu":
        col_cd_h1, col_cd_h2 = st.columns([3, 1])
        with col_cd_h1:
            st.header("Làm Sạch Dữ Liệu")
        with col_cd_h2:
            if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_cd"):
                st.cache_data.clear()
                st.rerun()

        if current_user_role != "Admin":
            st.warning("🔒 Tính năng làm sạch dữ liệu chỉ dành cho Admin.")
        else:
            if st.button("🔥 Xóa Toàn Bộ Dữ Liệu Thùng Rác Vĩnh Viễn", use_container_width=True):
                trash_df = get_production_logs_db(is_deleted=True, limit_rows=500)
                if not trash_df.empty:
                    from database import permanent_delete_db
                    permanent_delete_db(trash_df["db_id"].tolist())
                    st.success("✅ Đã làm sạch toàn bộ thùng rác!")
                    st.rerun()
    else:
        st.subheader(current_menu_name)
        st.info(f"Đang hiển thị nội dung cho mục: {current_menu_name}")
