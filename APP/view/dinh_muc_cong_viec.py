# view/dinh_muc_cong_viec.py
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

get_rules_db = db_module.get_rules_db
add_rule_db = db_module.add_rule_db
update_rule_db = db_module.update_rule_db
delete_rule_db = db_module.delete_rule_db

def render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms):
    st.subheader(f"📋 {current_menu_name}")
    
    # 1. Tải dữ liệu định mức thực tế từ Supabase
    rules_df = get_rules_db()
    st.session_state["rules_df"] = rules_df

    # 2. Phân quyền hiển thị thông báo
    is_admin = (current_user_role == "Admin" or user_perms.get("perm_rules", False))
    if not is_admin:
        st.info("👁️ Tài khoản của bạn đang ở chế độ **Chỉ xem bảng định mức**. Bạn không có quyền chỉnh sửa cấu hình này.")
    else:
        st.success("🔓 Bạn có quyền quản trị viên. Tính năng cấu hình, thêm, sửa, xóa bảng định mức đã sẵn sàng.")

    st.markdown("---")

    # 3. NẾU LÀ ADMIN: HIỂN THỊ KHỐI CÔNG CỤ QUẢN LÝ (THÊM / SỬA / XÓA)
    if is_admin:
        st.markdown("### 🛠️ Bộ Công Cụ Cập Nhật Định Mức")
        
        tab_add, tab_edit, tab_delete = st.tabs(["➕ Thêm Mới", "📝 Chỉnh Sửa", "❌ Xóa Hạng Mục"])
        
        # --- TAB 1: THÊM MỚI ---
        with tab_add:
            with st.form("form_add_rule"):
                a_col1, a_col2, a_col3 = st.columns(3)
                with a_col1: new_hm = st.text_input("Tên Hạng Mục Công Việc mới", value="")
                with a_col2: new_hs = st.number_input("Hệ Số Điểm", min_value=0.0, value=1.0, step=0.1)
                with a_col3: new_dv = st.text_input("Đơn Vị Tính", value="Cái")
                new_gc = st.text_input("Ghi Chú bổ sung", value="")
                
                if st.form_submit_button("🚀 Thêm Định Mức Vào Hệ Thống", use_container_width=True):
                    if not new_hm.strip():
                        st.error("⚠️ Vui lòng nhập tên hạng mục công việc!")
                    else:
                        add_rule_db(new_hm.strip(), new_hs, new_dv.strip(), new_gc.strip())
                        st.success(f"✅ Đã thêm mới thành công hạng mục: **{new_hm}**")
                        st.cache_data.clear()
                        st.rerun()

        # --- TAB 2: CHỈNH SỬA ---
        with tab_edit:
            if not rules_df.empty:
                # Tạo danh sách chọn lựa các hạng mục hiện có để sửa
                rule_options = rules_df["Hạng Mục Công Việc"].tolist()
                selected_hm = st.selectbox("Chọn hạng mục cần chỉnh sửa", rule_options, key="sb_edit_rule")
                
                # Lấy dòng dữ liệu hiện tại để đưa vào form sửa
                row_current = rules_df[rules_df["Hạng Mục Công Việc"] == selected_hm].iloc[0]
                
                with st.form("form_edit_rule"):
                    e_col1, e_col2, e_col3 = st.columns(3)
                    with e_col1: edit_hm = st.text_input("Tên Hạng Mục", value=str(row_current["Hạng Mục Công Việc"]))
                    with e_col2: edit_hs = st.number_input("Hệ Số Điểm", min_value=0.0, value=float(row_current["Hệ Số Điểm"]), step=0.1)
                    with e_col3: edit_dv = st.text_input("Đơn Vị Tính", value=str(row_current["Đơn Vị"]))
                    edit_gc = st.text_input("Ghi Chú", value=str(row_current["Ghi Chú"]) if pd.notna(row_current["Ghi Chú"]) else "")
                    
                    if st.form_submit_button("💾 Lưu Thay Đổi Cấu Hình", use_container_width=True):
                        update_rule_db(row_current["db_id"], edit_hm.strip(), edit_hs, edit_dv.strip(), edit_gc.strip())
                        st.success(f"✅ Đã cập nhật thành công cấu hình hạng mục!")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.info("Hệ thống trống danh mục, không thể chỉnh sửa.")

        # --- TAB 3: XÓA HẠNG MỤC ---
        with tab_delete:
            if not rules_df.empty:
                del_options = rules_df["Hạng Mục Công Việc"].tolist()
                selected_del = st.selectbox("Chọn hạng mục muốn xóa vĩnh viễn", del_options, key="sb_del_rule")
                row_del = rules_df[rules_df["Hạng Mục Công Việc"] == selected_del].iloc[0]
                
                st.warning(f"⚠️ Bạn có chắc chắn muốn xóa hạng mục **{selected_del}** không? Hành động này sẽ gỡ bỏ hoàn toàn định mức hệ số khỏi Supabase.")
                if st.button("🔥 Xác Nhận Xóa Vĩnh Viễn", use_container_width=True, key="btn_confirm_del_rule"):
                    delete_rule_db(row_del["db_id"])
                    st.success("❌ Đã xóa hạng mục định mức thành công!")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.info("Hệ thống trống danh mục.")

        st.markdown("---")

    # 4. KHỐI HIỂN THỊ BẢNG DANH MỤC TRỰC QUAN CHO TẤT CẢ NGƯỜI DÙNG
    st.markdown("### 📊 Danh Mục Tham Chiếu Hệ Số Điểm")
    if not rules_df.empty:
        st.dataframe(rules_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Hiện tại bảng dữ liệu trên Supabase trống hoặc tên cột bị lệch. Vui lòng thêm định mới ở form phía trên!")
