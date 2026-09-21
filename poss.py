import os
import sys
import streamlit as st
import pandas as pd
import datetime
import base64
import hashlib

# ==================== CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG GỐC ====================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

view_path = os.path.join(current_dir, "APP", "view")
if view_path not in sys.path:
    sys.path.insert(0, view_path)

os.environ["PYTHONPATH"] = current_dir

# ==================== IMPORT CÁC MODULE VÀ VIEW NGHIỆP VỤ ====================
from utils import (
    VN_TIMEZONE, 
    compress_image_to_base64, 
    calculate_exact_minutes, 
    hex_to_rgba
)
from database import (
    supabase, 
    is_supabase_connected, 
    init_db_data,
    get_staff_df_db, 
    get_staff_list_db, 
    get_rules_db,
    get_production_logs_db, 
    get_production_logs_by_date_range,
    get_total_production_count_db, 
    get_attendance_db,
    load_app_settings_db, 
    load_folders_db
)

import nhap_san_luong
import cham_cong
import bao_cao
import thu_muc_bao_cao
import dinh_muc_cong_viec
import thung_rac

# Cấu hình giao diện trang web Streamlit
st.set_page_config(page_title="Hệ Thống Quản Lý POSS", page_icon="🏭", layout="wide")

init_db_data()

# Hàm mã hóa mật khẩu bảo mật
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Hàm đo RAM tiến trình app thuần Python
def get_app_memory_usage():
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 ** 2)
        return f"{mem_mb:.1f} MB"
    except Exception:
        return "Ổn định"

# Hàm tính dung lượng Database và File Storage thực tế từ Supabase
def get_detailed_storage_usage():
    if supabase is None:
        return "0 MB / 500 MB", "0 MB / 1 GB"
    try:
        logs_count = len(supabase.table("production_logs").select("id", count="exact").execute().data)
        att_count = len(supabase.table("attendance").select("id", count="exact").execute().data)
        users_count = len(supabase.table("user_accounts").select("id", count="exact").execute().data)
        
        estimated_db_kb = (logs_count + att_count + users_count) * 2.5
        if estimated_db_kb > 1024:
            db_used_str = f"{estimated_db_kb / 1024:.2f} MB"
        else:
            db_used_str = f"{estimated_db_kb:.1f} KB"
        db_display = f"{db_used_str} / 500 MB"

        storage_bytes = 0
        try:
            files_img = supabase.storage.from_("production-images").list()
            files_rep = supabase.storage.from_("reports-storage").list()
            total_files = (files_img if files_img else []) + (files_rep if files_rep else [])
            for f in total_files:
                storage_bytes += f.get("metadata", {}).get("size", 0)
        except Exception:
            pass

        storage_mb = storage_bytes / (1024 * 1024)
        if storage_mb >= 1024:
            storage_display = f"{storage_mb / 1024:.2f} GB / 1 GB"
        else:
            storage_display = f"{storage_mb:.2f} MB / 1 GB"
            
        return db_display, storage_display
    except Exception:
        return "0 MB / 500 MB", "0 MB / 1 GB"

# ==================== KIỂM TRA ĐĂNG NHẬP SESSION ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_identifier" not in st.session_state:
    st.session_state.user_identifier = ""

