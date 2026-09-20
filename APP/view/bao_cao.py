# view/bao_cao.py
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
get_production_logs_by_date_range = db_module.get_production_logs_by_date_range

def render_bao_cao(current_menu_name):
    st.subheader(f"📊 {current_menu_name}")
    
    # --- BỘ LỌC THỜI GIAN ---
    now_vn = datetime.datetime.now(VN_TIMEZONE)
    col_date_1, col_date_2 = st.columns(2)
    with col_date_1:
        start_date = st.date_input("Từ ngày", now_vn.date() - datetime.timedelta(days=7))
    with col_date_2:
        end_date = st.date_input("Đến ngày", now_vn.date())
        
    if start_date > end_date:
        st.error("⚠️ Ngày bắt đầu không thể lớn hơn ngày kết thúc!")
        return

    st.markdown("---")

    # --- TẢI DỮ LIỆU TỪ DATABASE ---
    with st.spinner("🔄 Đang tổng hợp dữ liệu báo cáo..."):
        report_df = get_production_logs_by_date_range(start_date, end_date)
    
    if not report_df.empty:
        # Chuẩn hóa kiểu dữ liệu cho các cột tính toán để tránh lỗi vẽ biểu đồ
        if "Tổng Điểm" in report_df.columns:
            report_df["Tổng Điểm"] = pd.to_numeric(report_df["Tổng Điểm"], errors='coerce').fillna(0)
        if "Số Lượng" in report_df.columns:
            report_df["Số Lượng"] = pd.to_numeric(report_df["Số Lượng"], errors='coerce').fillna(0)

        # --- 1. KHỐI THỐNG KÊ TỔNG QUAN (KPI CARDS) ---
        total_records = len(report_df)
        total_points = report_df["Tổng Điểm"].sum() if "Tổng Điểm" in report_df.columns else 0
        total_qty = report_df["Số Lượng"].sum() if "Số Lượng" in report_df.columns else 0
        
        card1, card2, card3 = st.columns(3)
        with card1:
            st.metric("📋 Tổng số bản ghi", f"{total_records} đơn")
        with card2:
            st.metric("🎯 Tổng điểm tích lũy", f"{total_points:,.1f} điểm")
        with card3:
            st.metric("📦 Tổng sản lượng", f"{total_qty:,} sản phẩm")
            
        st.markdown("---")
        
        # --- 2. KHỐI BIỂU ĐỒ TRỰC QUAN (CHARTS) ---
        st.markdown("### 📈 Biểu Đồ Phân Tích Hiệu Suất")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("#### 👤 Tổng điểm theo Nhân sự")
            if "Nhân Sự" in report_df.columns and "Tổng Điểm" in report_df.columns:
                # Nhóm dữ liệu tính tổng điểm của từng người
                staff_points = report_df.groupby("Nhân Sự")["Tổng Điểm"].sum().reset_index()
                # Sắp xếp từ cao đến thấp để biểu đồ đẹp hơn
                staff_points = staff_points.sort_values(by="Tổng Điểm", ascending=False)
                st.bar_chart(data=staff_points, x="Nhân Sự", y="Tổng Điểm", color="#1f77b4", use_container_width=True)
            else:
                st.info("Thiếu dữ liệu cột 'Nhân Sự' hoặc 'Tổng Điểm' để vẽ biểu đồ.")
                
        with chart_col2:
            st.markdown("#### 📌 Sản lượng theo Hạng mục công việc")
            if "Hạng Mục Công Việc" in report_df.columns and "Số Lượng" in report_df.columns:
                # Nhóm dữ liệu tính tổng sản lượng theo từng hạng mục
                task_qty = report_df.groupby("Hạng Mục Công Việc")["Số Lượng"].sum().reset_index()
                task_qty = task_qty.sort_values(by="Số Lượng", ascending=False)
                st.bar_chart(data=task_qty, x="Hạng Mục Công Việc", y="Số Lượng", color="#ff7f0e", use_container_width=True)
            else:
                st.info("Thiếu dữ liệu cột 'Hạng Mục Công Việc' hoặc 'Số Lượng' để vẽ biểu đồ.")

        st.markdown("---")

        # --- 3. KHỐI BẢNG DỮ LIỆU CHI TIẾT ---
        st.markdown("### 📋 Bảng Chi Tiết Bản Ghi Sản Lượng")
        # Thêm cột STT hiển thị động trên lưới dữ liệu
        display_df = report_df.copy()
        display_df.insert(0, "STT", range(1, len(display_df) + 1))
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
    else:
        st.info("Chưa có dữ liệu báo cáo sản lượng nào được ghi nhận trong khoảng thời gian được chọn.")
