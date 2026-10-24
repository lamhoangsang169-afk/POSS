import os
import sys
import streamlit as st
import pandas as pd
import datetime
import base64
import hashlib
import requests
import importlib.util

# ==================== CẤU HÌNH ĐƯỜNG DẪN & NẠP MODULE AN TOÀN ====================
current_dir = os.path.dirname(os.path.abspath(__file__))
view_dir = os.path.join(current_dir, "APP", "view")

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if view_dir not in sys.path:
    sys.path.insert(0, view_dir)

os.environ["PYTHONPATH"] = current_dir

def load_view_module(module_name):
    file_path = os.path.join(view_dir, f"{module_name}.py")
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
            return mod
    except Exception as e:
        print(f"Không thể nạp module {module_name} từ {file_path}: {e}")
    return None

# Nạp chính xác các tệp từ thư mục APP/view/
nhap_san_luong = load_view_module("nhap_san_luong")
cham_cong = load_view_module("cham_cong")
bao_cao = load_view_module("bao_cao")
thu_muc_bao_cao = load_view_module("thu_muc_bao_cao")
dinh_muc_cong_viec = load_view_module("dinh_muc_cong_viec")
quan_ly_loi = load_view_module("quan_ly_loi")
thung_rac = load_view_module("thung_rac")

from utils import (
    VN_TIMEZONE, 
    compress_image_to_base64, 
    calculate_exact_minutes, 
    hex_to_rgba
)
from database import (
    supabase, 
    is_supabase_connected, 
    safe_supabase_call,
    init_db_data,
    get_staff_df_db, 
    get_staff_list_db, 
    get_rules_db,
    get_production_logs_db, 
    get_production_logs_by_date_range,
    get_total_production_count_db, 
    get_attendance_db,
    load_app_settings_db,
    save_app_settings_db,
    cleanup_orphan_storage_files,
    delete_storage_files_by_date_range
)

from storage_manager import upload_image
from db_manager import get_database_connection

# Cấu hình giao diện trang web Streamlit
st.set_page_config(
    page_title="Hệ Thống Quản Lý POSS", 
    page_icon="logo.png", 
    layout="wide"
)

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

# Hàm tính dung lượng Database, Storage và Băng thông (Egress) Dynamic
def get_detailed_storage_usage():
    if supabase is None:
        return "0 MB / 500 MB", "0 MB / 1 GB", 0.0

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

        project_ref = st.secrets.get("SUPABASE_PROJECT_REF", "")
        api_token = st.secrets.get("SUPABASE_ACCESS_TOKEN", "")
        bandwidth_used_gb = 0.0

        if project_ref and api_token:
            try:
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                }
                res = requests.get(f"https://api.supabase.com/v1/projects/{project_ref}/usage", headers=headers, timeout=3.0)
                if res.status_code == 200:
                    egress_bytes = res.json().get("egress_bytes", 0)
                    bandwidth_used_gb = egress_bytes / (1024 ** 3)
            except Exception:
                pass

        if bandwidth_used_gb == 0.0 and storage_bytes > 0:
            estimated_read_factor = 3.5
            bandwidth_used_gb = round((storage_bytes * estimated_read_factor) / (1024 ** 3), 3)

        return db_display, storage_display, bandwidth_used_gb

    except Exception:
        return "0 MB / 500 MB", "0 MB / 1 GB", 0.0

# ==================== CÁC HÀM CRUD BỔ SUNG ====================
def save_staff_list_db(edited_df):
    if supabase is None:
        return
    try:
        res_old = safe_supabase_call(lambda client: client.table("user_accounts").select("id, name, role").execute())
        old_staffs = {row["id"]: row for row in res_old.data} if res_old and res_old.data else {}
        old_ids = list(old_staffs.keys())
        
        current_ids_in_editor = []
        for _, row in edited_df.iterrows():
            name = str(row.get("name", "")).strip()
            row_id = row.get("id")
            role_val = str(row.get("role", "Staff")).strip() if pd.notna(row.get("role")) and str(row.get("role")).strip() else "Staff"
            
            if not name or name.lower() in ["nan", "none"]:
                continue
                
            if pd.notna(row_id) and int(row_id) in old_ids:
                uid = int(row_id)
                old_name = old_staffs[uid].get("name", "")
                update_payload = {"name": name}
                if "role" in edited_df.columns and pd.notna(row.get("role")):
                    update_payload["role"] = role_val
                safe_supabase_call(lambda client, u=uid, p=update_payload: client.table("user_accounts").update(p).eq("id", u).execute())
                
                if old_name and old_name != name:
                    try:
                        supabase.table("staff").update({"name": name}).eq("name", old_name).execute()
                    except Exception:
                        pass
                current_ids_in_editor.append(uid)
            else:
                new_user_payload = {
                    "name": name,
                    "password_hash": hash_password("123456"),
                    "role": role_val if role_val in ["Admin", "Manager", "Staff"] else "Staff",
                    "perm_input": True if role_val == "Admin" else False,
                    "perm_report": True if role_val == "Admin" else False,
                    "perm_attendance": True,
                    "perm_rules": True if role_val == "Admin" else False
                }
                res_ins = safe_supabase_call(lambda client, p=new_user_payload: client.table("user_accounts").insert(p).execute())
                if res_ins and res_ins.data:
                    current_ids_in_editor.append(res_ins.data[0]["id"])
                try:
                    supabase.table("staff").insert({"name": name}).execute()
                except Exception:
                    pass
                    
        ids_to_delete = [oid for oid in old_ids if oid not in current_ids_in_editor]
        for del_id in ids_to_delete:
            del_name = old_staffs[del_id].get("name", "")
            safe_supabase_call(lambda client, d=del_id: client.table("user_accounts").delete().eq("id", d).execute())
            if del_name:
                try:
                    supabase.table("staff").delete().eq("name", del_name).execute()
                except Exception:
                    pass
            
        get_staff_df_db.clear()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Lỗi khi lưu nhân sự: {e}")

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

# ==================== PHÂN QUYỀN TÀI KHOẢN ====================
def get_user_permissions(identifier):
    default_perms = {"role": "Staff", "perm_input": False, "perm_report": False, "perm_attendance": True, "perm_rules": False}
    if not identifier or supabase is None:
        return default_perms
    clean_id = str(identifier).strip().lower()
    if clean_id == "lamhoangsang169@gmail.com":
        return {"role": "Admin", "perm_input": True, "perm_report": True, "perm_attendance": True, "perm_rules": True}
    try:
        res = safe_supabase_call(lambda client: client.table("user_accounts").select("*").eq("name", identifier).execute())
        if res and res.data and len(res.data) > 0:
            row = res.data[0]
            return {
                "role": row.get("role", "Staff") if pd.notna(row.get("role")) else "Staff",
                "perm_input": bool(row.get("perm_input")) if pd.notna(row.get("perm_input")) else False,
                "perm_report": bool(row.get("perm_report")) if pd.notna(row.get("perm_report")) else False,
                "perm_attendance": bool(
