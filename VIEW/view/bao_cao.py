import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from database import (
    get_production_logs_by_date_range,
    get_attendance_db,
    upload_report_to_storage,
    save_export_report_db
)

def render_bao_cao(current_menu_name):
    col_rep_h1, col_rep_h2 = st.columns([3, 1])
    with col_rep_h1:
        st.header(current_menu_name)
    with col_rep_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_report"):
            st.cache_data.clear()
            st.rerun()
    
    col_date1, col_date2 = st.columns(2)
    default_start = datetime.date.today().replace(day=1)
    default_end = datetime.date.today()
    
    with col_date1:
        report_start_date = st.date_input("Từ ngày", default_start)
    with col_date2:
        report_end_date = st.date_input("Đến ngày", default_end)

    all_staff_current = st.session_state.staff_list
    input_df = get_production_logs_by_date_range(report_start_date, report_end_date)
    
    if not input_df.empty:
        summary = input_df.groupby("Nhân Sự").agg(Tổng_Số_Lượng=("Số Lượng", "sum"), Tổng_Điểm=("Tổng Điểm", "sum")).reset_index()
    else:
        summary = pd.DataFrame(columns=["Nhân Sự", "Tổng_Số_Lượng", "Tổng_Điểm"])

    if not summary.empty:
        summary = summary[summary["Nhân Sự"].isin(all_staff_current)]
        summary = summary[summary["Tổng_Điểm"] > 0]
    
    total_all_points = summary["Tổng_Điểm"].sum() if not summary.empty else 0
    if not summary.empty:
        summary["Tỷ_Lệ_Đóng_Góp"] = summary["Tổng_Điểm"].apply(lambda x: (x / total_all_points) if total_all_points > 0 else 0)
        summary["Xếp_Loại"] = summary["Tổng_Điểm"].apply(lambda pts: "Xuất Sắc" if pts >= 700 else ("Đạt" if pts >= 400 else "Cần Cố Gắn"))
        summary_display = summary[["Nhân Sự", "Tổng_Số_Lượng", "Tổng_Điểm", "Tỷ_Lệ_Đóng_Góp", "Xếp_Loại"]].copy()
        summary_display.columns = ["Nhân Sự", "Số Lượng Thực Tế", "Tổng Điểm", "Tỷ Lệ Đóng Góp", "Xếp Loại"]
    else:
        summary_display = pd.DataFrame(columns=["Nhân Sự", "Số Lượng Thực Tế", "Tổng Điểm", "Tỷ Lệ Đóng Góp", "Xếp Loại"])
    
    st.subheader("Bảng Tổng Kết Theo Nhân Sự")
    if not summary_display.empty:
        st.dataframe(summary_display.style.format({"Số Lượng Thực Tế": "{:,.0f}", "Tổng Điểm": "{:,.1f}", "Tỷ Lệ Đóng Góp": "{:.2%}"}), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu sản lượng trong khoảng thời gian này.")

    st.markdown("---")
    st.subheader("⚖️ Bảng Đối Chiếu Thời Gian Làm Việc & Sản Lượng")
    att_df = get_attendance_db()
    att_summary = att_df.groupby("Nhân Sự")["Số Phút Làm Việc"].sum().reset_index() if not att_df.empty else pd.DataFrame(columns=["Nhân Sự", "Tổng Phút Làm Việc"])
    att_summary.columns = ["Nhân Sự", "Tổng Phút Làm Việc"]
        
    if not summary.empty or not att_summary.empty:
        comparison_df = pd.merge(summary, att_summary, on="Nhân Sự", how="outer").fillna(0)
        comparison_df = comparison_df[comparison_df["Nhân Sự"].isin(all_staff_current)]
        comparison_df = comparison_df[(comparison_df["Tổng_Điểm"] > 0) | (comparison_df["Tổng Phút Làm Việc"] > 0)]
        
        if not comparison_df.empty:
            comparison_df = comparison_df.sort_values(by="Tổng_Điểm", ascending=False).reset_index(drop=True)
            rank_badges = []
            current_rank_num = 1
            for idx in range(len(comparison_df)):
                if idx > 0 and comparison_df.loc[idx, "Tổng_Điểm"] == comparison_df.loc[idx - 1, "Tổng_Điểm"]:
                    rank_badges.append(rank_badges[-1])
                else:
                    current_rank_num = current_rank_num + 1 if idx > 0 else 1
                    if current_rank_num == 1: rank_badges.append("🥇 Hạng 1")
                    elif current_rank_num == 2: rank_badges.append("🥈 Hạng 2")
                    elif current_rank_num == 3: rank_badges.append("🥉 Hạng 3")
                    else: rank_badges.append(f"Top {current_rank_num}")
            comparison_df.insert(0, "Xếp Hạng", rank_badges)
            
            total_minutes_all = comparison_df["Tổng Phút Làm Việc"].sum()
            comparison_df["Tỷ_Lệ_Thời_Gian"] = comparison_df["Tổng Phút Làm Việc"].apply(lambda x: (x / total_minutes_all) if total_minutes_all > 0 else 0)
            comparison_df["Tỷ_Lệ_Đóng_Góp"] = comparison_df["Tổng_Điểm"].apply(lambda x: (x / total_pts_all) if (total_pts_all := comparison_df["Tổng_Điểm"].sum()) > 0 else 0)
            comparison_df["Chênh_Lệch_%"] = comparison_df["Tỷ_Lệ_Đóng_Góp"] - comparison_df["Tỷ_Lệ_Thời_Gian"]
            comparison_df["Số_Ngày_Làm_Việc"] = comparison_df["Tổng Phút Làm Việc"] / 480.0
            
            comparison_table = comparison_df[["Xếp Hạng", "Nhân Sự", "Tổng Phút Làm Việc", "Số_Ngày_Làm_Việc", "Tỷ_Lệ_Thời_Gian", "Tổng_Điểm", "Tỷ_Lệ_Đóng_Góp", "Chênh_Lệch_%"]].copy()
            comparison_table.columns = ["Xếp Hạng", "Nhân Sự", "Tổng Thời Gian (Phút)", "Số ngày làm việc", "Tỷ Lệ Thời Gian (%)", "Tổng Điểm", "Tỷ Lệ Sản Lượng (%)", "Chênh Lệch"]
            
            st.dataframe(comparison_table.style.format({
                "Tổng Thời Gian (Phút)": "{:,.0f}", "Số ngày làm việc": "{:,.2f}", "Tỷ Lệ Thời Gian (%)": "{:.2%}",
                "Tổng Điểm": "{:,.1f}", "Tỷ Lệ Sản Lượng (%)": "{:.2%}", "Chênh Lệch": "{:+.2%}"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dữ liệu đối chiếu.")

    st.markdown("---")
    if not summary.empty and total_all_points > 0:
        export_csv_df = summary_display.copy()
        if not input_df.empty:
            task_details = []
            for staff_name in export_csv_df["Nhân Sự"]:
                staff_logs = input_df[input_df["Nhân Sự"] == staff_name]
                if not staff_logs.empty:
                    grouped_tasks = staff_logs.groupby("Hạng Mục Công Việc")["Số Lượng"].sum()
                    task_details.append(" | ".join([f"{t}: {q}" for t, q in grouped_tasks.items()]))
                else:
                    task_details.append("")
            export_csv_df["Chi Tiết Hạng Mục"] = task_details

        exp_col1, exp_col2 = st.columns([1, 3])
        with exp_col1:
            csv_bytes = export_csv_df.to_csv(index=False).encode('utf-8-sig')
            file_name_val = f"bao_cao_san_luong_{report_start_date}_den_{report_end_date}.csv"
            if st.button("📥 Xuất File & Lưu Cloud", use_container_width=True):
                file_url = upload_report_to_storage(file_name_val, csv_bytes)
                if file_url: save_export_report_db(file_name_val, file_url)
            st.download_button("💾 Tải File Về Máy", data=csv_bytes, file_name=file_name_val, mime="text/csv", use_container_width=True)

        chart_col1, chart_col2 = st.columns([0.45, 1.35])
        with chart_col1:
            fig_plotly = px.pie(summary, names="Nhân Sự", values="Tổng_Điểm", hole=0, color_discrete_sequence=st.session_state.chart_colors)
            fig_plotly.update_traces(textposition='inside', textinfo='percent', textfont=dict(size=20, color='white', family='Arial Black'), pull=[0.03] * len(summary))
            fig_plotly.update_layout(margin=dict(t=30, b=30, l=30, r=30), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, height=320)
            st.plotly_chart(fig_plotly, use_container_width=True)
            
        with chart_col2:
            st.markdown("### 📌 Chi Tiết Điểm Số & Tỷ Lệ")
            for idx, row in summary.iterrows():
                staff_name = row["Nhân Sự"]
                short_name = staff_name.split()[-1] if len(staff_name.split()) > 1 else staff_name
                pts, pct = row["Tổng_Điểm"], row["Tỷ_Lệ_Đóng_Góp"] * 100
                color_code = st.session_state.chart_colors[idx % len(st.session_state.chart_colors)]
                st.markdown(f'<div style="background-color: #f8fafc; padding: 6px 10px; border-radius: 6px; margin-bottom: 6px; border-left: 4px solid {color_code}; border: 1px solid #e2e8f0; font-size: 0.85rem;"><span style="display:inline-block; width:7px; height:7px; background-color:{color_code}; border-radius:2px; margin-right:4px;"></span><b>{short_name}</b>: {pts:,.1f} điểm (<b style="color: {color_code};">{pct:.1f}%</b>)</div>', unsafe_allow_html=True)