params = st.query_params
if not st.session_state.logged_in and "auth_user" in params:
    st.session_state.logged_in = True
    st.session_state.user_identifier = params["auth_user"]

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.9); padding: 25px 30px 10px 30px; border-radius: 12px 12px 0 0; box-shadow: 0 8px 20px rgba(0,0,0,0.15); border: 1px solid #e2e8f0; border-bottom: none;">
            <h2 style="text-align: center; color: #ff4b4b; margin-bottom: 0px;">🔐 HỆ THỐNG POSS</h2>
            <p style="text-align: center; color: #64748b; font-size: 0.9rem; margin-top: 5px;">Đăng nhập hệ thống nội bộ</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='background: rgba(255, 255, 255, 0.9); padding: 20px 30px 30px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.15); border: 1px solid #e2e8f0; border-top: none;'>", unsafe_allow_html=True)
        
        tab_admin, tab_staff = st.tabs(["👑 Quản Trị Viên", "👤 Nhân Viên"])
        
        with tab_admin:
            with st.form("login_admin_form"):
                email_input = st.text_input("📧 Email Admin", placeholder="lamhoangsang169@gmail.com")
                password_admin = st.text_input("🔑 Mật khẩu", type="password", placeholder="Nhập mật khẩu...", key="pw_admin")
                remember_admin = st.checkbox("📌 Ghi nhớ đăng nhập", value=True, key="rem_admin")
                
                if st.form_submit_button("🚀 Đăng Nhập Quản Trị Viên", use_container_width=True):
                    if not email_input or not password_admin:
                        st.error("⚠️ Vui lòng nhập đầy đủ Email và Mật khẩu!")
                    elif supabase is None:
                        st.error("⚠️ Chưa kết nối được tới cơ sở dữ liệu!")
                    else:
                        try:
                            clean_email = email_input.strip()
                            res = supabase.auth.sign_in_with_password({
                                "email": clean_email,
                                "password": password_admin.strip()
                            })
                            if res and res.user:
                                st.session_state.logged_in = True
                                st.session_state.user_identifier = res.user.email
                                if remember_admin:
                                    st.query_params["auth_user"] = res.user.email
                                st.success("✅ Đăng nhập Admin thành công!")
                                st.rerun()
                            else:
                                st.error("❌ Email hoặc mật khẩu Admin không chính xác!")
                        except Exception as e:
                            st.error(f"❌ Lỗi đăng nhập: {e}")
            
        with tab_staff:
            with st.form("login_staff_form"):
                staff_list_opt = ["--- Chọn họ và tên ---"] + get_staff_list_db()
                login_name = st.selectbox("👤 Họ và tên nhân sự", staff_list_opt)
                password_staff = st.text_input("🔑 Mật khẩu", type="password", placeholder="Nhập mật khẩu...", key="pw_staff")
                remember_staff = st.checkbox("📌 Ghi nhớ đăng nhập", value=True, key="rem_staff")
                
                if st.form_submit_button("🚀 Đăng Nhập Nhân Viên", use_container_width=True):
                    if login_name == "--- Chọn họ và tên ---" or not password_staff:
                        st.error("⚠️ Vui lòng chọn họ tên và nhập mật khẩu!")
                    elif supabase is None:
                        st.error("⚠️ Chưa kết nối được tới cơ sở dữ liệu!")
                    else:
                        try:
                            res = supabase.table("user_accounts").select("*").eq("name", login_name).execute()
                            if res.data and len(res.data) > 0:
                                user_record = res.data[0]
                                if user_record["password_hash"] == hash_password(password_staff):
                                    st.session_state.logged_in = True
                                    st.session_state.user_identifier = login_name
                                    if remember_staff:
                                        st.query_params["auth_user"] = login_name
                                    st.success("✅ Đăng nhập thành công!")
                                    st.rerun()
                                else:
                                    st.error("❌ Mật khẩu không chính xác!")
                            else:
                                st.error("❌ Tài khoản chưa được Quản trị viên cấp mật khẩu!")
                        except Exception as e:
                            st.error(f"❌ Lỗi đăng nhập: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== PHÂN QUYỀN TÀI KHOẢN ====================
def get_user_permissions(identifier):
    default_perms = {"role": "Staff", "perm_input": False, "perm_report": False, "perm_attendance": True, "perm_rules": False}
    if not identifier or supabase is None:
        return default_perms
    clean_id = str(identifier).strip().lower()
    if clean_id == "lamhoangsang169@gmail.com":
        return {"role": "Admin", "perm_input": True, "perm_report": True, "perm_attendance": True, "perm_rules": True}
    try:
        res = supabase.table("user_accounts").select("*").eq("name", identifier).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            return {
                "role": row.get("role", "Staff"),
                "perm_input": row.get("perm_input", False),
                "perm_report": row.get("perm_report", False),
                "perm_attendance": row.get("perm_attendance", True),
                "perm_rules": row.get("perm_rules", False)
            }
    except Exception:
        pass
    return default_perms

user_perms = get_user_permissions(st.session_state.user_identifier)
current_user_role = user_perms["role"]

# ==================== KHỞI TẠO BIẾN TRẠNG THÁI SESSION ====================
st.session_state.staff_list = get_staff_list_db()
if "rules_df" not in st.session_state:
    try:
        st.session_state.rules_df = get_rules_db()
    except Exception:
        st.session_state.rules_df = pd.DataFrame()

st.session_state.folders = load_folders_db()
db_settings = load_app_settings_db()

if "primary_color" not in st.session_state: st.session_state.primary_color = "#ff4b4b"
if "bg_color" not in st.session_state: st.session_state.bg_color = "#ffffff"
if "sidebar_bg" not in st.session_state: st.session_state.sidebar_bg = "#f0f2f6"
if "sidebar_opacity" not in st.session_state: st.session_state.sidebar_opacity = 0.9
if "text_color" not in st.session_state: st.session_state.text_color = "#31333F"
if "avatar_base64" not in st.session_state: st.session_state.avatar_base64 = None
if "current_menu" not in st.session_state: st.session_state.current_menu = "1. Nhập Sản Lượng"

sidebar_rgba = hex_to_rgba(st.session_state.sidebar_bg, st.session_state.sidebar_opacity)

st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{ background-color: {sidebar_rgba} !important; backdrop-filter: blur(8px); }}
    [data-testid="stSidebar"] > div:first-child {{ display: flex; flex-direction: column; height: 100vh; overflow-y: auto !important; padding: 0px !important; }}
    .fixed-avatar-container {{ position: sticky; top: 0; z-index: 999999; background-color: {sidebar_rgba}; padding-top: 15px; padding-bottom: 15px; border-bottom: 2px solid {st.session_state.primary_color}; margin-bottom: 10px; text-align: center; flex-shrink: 0; backdrop-filter: blur(8px); }}
    .avatar-wrapper {{ position: relative; width: 140px; height: 140px; margin: 0 auto; }}
    .sidebar-scrollable-content {{ flex-grow: 1; padding-left: 1rem; padding-right: 1rem; padding-bottom: 50px; }}
