import os
import sys
import streamlit as st
import pandas as pd
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
    cleanup_orphan_storage_files,
    delete_storage_files_by_date_range
)

from storage_manager import upload_image
from db_manager import get_database_connection

# Import trực tiếp tệp nhap_san_luong ở thư mục gốc
import nhap_san_luong

import cham_cong
import bao_cao
import thu_muc_bao_cao  
import dinh_muc_cong_viec
import quan_ly_loi
import thung_rac

st.set_page_config(
    page_title="Hệ Thống Quản Lý POSS", 
    page_icon="logo.png", 
    layout="wide"
)

init_db_data()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_app_memory_usage():
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 ** 2)
        return f"{mem_mb:.1f} MB"
    except Exception:
        return "Ổn định"

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
            files_img = supabase.storage.from_("production_images").list()
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

def save_staff_list_db(edited_df):
    if supabase is None:
        return
    try:
        res_old = supabase.table("staff").select("id, name").execute()
        old_staffs = {row["id"]: row["name"] for row in res_old.data} if res_old.data else {}
        old_ids = list(old_staffs.keys())
        
        current_ids_in_editor = []
        for _, row in edited_df.iterrows():
            name = str(row.get("name", "")).strip()
            row_id = row.get("id")
            if not name or name.lower() in ["nan", "none"]:
                continue
            if pd.notna(row_id) and int(row_id) in old_ids:
                supabase.table("staff").update({"name": name}).eq("id", int(row_id)).execute()
                current_ids_in_editor.append(int(row_id))
            else:
                res_ins = supabase.table("staff").insert({"name": name}).execute()
                if res_ins.data:
                    current_ids_in_editor.append(res_ins.data[0]["id"])
                    
        ids_to_delete = [oid for oid in old_ids if oid not in current_ids_in_editor]
        for del_id in ids_to_delete:
            supabase.table("staff").delete().eq("id", del_id).execute()
            
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Lỗi khi lưu nhân sự: {e}")

def save_app_settings_db(settings_dict):
    if supabase is None:
        return
    try:
        payload = {"id": 1, **settings_dict}
        supabase.table("app_settings").upsert(payload).execute()
        load_app_settings_db.clear()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Lỗi lưu cấu hình: {e}")

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
                        st.error("⚠ Chưa kết nối được tới cơ sở dữ liệu!")
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

st.session_state.staff_list = get_staff_list_db()
if "rules_df" not in st.session_state:
    try:
        st.session_state.rules_df = get_rules_db()
    except Exception:
        st.session_state.rules_df = pd.DataFrame()

db_settings = load_app_settings_db()

if not db_settings:
    db_settings = {
        "primary_color": "#ff4b4b",
        "bg_color": "#ffffff",
        "sidebar_bg": "#f0f2f6",
        "sidebar_opacity": 0.9,
        "text_color": "#31333F"
    }
    try:
        save_app_settings_db(db_settings)
    except Exception:
        pass

st.session_state.primary_color = db_settings.get("primary_color", "#ff4b4b")
st.session_state.bg_color = db_settings.get("bg_color", "#ffffff")
st.session_state.sidebar_bg = db_settings.get("sidebar_bg", "#f0f2f6")

val_opacity = db_settings.get("sidebar_opacity", 0.9)
try:
    st.session_state.sidebar_opacity = float(val_opacity) if val_opacity is not None and str(val_opacity).strip() != "" else 0.9
except Exception:
    st.session_state.sidebar_opacity = 0.9

st.session_state.text_color = db_settings.get("text_color", "#31333F")
st.session_state.bg_image_base64 = db_settings.get("bg_image_base64", None)
st.session_state.avatar_base64 = db_settings.get("avatar_base64", None)

if "current_menu" not in st.session_
