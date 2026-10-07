# view/bao_cao.py
import streamlit as st
import pandas as pd
import datetime
import io
import plotly.graph_objects as go

from database import get_production_logs_by_date_range, get_attendance_db
import utils

VN_TIMEZONE = utils.VN_TIMEZONE

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
    Hàm quy đổi tổng số phút thành chuỗi chi tiết 'X ngày Y phút'.
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
    
    if "report_start_date" not in st.session_state:
        st.session_state.report_start_date = datetime.date.today()
    if "report_end_date" not in st.session_state:
        st.session_state.report_end_date = datetime.date.today()

    col_date_1, col_date_2 = st.columns(2)
    with col_date_1:
        start_date = st.date_input("Từ ngày", value=st.session_state.report_start_date, key="widget_report_start")
    with col_date_2:
        end_date = st.date_input("Đến ngày", value=st.session_state.report_end_date, key="widget_report_end")
        
    st.session_state.report_start_date = start_date
    st.session_state.report_end_date = end_date

    if start_date > end_date:
        st.error("⚠ Ngày bắt đầu không thể lớn hơn ngày kết thúc!")
        return

    st.markdown("---")

    with st.spinner("🔄 Đang xử lý và tổng hợp dữ liệu nâng cao..."):
        prod_df = get_production_logs_by_date_range(start_date, end_date)
        att_df = get_attendance_db()

    if prod_df.empty:
        st.info("Chưa có dữ liệu sản lượng nào được ghi nhận trong khoảng thời gian này.")
        return

    prod_df["Tổng Điểm"] = pd.to_numeric(prod_df["Tổng Điểm"], errors='coerce').fillna(0)
    prod_df["Số Lượng"] = pd.to_numeric(prod_df["Số Lượng"], errors='coerce').fillna(0)

    if not att_df.empty:
        att_df["Số Phút Làm Việc"] = pd.to_numeric(att_df["Số Phút Làm Việc"], errors='coerce').fillna(0)
        att_df["Ngày_DT"] = pd.to_datetime(att_df["Ngày"], errors='coerce')
        att_filtered = att_df[(att_df["Ngày_DT"].dt.date >= start_date) & (att_df["Ngày_DT"].dt.date <= end_date)]
    else:
        att_filtered = pd.DataFrame()

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

    st.markdown("### 👥 Bảng Đối Chiếu Thời Gian Làm Việc & Sản Lượng")
    
    if not att_filtered.empty and "Nhân Sự" in att_filtered.columns:
        time_staff = att_filtered.groupby("Nhân Sự").agg(
            tong_phut_lam_viec=("Số Phút Làm Việc", "sum")
        ).reset_index()
    else:
        time_staff = pd.DataFrame(columns=["Nhân Sự", "tong_phut_lam_viec"])

    cross_df = pd.merge(summary_staff, time_staff, on="Nhân Sự", how="left").fillna(0)
    cross_df["tong_phut_lam"] = cross_df["tong_phut_lam_viec"].astype(int)
    cross_df["diem_moi_phut"] = (cross_df["tong_diem_tich_luy"] / cross_df["tong_phut_lam"].replace(0, 1)).round(3)
    
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

    chart_col, text_col = st.columns([1, 1.2])
    
    with chart_col:
        st.markdown("##### 📥 Thao Tác Xuất Dữ Liệu")
        
        export_df = cross_display.copy() if 'cross_display' in locals() else summary_staff.copy()
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='BaoCao_HieuSuat')
        excel_data = output.getvalue()
        
        file_name_download = f"Bao_Cao_San_Luong_{start_date}_den_{end_date}.xlsx"
        
        st.download_button(
            label="💾 Tải File Về Máy (.xlsx)",
            data=excel_data,
            file_name=file_name_download,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        if st.button("☁️ Xuất File & Lưu Cloud", use_container_width=True, key="btn_export_cloud_real"):
            from database import supabase, safe_supabase_call
            if supabase is not None:
                try:
                    bucket_reports = "reports-storage"
                    unique_filename = f"baocao_{start_date}_{end_date}_{int(datetime.datetime.now().timestamp())}.xlsx"
                    
                    # 1. Đẩy file lên Cloud Storage
                    supabase.storage.from_(bucket_reports).upload(
                        path=unique_filename,
                        file=excel_data,
                        file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
                    )
                    
                    public_report_url = supabase.storage.from_(bucket_reports).get_public_url(unique_filename)
                    
                    # 2. Lưu trực tiếp vào bảng 'report_files' trên Supabase để đồng bộ sang Thư Mục Báo Cáo
                    def _insert_report_db(client):
                        return client.table("report_files").insert({
                            "name": unique_filename,
                            "url": public_report_url,
                            "is_deleted": False
                        }).execute()
                    
                    res_db = safe_supabase_call(_insert_report_db)
                    
                    if res_db:
                        st.success(f"✅ Đã lưu báo cáo lên Cloud và đồng bộ vào thư mục thành công! Tên file: `{unique_filename}`")
                    else:
                        st.warning(f"⚠️ Đã tải file lên Storage nhưng chưa ghi được vào bảng cơ sở dữ liệu. Tên file: `{unique_filename}`")
                        
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
