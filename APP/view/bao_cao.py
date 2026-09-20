# view/bao_cao.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go

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
get_attendance_db = db_module.get_attendance_db

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

    # --- TẢI DỮ LIỆU GỐC TỪ DATABASE ---
    with st.spinner("🔄 Đang xử lý và tổng hợp dữ liệu nâng cao..."):
        prod_df = get_production_logs_by_date_range(start_date, end_date)
        att_df = get_attendance_db()

    # Kiểm tra xem có dữ liệu sản lượng không
    if prod_df.empty:
        st.info("Chưa có dữ liệu sản lượng nào được ghi nhận trong khoảng thời gian này.")
        return

    # Chuẩn hóa kiểu số cho các trường tính toán
    prod_df["Tổng Điểm"] = pd.to_numeric(prod_df["Tổng Điểm"], errors='coerce').fillna(0)
    prod_df["Số Lượng"] = pd.to_numeric(prod_df["Số Lượng"], errors='coerce').fillna(0)

    if not att_df.empty:
        att_df["Số Phút Làm Việc"] = pd.to_numeric(att_df["Số Phút Làm Việc"], errors='coerce').fillna(0)
        # Lọc bảng chấm công theo khoảng ngày được chọn
        att_df["Ngày_DT"] = pd.to_datetime(att_df["Ngày"], errors='coerce')
        att_filtered = att_df[(att_df["Ngày_DT"].dt.date >= start_date) & (att_df["Ngày_DT"].dt.date <= end_date)]
    else:
        att_filtered = pd.DataFrame()

    # --- TÍNH TOÁN BẢNG TỔNG KẾT THEO NHÂN SỰ ---
    summary_staff = prod_df.groupby("Nhân Sự").agg(
        📊_Số_Lượng_Thực_Tế=("Số Lượng", "sum"),
        🎯_Tổng_Điểm=("Tổng Điểm", "sum")
    ).reset_index()

    total_all_points = summary_staff["🎯_Tổng_Điểm"].sum()
    if total_all_points > 0:
        summary_staff["📈_Tỷ_Lệ_Hiệu_Suất"] = (summary_staff["🎯_Tổng_Điểm"] / total_all_points * 100).round(2).astype(str) + "%"
    else:
        summary_staff["📈_Tỷ_Lệ_Hiệu_Suất"] = "0%"

    # Xếp hạng nhân sự theo tổng điểm từ cao xuống thấp
    summary_staff = summary_staff.sort_values(by="🎯_Tổng_Điểm", ascending=False).reset_index(drop=True)
    summary_staff.insert(0, "Xếp Hạng (Top)", [f"🏆 Top {i+1}" for i in range(len(summary_staff))])

    # Hiển thị Bảng 1 lên giao diện
    st.markdown("### 📋 Bảng Tổng Kết Hiệu Suất Theo Nhân Sự")
    st.dataframe(summary_staff, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- TÍNH TOÁN BẢNG ĐỐI CHIẾU THỜI GIAN VÀ SẢN LƯỢNG ---
    st.markdown("### 👥 Bảng Đối Chiếu Thời Gian Làm Việc & Sản Lượng")
    
    # Tính tổng số phút đi làm của từng nhân sự từ bảng chấm công lọc được
    if not att_filtered.empty and "Nhân Sự" in att_filtered.columns:
        time_staff = att_filtered.groupby("Nhân Sự")["Số Phút Làm Việc"].sum().reset_index()
    else:
        time_staff = pd.DataFrame(columns=["Nhân Sự", "Số Phút Làm Việc"])

    # Gộp bảng sản lượng và bảng thời gian lại với nhau
    cross_df = pd.merge(summary_staff, time_staff, on="Nhân Sự", how="left").fillna(0)
    
    # Tính toán các chỉ số phân tích sâu
    cross_df["⏱️ Tổng Số Phút Làm"] = cross_df["Số Phút Làm Việc"].astype(int)
    cross_df["⚡ Điểm Mỗi Phút"] = (cross_df["🎯_Tổng_Điểm"] / cross_df["⏱️ Tổng Số Phút Làm"].replace(0, 1)).round(3)
    
    # Đổi tên cột hiển thị cho gọn gàng giống mẫu của bạn
    cross_display = cross_df[[
        "Xếp Hạng (Top)", "Nhân Sự", "⏱️ Tổng Số Phút Làm", 
        "📊_Số_Lượng_Thực_Tế", "🎯_Tổng_Điểm", "⚡ Điểm Mỗi Phút", "📈_Tỷ_Lệ_Hiệu_Suất"
    ]].rename(columns={
        "📊_Số_Lượng_Thực_Tế": "Tổng Sản Lượng",
        "🎯_Tổng_Điểm": "Tổng Điểm Tích Lũy",
        "📈_Tỷ_Lệ_Hiệu_Suất": "Tỷ Lệ Đóng Góp (%)"
    })
    
    st.dataframe(cross_display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- KHỐI BIỂU ĐỒ TRÒN (PIE CHART) & CHI TIẾT TỶ LỆ ---
    st.markdown("### 📌 Chi Tiết Điểm Số & Tỷ Lệ Đóng Góp")
    
    chart_col, text_col = st.columns([1, 2])
    
    with chart_col:
        # Sử dụng thư viện Plotly để vẽ biểu đồ tròn hiển thị % đẹp mắt như ảnh mẫu
        fig = go.Figure(data=[go.Pie(
            labels=summary_staff["Nhân Sự"],
            values=summary_staff["🎯_Tổng_Điểm"],
            hole=0.3, # Biểu đồ dạng Donut như mẫu
            textinfo='percent+label' if len(summary_staff) <= 3 else 'percent',
            marker=dict(colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
        )])
        fig.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=260
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with text_col:
        st.markdown("<br>", unsafe_allow_html=True)
        # Hiển thị khối danh sách ghi chú tỷ lệ ở bên cạnh
        for idx, row in summary_staff.iterrows():
            st.info(f"🔹 **{row['Xếp Hạng (Top)']}**: {row['Nhân Sự']} đạt **{row['🎯_Tổng_Điểm']:,.1f} điểm** (Chiếm tỷ lệ **{row['📈_Tỷ_Lệ_Hiệu_Suất']}** toàn hệ thống).")
