# view/bao_cao.py
import streamlit as st
import pandas as pd
import datetime
import io
import plotly.graph_objects as go

# Sử dụng import trực tiếp từ database và utils (đã được cấu hình PYTHONPATH ở poss.py)
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
    
    # (Phần code bên dưới giữ nguyên hoàn toàn như cũ của bạn từ dòng xử lý ngày tháng trở đi)