</style>
""", unsafe_allow_html=True)

# ==================== THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR) ====================
with st.sidebar:
    st.markdown('<div class="fixed-avatar-container">', unsafe_allow_html=True)
    st.markdown(f'<div style="width:140px; height:140px; border-radius:50%; background:#cbd5e1; display:flex; align-items:center; justify-content:center; font-size:50px; border:3px solid {st.session_state.primary_color}; box-shadow:0 4px 10px rgba(0,0,0,0.3); margin: 0 auto;">👤</div>', unsafe_allow_html=True)

    role_badge = "👑 Quản Trị Viên (Admin)" if current_user_role == "Admin" else "👤 Nhân Viên"
    st.markdown(f"""
        <div style="text-align: center; margin-top: 10px;">
            <a href="mailto:{st.session_state.user_identifier}" style="color: #2563eb; text-decoration: none; font-weight: 500; font-size: 0.9rem;">
                📍 {st.session_state.user_identifier}
            </a>
            <div style="font-size: 0.85rem; color: #475569; margin-top: 4px;">
                🛡️ Phân quyền: <span style='color: {'#ff4b4b' if current_user_role=='Admin' else '#3b82f6'}; font-weight:bold;'>{role_badge}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Đăng Xuất", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_identifier = ""
        if "auth_user" in st.query_params: del st.query_params["auth_user"]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-scrollable-content">', unsafe_allow_html=True)
    
    if st.button("🔄 Cập Nhập", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    if st.button("⏱️ Chấm Công Ca Làm Việc", use_container_width=True):
        st.session_state.current_menu = "⏱️ Chấm Công Ca Làm Việc"
        st.rerun()

    st.markdown("---")
    st.markdown("### 📂 CHỨC NĂNG HỆ THỐNG")
    
    # Menu chọn danh mục nghiệp vụ
    menu_options = [
        "1. Nhập Sản Lượng",
        "📊 Báo Cáo & Biểu Đồ",
        "📂 Thư Mục Báo Cáo",
        "📋 Định Mức Công Việc",
        "🗑️ Thùng Rác"
    ]
    
    chosen_menu = st.radio("📌 Danh Mục Nghiệp Vụ", menu_options, label_visibility="collapsed")
    if chosen_menu:
        st.session_state.current_menu = chosen_menu

    # Các mục cấu hình hệ thống (Admin)
    if current_user_role == "Admin":
        st.markdown("---")
        st.markdown("### ⚙️ Cấu Hình Hệ Thống\n(Admin)")
        if st.button("📁 Quản Lý Thư Mục & Menu", use_container_width=True):
            st.session_state.current_menu = "📁 Quản Lý Thư Mục & Menu"
        if st.button("🎨 Cài Đặt Giao Diện", use_container_width=True):
            st.session_state.current_menu = "🎨 Cài Đặt Giao Diện"
        if st.button("🛡️ Quản Lý Tài Khoản & Phân Quyền", use_container_width=True):
            st.session_state.current_menu = "🛡️ Quản Lý Tài Khoản & Phân Quyền"
        if st.button("🧹 Làm Sạch & Tối Ưu Dữ Liệu", use_container_width=True):
            st.session_state.current_menu = "🧹 Làm Sạch Dữ Liệu"

    st.markdown("---")
    if is_supabase_connected:
        st.markdown('<div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9rem; font-weight: bold; color: #155724; margin-bottom: 8px;">🟢 Đã kết nối Supabase</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9rem; font-weight: bold; color: #721c24; margin-bottom: 8px;">🔴 Chưa kết nối Supabase</div>', unsafe_allow_html=True)

    ram_usage_str = get_app_memory_usage()
    db_usage_str, storage_usage_str = get_detailed_storage_usage()
    total_db_count = get_total_production_count_db()

    st.markdown(f'<div style="background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 8px; border-radius: 8px; text-align: center; font-size: 0.85rem; font-weight: bold; color: #721c24; margin-bottom: 6px;">🧠 RAM App: {ram_usage_str}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="background-color: #fff3cd; border: 1px solid #ffeeba; padding: 8px; border-radius: 8px; text-align: center; font-size: 0.85rem; font-weight: bold; color: #856404; margin-bottom: 6px;">💾 Database: {db_usage_str}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 8px; border-radius: 8px; text-align: center; font-size: 0.85rem; font-weight: bold; color: #0c5460; margin-bottom: 6px;">🗂️ File Storage: {storage_usage_str}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="background-color: #cce5ff; border: 1px solid #b8daff; padding: 8px; border-radius: 8px; text-align: center; font-size: 0.85rem; font-weight: bold; color: #004085; margin-bottom: 6px;">📊 Tổng bản ghi: {total_db_count}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== ĐIỀU HƯỚNG NỘI DUNG CHÍNH (MAIN CONTENT) ====================
@st.fragment
def render_main_content(current_menu_name):
    if current_menu_name == "1. Nhập Sản Lượng":
        nhap_san_luong.render_nhap_san_luong(current_menu_name, current_user_role, user_perms)
    elif current_menu_name == "⏱️ Chấm Công Ca Làm Việc":
        cham_cong.render_cham_cong(current_menu_name, current_user_role)
    elif current_menu_name == "📊 Báo Cáo & Biểu Đồ":
        bao_cao.render_bao_cao(current_menu_name)
    elif current_menu_name == "📂 Thư Mục Báo Cáo":
        thu_muc_bao_cao.render_thu_muc_bao_cao(current_menu_name)
    elif current_menu_name == "📋 Định Mức Công Việc":
        dinh_muc_cong_viec.render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms)
    elif current_menu_name == "🗑️ Thùng Rác":
        thung_rac.render_thung_rac(current_menu_name, current_user_role)
    else:
        st.subheader(current_menu_name)
        st.info(f"Đang hiển thị nội dung cho mục: {current_menu_name}")

render_main_content(st.session_state.current_menu)
