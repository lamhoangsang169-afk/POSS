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
supabase = db_module.supabase

def render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms):
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.subheader(f"📋 {current_menu_name}")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_rules"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Tải bảng định mức thực tế từ database Supabase
    rules_df = get_rules_db()
    st.session_state["rules_df"] = rules_df

    is_admin = (current_user_role == "Admin" or user_perms.get("perm_rules", False))

    if not rules_df.empty:
        display_df = rules_df.copy()
        
        # Đổi tên cột id khóa chính sang 'id' viết thường hiển thị giống ảnh mẫu
        if "db_id" in display_df.columns:
            display_df = display_df.rename(columns={"db_id": "id"})
            
        # Tự động chèn cột số thứ tự STT viết hoa hiển thị động ở vị trí số 2
        if "STT" not in display_df.columns:
            display_df.insert(1, "STT", range(1, len(display_df) + 1))
            
        # Cơ chế quét tìm và đồng bộ cột hạng mục công việc
        task_col_real = None
        for col in display_df.columns:
            if str(col).lower().strip() in ["hạng mục công việc", "hang_muc_cong_viec", "hang_muc", "hạng mục"]:
                task_col_real = col
                break
        
        if task_col_real and task_col_real != "Hạng Mục Công Việc":
            display_df = display_df.rename(columns={task_col_real: "Hạng Mục Công Việc"})
            
        columns_order = ["id", "STT", "Hạng Mục Công Việc", "Đơn Vị", "Hệ Số Điểm", "Ghi Chú"]
        final_columns = [c for c in columns_order if c in display_df.columns]
        display_df = display_df[final_columns]
        
        # === NÂNG CẤP TÍNH NĂNG CHỈNH SỬA TRỰC TIẾP TRÊN BẢNG ===
        # Cho phép chỉnh sửa (num_rows="dynamic") nếu là Admin, ngược lại chỉ cho xem
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" if is_admin else "fixed",
            disabled=["id", "STT"] if is_admin else True, # Khóa cột ID và STT để tránh gãy cấu trúc dữ liệu
            key="rules_data_editor"
        )
    else:
        st.info("Chưa có dữ liệu định mức công việc nào trong hệ thống.")
        # Nếu database trống hoàn toàn, Admin vẫn có thể tạo bảng mới từ đầu
        if is_admin:
            empty_df = pd.DataFrame(columns=["id", "STT", "Hạng Mục Công Việc", "Đơn Vị", "Hệ Số Điểm", "Ghi Chú"])
            edited_df = st.data_editor(empty_df, use_container_width=True, hide_index=True, num_rows="dynamic", key="rules_empty_editor")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. KHỐI THAO TÁC NÂNG CAO LƯU DỮ LIỆU ĐỘNG CHO ADMIN
    if is_admin:
        st.markdown("#### ⚙️ Thao Tác Nâng Cao (Admin)")
        
        confirm_delete_all = st.checkbox("⚠️ Tôi chắc chắn muốn xóa toàn bộ danh mục công việc trong hệ thống", key="chk_confirm_delete_all_rules")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("📝 Lưu Thay Đổi Định Mức", use_container_width=True, key="btn_save_rules_change"):
                if supabase is not None:
                    with st.spinner("⏳ Đang đồng bộ dữ liệu sửa đổi lên Supabase..."):
                        try:
                            # 1. Đọc dữ liệu thô từ session state của data_editor để lấy danh sách Thêm/Sửa/Xóa
                            editor_state = st.session_state["rules_data_editor"]
                            
                            # XỬ LÝ HÀNG XÓA (Deleted rows)
                            if "deleted_rows" in editor_state and editor_state["deleted_rows"]:
                                for row_idx in editor_state["deleted_rows"]:
                                    row_id = display_df.iloc[row_idx]["id"]
                                    supabase.table("rules").delete().eq("id", row_id).execute()

                            # XỬ LÝ HÀNG THÊM MỚI (Added rows)
                            if "added_rows" in editor_state and editor_state["added_rows"]:
                                for row_data in editor_state["added_rows"]:
                                    insert_data = {
                                        "hang_muc_cong_viec": row_data.get("Hạng Mục Công Việc", ""),
                                        "don_vi": row_data.get("Đơn Vị", "Cái"),
                                        "he_so_diem": float(row_data.get("Hệ Số Điểm", 1.0)),
                                        "ghi_chu": row_data.get("Ghi Chú", "")
                                    }
                                    supabase.table("rules").insert(insert_data).execute()

                            # XỬ LÝ HÀNG CHỈNH SỬA Ô DỮ LIỆU (Edited rows)
                            if "edited_rows" in editor_state and editor_state["edited_rows"]:
                                for row_idx_str, updated_cols in editor_state["edited_rows"].items():
                                    row_idx = int(row_idx_str)
                                    row_id = display_df.iloc[row_idx]["id"]
                                    
                                    # Chuyển đổi tên cột giao diện về tên cột Supabase tương ứng
                                    update_data = {}
                                    if "Hạng Mục Công Việc" in updated_cols: update_data["hang_muc_cong_viec"] = updated_cols["Hạng Mục Công Việc"]
                                    if "Đơn Vị" in updated_cols: update_data["don_vi"] = updated_cols["Đơn Vị"]
                                    if "Hệ Số Điểm" in updated_cols: update_data["he_so_diem"] = float(updated_cols["Hệ Số Điểm"])
                                    if "Ghi Chú" in updated_cols: update_data["ghi_chu"] = updated_cols["Ghi Chú"]
                                    
                                    if update_data:
                                        supabase.table("rules").update(update_data).eq("id", row_id).execute()

                            st.success("✅ Đã ghi nhận và đồng bộ toàn bộ thao tác Thêm / Sửa / Xóa lên Supabase thành công!")
                            st.cache_data.clear()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Lỗi đồng bộ dữ liệu: {e}")
                else:
                    st.error("Kết nối cơ sở dữ liệu Supabase thất bại.")
                
        with col_btn2:
            if st.button("🗑️ Xóa Toàn Bộ Định Mức", use_container_width=True, key="btn_delete_all_rules"):
                if not confirm_delete_all:
                    st.error("⚠️ Bạn phải tích chọn vào ô xác nhận 'Tôi chắc chắn muốn xóa toàn bộ danh mục...' trước khi thực hiện hành động này!")
                else:
                    if supabase is not None:
                        try:
                            supabase.table("rules").delete().neq("id", 0).execute()
                            st.success("🔥 Đã xóa sạch toàn bộ danh mục định mức công việc khỏi cơ sở dữ liệu thành công!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa bảng dữ liệu: {e}")
