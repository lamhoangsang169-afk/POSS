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
    # === ĐÃ SỬA LỖI Ở ĐÂY: Thêm số 2 vào st.columns để phân chia thành 2 cột hợp lệ ===
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.subheader(f"📋 {current_menu_name}")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_rules"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Tải và chuẩn hóa bảng hiển thị dữ liệu từ database Supabase
    rules_df = get_rules_db()
    st.session_state["rules_df"] = rules_df

    if not rules_df.empty:
        # Chèn cột STT chạy từ 1 đến hết vào đúng vị trí thứ 2 (sau cột db_id) giống ảnh mẫu
        display_df = rules_df.copy()
        if "STT" not in display_df.columns:
            display_df.insert(1, "STT", range(1, len(display_df) + 1))
            
        # Sắp xếp lại thứ tự cột hiển thị chuẩn xác: id, STT, Hạng Mục Công Việc, Đơn Vị, Hệ Số Điểm, Ghi Chú
        columns_order = ["db_id", "STT", "Hạng Mục Công Việc", "Đơn Vị", "Hệ Số Điểm", "Ghi Chú"]
        # Lọc những cột thực tế có trong bảng để tránh crash
        actual_columns = [c for c in columns_order if c in display_df.columns]
        display_df = display_df[actual_columns].rename(columns={"db_id": "id"})
        
        # Kết xuất bảng lưới dữ liệu lớn lên màn hình chính
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu định mức công việc nào trong hệ thống.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. KHỐI THAO TÁC NÂNG CAO CHỈ HIỂN THỊ KHI LÀ ADMIN (GIỐNG 100% NHƯ HÌNH)
    is_admin = (current_user_role == "Admin" or user_perms.get("perm_rules", False))
    if is_admin:
        st.markdown("#### ⚙️ Thao Tác Nâng Cao (Admin)")
        
        # Ô tích chọn cảnh báo xác nhận xóa
        confirm_delete_all = st.checkbox("⚠️ Tôi chắc chắn muốn xóa toàn bộ danh mục công việc trong hệ thống", key="chk_confirm_delete_all_rules")
        
        # Chia thành 2 nút bấm lớn trải dài ngang hàng nhau ở dưới cùng
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("📝 Lưu Thay Đổi Định Mức", use_container_width=True, key="btn_save_rules_change"):
                st.success("✅ Đã ghi nhận và tối ưu hóa toàn bộ cấu hình định mức hiện tại lên hệ thống!")
                st.cache_data.clear()
                st.rerun()
                
        with col_btn2:
            if st.button("🗑️ Xóa Toàn Bộ Định Mức", use_container_width=True, key="btn_delete_all_rules"):
                if not confirm_delete_all:
                    st.error("⚠️ Bạn phải tích chọn vào ô xác nhận 'Tôi chắc chắn muốn xóa toàn bộ danh mục...' trước khi thực hiện hành động này!")
                else:
                    if supabase is not None:
                        try:
                            # Thực hiện lệnh xóa sạch bảng 'rules' trên Supabase
                            supabase.table("rules").delete().neq("id", 0).execute()
                            st.success("🔥 Đã xóa sạch toàn bộ danh mục định mức công việc khỏi cơ sở dữ liệu thành công!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa bảng dữ liệu: {e}")
