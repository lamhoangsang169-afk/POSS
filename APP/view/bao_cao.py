# view/bao_cao.py
import os
import sys
import importlib.util
import streamlit as st
import pandas as pd
import datetime
import io
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

def clean_name(full_name):
    """Hàm rút gọn tên nhân sự (Ví dụ: Nguyễn Hữu Khang Tôn Đức -> Đức)"""
    if not full_name:
        return ""
    name_parts = str(full_name).strip().split()
    if name_parts:
        return name_parts[-1]
    return full_name

def convert_minutes_to_work_days(total_minutes, minutes_per_day=480):
    """
    Hàm cải tiến quy đổi tổng số phút thành chuỗi chi tiết 'X ngày Y phút'.
    Mặc định 1 ngày công tiêu chuẩn = 8 tiếng = 480 phút.
    """
    if total_minutes <= 0:
        return "0 ngày"
    
    days = int(total_minutes // minutes_per_day)
    remaining_minutes = int(total_minutes % minutes_per_day)
    
    if days > 0 and remaining_minutes > 0:
        return f"{days} ngày {remaining_minutes} phút"
    elif days > 0:
        return f"{days} ngày"
    else:
        return f"{remaining_minutes} phút"

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
        att_df["Ngày_DT"] = pd.to_datetime(att_df["Ngày"], errors='coerce')
        att_filtered = att_df[(att_df["Ngày_DT"].dt.date >= start_date) & (att_df["Ngày_DT"].dt.date <= end_date)]
    else:
        att_filtered = pd.DataFrame()

    # --- TÍNH TOÁN BẢNG TỔNG KẾT THEO NHÂN SỰ ---
    summary_staff = prod_df.groupby("Nhân Sự").agg(
        so_luong_thuc_te=("Số Lượng", "sum"),
        tong_diem_tich_luy=("Tổng Điểm", "sum")
    ).reset_index()

    total_all_points = summary_staff["tong_diem_tich_luy"].sum()
    if total_all_points > 0:
        summary_staff["ty_le_hieu_suat"] = (summary_staff["tong_diem_tich_luy"] / total_all_points * 100).round(1)
    else:
        summary_staff["ty_le_hieu_suat"] = 0.0

    summary_staff = summary_staff.sort_values(by="tong_diem_tich_luy", ascending=False).reset_index(drop=True)
    summary_staff.insert(0, "Xếp Hạng (Top)", [f"🏆 Top {i+1}" for i in range(len(summary_staff))])

    # Hiển thị Bảng 1 lên giao diện
    st.markdown("### 📋 Bảng Tổng Kết Theo Nhân Sự")
    display_table1 = summary_staff.rename(columns={
        "Nhân Sự": "Nhân Sự",
        "so_luong_thuc_te": "Số Lượng Thực Tế",
        "tong_diem_tich_luy": "Tổng Điểm",
        "ty_le_hieu_suat": "Hiệu Suất"
    })
    display_table1["Hiệu Suất"] = display_table1["Hiệu Suất"].astype(str) + "%"
    st.dataframe(display_table1, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- TÍNH TOÁN BẢNG ĐỐI CHIẾU THỜI GIAN VÀ SẢN LƯỢNG ---
    st.markdown("### 👥 Bảng Đối Chiếu Thời Gian Làm Việc & Sản Lượng")
    
    if not att_filtered.empty and "Nhân Sự" in att_filtered.columns:
        time_staff = att_filtered.groupby("Nhân Sự").agg(
            tong_phut_lam_viec=("Số Phút Làm Việc", "sum")
        ).reset_index()
    else:
        time_staff = pd.DataFrame(columns=["Nhân Sự", "tong_phut_lam_viec"])

    # Gộp bảng sản lượng và bảng chấm công nâng cao
    cross_df = pd.merge(summary_staff, time_staff, on="Nhân Sự", how="left").fillna(0)
    cross_df["tong_phut_lam"] = cross_df["tong_phut_lam_viec"].astype(int)
    cross_df["diem_moi_phut"] = (cross_df["tong_diem_tich_luy"] / cross_df["tong_phut_lam"].replace(0, 1)).round(3)
    
    # Quy đổi tổng số phút thành chuỗi chi tiết "X ngày Y phút"
    cross_df["Số Ngày Làm Việc"] = cross_df["tong_phut_lam"].apply(lambda x: convert_minutes_to_work_days(x, minutes_per_day=480))
    
    cross_display = cross_df[[
        "Xếp Hạng (Top)", "Nhân Sự", "Số Ngày Làm Việc", "tong_phut_lam", 
        "so_luong_thuc_te", "tong_diem_tich_luy", "diem_moi_phut", "ty_le_hieu_suat"
    ]].rename(columns={
        "tong_phut_lam": "Tổng Số Phút Làm",
        "so_luong_thuc_te": "Tổng Sản Lượng Thực Tế",
        "tong_diem_tich_luy": "Tổng Điểm",
        "diem_moi_phut": "Điểm Mỗi Phút",
        "ty_le_hieu_suat": "Hiệu Suất Sản Lượng (%)"
    })
    cross_display["Hiệu Suất Sản Lượng (%)"] = cross_display["Hiệu Suất Sản Lượng (%)"].astype(str) + "%"
    st.dataframe(cross_display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- KHỐI BIỂU ĐỒ TRÒN & TÍNH NĂNG XUẤT FILE THỰC TẾ ---
    chart_col, text_col = st.columns([1, 1.2])
    
    with chart_col:
        st.markdown("##### 📥 Thao Tác Xuất Dữ Liệu")
        
        # Chuẩn bị dữ liệu DataFrame để xuất file Excel
        export_df = cross_display.copy() if 'cross_display' in locals() else summary_staff.copy()
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='BaoCao_HieuSuat')
        excel_data = output.getvalue()
        
        file_name_download = f"Bao_Cao_San_Luong_{start_date}_den_{end_date}.xlsx"
        
        # Nút tải file Excel về máy tính
        st.download_button(
            label="💾 Tải File Về Máy (.xlsx)",
            data=excel_data,
            file_name=file_name_download,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # Nút xuất file và lưu trực tiếp lên Cloud (Supabase Storage)
        if st.button("☁️ Xuất File & Lưu Cloud", use_container_width=True, key="btn_export_cloud_real"):
            if db.supabase is not None:
                try:
                    bucket_reports = "reports-storage"
                    unique_filename = f"baocao_{start_date}_{end_date}_{int(datetime.datetime.now().timestamp())}.xlsx"
                    
                    db.supabase.storage.from_(bucket_reports).upload(
                        path=unique_filename,
                        file=excel_data,
                        file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
                    )
                    
                    public_report_url = db.supabase.storage.from_(bucket_reports).get_public_url(unique_filename)
                    
                    if "cloud_folders" not in st.session_state:
                        st.session_state["cloud_folders"] = []
                    
                    st.session_state["cloud_folders"].append({
                        "db_id": len(st.session_state["cloud_folders"]) + 1,
                        "name": unique_filename,
                        "url": public_report_url,
                        "is_deleted": False
                    })
                    
                    st.success(f"✅ Đã lưu báo cáo lên Cloud thành công! Tên file: `{unique_filename}`")
                except Exception as e:
                    st.error(f"❌ Lỗi tải lên Cloud Storage: {e}")
            else:
                st.error("⚠️ Chưa kết nối cơ sở dữ liệu Supabase để lưu file lên Cloud!")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        short_labels = [clean_name(name) for name in summary_staff["Nhân Sự"]]
        color_palette = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
        
        fig = go.Figure(data=[go.Pie(
            labels=short_labels,
            values=summary_staff["tong_diem_tich_luy"],
            textinfo='percent',
            textfont_size=15,
            marker=dict(colors=color_palette, line=dict(color='#ffffff', width=2))
        )])
        fig.update_layout(
            showlegend=False,
            margin=dict(t=15, b=15, l=15, r=15),
            height=280
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with text_col:
        st.markdown("### 📌 Chi Tiết Điểm Số & Tỷ Lệ")
        st.markdown("<br>", unsafe_allow_html=True)
        
        color_markers = ["🔵", "🔴", "🟢", "🟡", "🟣"]
        for idx, row in summary_staff.iterrows():
            short_name = clean_name(row['Nhân Sự'])
            marker = color_markers[idx % len(color_markers)]
            st.info(f"{marker} **{short_name}**: {row['tong_diem_tich_luy']:,.1f} điểm ({row['ty_le_hieu_suat']}%)")
