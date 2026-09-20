# view/thu_muc_bao_cao.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime
import io

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
get_production_logs_db = db_module.get_production_logs_db
get_attendance_db = db_module.get_attendance_db

def to_excel(df1, df2):
    """Hàm chuyển đổi các bảng dữ liệu thành file Excel nhiều Sheet"""
    output = io.BytesIO()
    # Sử dụng openpyxl tích hợp sẵn trong pandas để ghi file
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not df1.empty:
            df1.to_excel(writer, sheet_name='Sản Lượng', index=False)
        if not df2.empty:
            df2.to_excel(writer, sheet_name='Chấm Công', index=False)
    processed_data = output.getvalue()
    return processed_data

def render_thu_muc_bao_cao(current_menu_name):
    st.subheader(f"📂 {current_menu_name}")
    
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    today_str = now_vn.strftime("%Y-%m-%d")

    # --- KHỐI CÔNG CỤ XUẤT FILE TỰ ĐỘNG ---
    st.markdown("### 📥 Trung Tâm Xuất Dữ Liệu Tổng Hợp")
    
    with st.spinner("🔄 Đang chuẩn bị cấu trúc tệp dữ liệu..."):
        prod_df = get_production_logs_db(is_deleted=False, limit_rows=500)
        att_df = get_attendance_db()

    col_btn1, col_btn2 = st.columns(2)
    
    # Tạo tệp Excel nhị phân
    excel_data = to_excel(prod_df, att_df)
    file_name_download = f"Bao_Cao_Tong_Hop_POSS_{today_str}.xlsx"

    with col_btn1:
        # Nút bấm tích hợp bộ tải tải trực tiếp từ Streamlit về máy Client
        st.download_button(
            label="💾 Tải Tệp Excel Về Máy",
            data=excel_data,
            file_name=file_name_download,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col_btn2:
        if st.button("🚀 Đồng Bộ & Lưu Lên Đám Mây", use_container_width=True):
            # Tính năng lưu vết động vào cấu trúc danh mục
            if "cloud_folders" not in st.session_state:
                st.session_state["cloud_folders"] = []
                
            new_cloud_file = {
                "name": file_name_download,
                "time": now_vn.strftime("%H:%M:%S"),
                "size": f"{len(excel_data)/1024:.1f} KB"
            }
            st.session_state["cloud_folders"].append(new_cloud_file)
            st.success(f"✅ Đã đóng gói và đồng bộ file `{file_name_download}` lên Cloud Thư mục báo cáo thành công!")

    st.markdown("---")

    # --- KHỐI QUAN SÁT THƯ MỤC CẤU TRÚC ĐÁM MÂY ---
    st.markdown("### 🗂️ Cấu Trúc Thư Mục Lưu Trữ Báo Cáo")
    
    # 1. Thư mục hệ thống cố định
    with st.expander("📌 Thư Mục Hệ Thống (Mặc định)", expanded=True):
        st.markdown(f"📄 `Cấu_Hình_Định_Mức_Công_Việc.xlsx` *(Dữ liệu gốc tham chiếu)*")
        st.markdown(f"📄 `Danh_Sách_Nhân_Sự_Chạy_Mẫu.xlsx` *(Bảng nhân sự)*")

    # 2. Thư mục động lưu các file do người dùng bấm xuất ra
    with st.expander("📂 Thư Mục Báo Cáo Xuất Bản (Cloud Storage)", expanded=True):
        cloud_files = st.session_state.get("cloud_folders", [])
        if cloud_files:
            for f in cloud_files:
                st.markdown(f"📊 `{f['name']}` | 🕒 Khởi tạo: {f['time']} | 📦 Dung lượng: {f['size']}")
        else:
            st.info("Chưa có tệp báo cáo tổng hợp nào được đồng bộ lên đám mây ngày hôm nay. Hãy bấm nút 'Đồng Bộ & Lưu Lên Đám Mây' ở phía trên.")
