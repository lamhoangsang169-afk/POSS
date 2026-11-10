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
update_all_historical_production_scores_db = getattr(db_module, "update_all_historical_production_scores_db", None)

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
        
        if "db_id" in display_df.columns:
            display_df = display_df.rename(columns={"db_id": "id"})
        
        if "STT" not in display_df.columns:
            display_df.insert(1, "STT", range(1, len(display_df) + 1))
        
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
        
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" if is_admin else "fixed",
            disabled=["id", "STT"] if is_admin else True,
            key="rules_data_editor"
        )
    else:
        st.info("Chưa có dữ liệu định mức công việc nào trong hệ thống.")
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
                            editor_state = st.session_state.get("rules_data_editor", {})
                            
                            # XỬ LÝ HÀNG XÓA
                            if "deleted_rows" in editor_state and editor_state["deleted_rows"]:
                                for row_idx in editor_state["deleted_rows"]:
                                    row_id = display_df.iloc[row_idx]["id"]
                                    supabase.table("rules").delete().eq("id", row_id).execute()
                            
                            # Hàm kiểm tra và ép kiểu ID hợp lệ (xử lý cả 1, 1.0, "1")
                            def parse_valid_id(val):
                                if pd.isna(val) or val is None:
                                    return None
                                s = str(val).strip()
                                if not s or s.startswith("arg_") or s.lower() in ["none", "nan"]:
                                    return None
                                try:
                                    return int(float(s))
                                except Exception:
                                    return None

                            for idx, row in edited_df.iterrows():
                                h_muc = str(row.get("Hạng Mục Công Việc", "")).strip()
                                d_vi = str(row.get("Đơn Vị", "Cái")).strip()
                                hs_diem = row.get("Hệ Số Điểm", 1.0)
                                g_chu = str(row.get("Ghi Chú", "")).strip() if pd.notna(row.get("Ghi Chú")) else ""
                                clean_id = parse_valid_id(row.get("id"))

                                if h_muc:
                                    try:
                                        hs_diem = float(str(hs_diem).replace(",", ".").strip())
                                    except Exception:
                                        hs_diem = 1.0

                                    payload = {
                                        "hang_muc_cong_viec": h_muc,
                                        "don_vi": d_vi,
                                        "he_so_diem": hs_diem,
                                        "ghi_chu": g_chu
                                    }

                                    if clean_id is None:
                                        # Thêm mới nếu chưa có ID
                                        supabase.table("rules").insert(payload).execute()
                                    else:
                                        # Cập nhật theo đúng ID
                                        supabase.table("rules").update(payload).eq("id", clean_id).execute()
                                        # Cập nhật bổ trợ theo tên hạng mục để xóa sạch hệ số cũ còn sót lại
                                        supabase.table("rules").update({"he_so_diem": hs_diem}).eq("hang_muc_cong_viec", h_muc).execute()

                            st.cache_data.clear()
                            st.success("✅ Đã lưu định mức mới thành công vào cơ sở dữ liệu!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi khi lưu dữ liệu định mức: {e}")

        with col_btn2:
            if confirm_delete_all:
                if st.button("🗑️ Xóa Toàn Bộ Định Mức", use_container_width=True, type="primary", key="btn_del_all_rules_confirm"):
                    try:
                        supabase.table("rules").delete().neq("id", -1).execute()
                        st.cache_data.clear()
                        st.success("✅ Đã xóa toàn bộ bảng định mức thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi xóa toàn bộ định mức: {e}")

        # === KHỐI NÚT BẤM ĐỒNG BỘ ĐIỂM LỊCH SỬ ===
        st.markdown("---")
        st.markdown("#### 🔄 Đồng Bộ Điểm Lịch Sử")
        st.info("💡 Sau khi bạn bấm '📝 Lưu Thay Đổi Định Mức' ở trên, hãy bấm nút dưới đây để hệ thống tự động cập nhật lại tên, hệ số và điểm số cho toàn bộ các báo cáo cũ trong lịch sử.")

        if st.button("🚀 Cập nhật lại toàn bộ điểm lịch sử theo định mức mới", use_container_width=True, type="primary", key="btn_sync_history_scores"):
            if update_all_historical_production_scores_db is not None:
                status_container = st.empty()
                status_container.info("⏳ Đang quét cơ sở dữ liệu và tính toán điểm mới theo định mức đã lưu...")
                
                success, msg = update_all_historical_production_scores_db()
                status_container.empty()
                
                if success:
                    st.success(f"✅ {msg}")
                    st.info("👉 Bạn có thể chuyển sang menu **1. Nhập Sản Lượng** để kiểm tra lại các bản ghi cũ.")
                else:
                    st.error(f"❌ {msg}")
            else:
                st.error("⚠️ Không tìm thấy hàm `update_all_historical_production_scores_db` trong `database.py`.")
