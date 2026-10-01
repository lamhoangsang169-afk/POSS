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
    cleanup_orphan_storage_files
)

import nhap_san_luong
import cham_cong
import bao_cao
import thu_muc_bao_cao  
import dinh_muc_cong_viec
import quan_ly_loi
import thung_rac

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

# ==================== CÁC HÀM CRUD BỔ SUNG ====================
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

# ==================== KHỞI TẠO & ĐỒNG BỘ CẤU HÌNH TỪ DATABASE ====================
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

if "current_menu" not in st.session_state: 
    st.session_state.current_menu = "1. Nhập Sản Lượng"

bg_style = f"background-color: {st.session_state.bg_color};"
if st.session_state.bg_image_base64:
    bg_style = f"background-image: url(data:image/jpeg;base64,{st.session_state.bg_image_base64}); background-size: cover; background-repeat: no-repeat; background-position: center; background-attachment: fixed;"

sidebar_rgba = hex_to_rgba(st.session_state.sidebar_bg, st.session_state.sidebar_opacity)

st.markdown(f"""
<style>
    .stApp {{ 
        {bg_style} 
        color: {st.session_state.text_color} !important; 
        -webkit-print-color-adjust: exact;
    }}
    h1, h2, h3, h4, h5, h6, p, span, label, div {{
        color: {st.session_state.text_color} !important;
    }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_rgba} !important; backdrop-filter: blur(8px); }}
    [data-testid="stSidebar"] > div:first-child {{ display: flex; flex-direction: column; height: 100vh; overflow-y: auto !important; padding: 0px !important; }}
    .fixed-avatar-container {{ position: sticky; top: 0; z-index: 999999; background-color: {sidebar_rgba}; padding-top: 15px; padding-bottom: 15px; border-bottom: 2px solid {st.session_state.primary_color}; margin-bottom: 10px; text-align: center; flex-shrink: 0; backdrop-filter: blur(8px); }}
    .avatar-wrapper {{ position: relative; width: 140px; height: 140px; margin: 0 auto; }}
    .sidebar-scrollable-content {{ flex-grow: 1; padding-left: 1rem; padding-right: 1rem; padding-bottom: 50px; }}
</style>
""", unsafe_allow_html=True)

# ==================== ĐỊNH NGHĨA HÀM ĐIỀU HƯỚNG NỘI DUNG CHÍNH ====================
def render_main_content(current_menu_name):
    menu_lower = current_menu_name.lower()
    
    if "nhập sản lượng" in menu_lower:
        nhap_san_luong.render_nhap_san_luong(current_menu_name, current_user_role, user_perms)
    elif "chấm công" in menu_lower:
        cham_cong.render_cham_cong(current_menu_name, current_user_role)
    elif "thư mục báo cáo" in menu_lower:
        thu_muc_bao_cao.render_thu_muc_bao_cao(current_menu_name)
    elif "báo cáo" in menu_lower or "thống kê" in menu_lower:
        bao_cao.render_bao_cao(current_menu_name)
    elif "định mức" in menu_lower or "tham chiếu" in menu_lower:
        dinh_muc_cong_viec.render_dinh_muc_cong_viec(current_menu_name, current_user_role, user_perms)
    elif "quản lý lỗi" in menu_lower or "quan ly loi" in menu_lower or "lỗi" in menu_lower:
        quan_ly_loi.render_quan_ly_loi(current_menu_name)
    elif "thùng rác" in menu_lower:
        thung_rac.render_thung_rac(current_menu_name, current_user_role)

    # ==================== CÀI ĐẶT GIAO DIỆN ====================
    elif current_menu_name == "🎨 Cài Đặt Giao Diện":
        col_ui_h1, col_ui_h2 = st.columns([3, 1])
        with col_ui_h1:
            st.header("Cài Đặt Giao Diện & Nhân Sự")
        with col_ui_h2:
            if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_ui"):
                st.cache_data.clear()
                st.rerun()

        if current_user_role != "Admin":
            st.warning("🔒 Chỉ Quản trị viên mới được phép cài đặt giao diện và danh sách nhân sự!")
        else:
            st.markdown("### 🎨 Tùy Chỉnh Giao Diện Trực Tiếp")
            
            with st.form("settings_form"):
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    picker_bg = st.color_picker("Màu nền ứng dụng", value=st.session_state.get("bg_color", "#ffffff"))
                    picker_text = st.color_picker("Màu chữ", value=st.session_state.get("text_color", "#31333F"))
                with c_col2:
                    picker_primary = st.color_picker("Màu chủ đạo", value=st.session_state.get("primary_color", "#ff4b4b"))
                    picker_sidebar = st.color_picker("Màu nền sidebar", value=st.session_state.get("sidebar_bg", "#f0f2f6"))
                    
                slider_opacity = st.slider("Độ mờ sidebar", 0.1, 1.0, float(st.session_state.get("sidebar_opacity", 0.9)), 0.05)
                bg_file_upload = st.file_uploader("🖼️ Tải lên hình nền ứng dụng", type=["png", "jpg", "jpeg"], key="bg_uploader_direct")
                
                submitted_settings = st.form_submit_button("💾 Lưu Cài Đặt Giao Diện", use_container_width=True, type="primary")
                if submitted_settings:
                    bg_base64_to_save = st.session_state.get("bg_image_base64")
                    if bg_file_upload is not None:
                        compressed_bg = compress_image_to_base64(bg_file_upload, max_size=(1920, 1080), quality=80)
                        if compressed_bg:
                            bg_base64_to_save = compressed_bg
                            st.session_state.bg_image_base64 = compressed_bg

                    st.session_state.bg_color = picker_bg
                    st.session_state.text_color = picker_text
                    st.session_state.primary_color = picker_primary
                    st.session_state.sidebar_bg = picker_sidebar
                    st.session_state.sidebar_opacity = slider_opacity

                    save_app_settings_db({
                        "primary_color": picker_primary, 
                        "bg_color": picker_bg,
                        "sidebar_bg": picker_sidebar, 
                        "sidebar_opacity": slider_opacity,
                        "text_color": picker_text, 
                        "bg_image_base64": bg_base64_to_save,
                        "avatar_base64": st.session_state.get("avatar_base64")
                    })
                    st.success("✅ Đã lưu cài đặt giao diện vĩnh viễn lên cơ sở dữ liệu thành công!")
                    st.rerun()

            st.markdown("---")
            st.subheader("👥 Quản Lý Danh Sách Nhân Sự")
            
            try:
                staff_df = get_staff_df_db()
                if staff_df is None or staff_df.empty:
                    staff_df = pd.DataFrame(columns=["id", "name"])
            except Exception as e:
                st.error(f"Lỗi tải dữ liệu nhân sự: {e}")
                staff_df = pd.DataFrame(columns=["id", "name"])
            
            with st.form("staff_form"):
                edited_staff = st.data_editor(
                    staff_df, 
                    num_rows="dynamic", 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "name": st.column_config.TextColumn("Họ và tên nhân sự", required=True)
                    }
                )
                
                submitted_staff = st.form_submit_button("💾 Lưu Nhân Sự", use_container_width=True)
                if submitted_staff:
                    save_staff_list_db(edited_staff)
                    st.cache_data.clear()
                    st.session_state.staff_list = get_staff_list_db()
                    st.success("✅ Đã cập nhật danh sách nhân sự thành công!")
                    st.rerun()

    # ==================== QUẢN LÝ TÀI KHOẢN & PHÂN QUYỀN ====================
    elif current_menu_name == "🛡️ Quản Lý Tài Khoản & Phân Quyền":
        col_mr_h1, col_mr_h2 = st.columns([3, 1])
        with col_mr_h1:
            st.header("🛡 Quản Lý Tài Khoản & Phân Quyền Chi Tiết")
        with col_mr_h2:
            if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_mr"):
                st.cache_data.clear()
                st.rerun()

        if current_user_role != "Admin":
            st.warning("🔒 Chỉ Quản trị viên mới có quyền quản lý tài khoản và phân quyền!")
        else:
            st.markdown("Tại đây bạn có thể tạo tài khoản, đổi mật khẩu, xóa tài khoản và cấp quyền trực tiếp cho từng nhân sự:")
            
            with st.expander("➕ Tạo Tài Khoản Nhân Sự Mới", expanded=False):
                with st.form("create_new_account_form"):
                    c_new1, c_new2, c_new3 = st.columns(3)
                    with c_new1:
                        new_acc_name = st.text_input("Họ và tên nhân sự", placeholder="Nhập tên nhân sự...")
                    with c_new2:
                        new_acc_pass = st.text_input("Mật khẩu tài khoản", type="password", placeholder="Nhập mật khẩu (>=6 ký tự)...")
                    with c_new3:
                        new_acc_role = st.selectbox("Vai trò", options=["Staff", "Manager", "Admin"])
                    
                    submitted_new_acc = st.form_submit_button("🚀 Tạo Tài Khoản Mới", use_container_width=True)
                    if submitted_new_acc:
                        if not new_acc_name.strip() or not new_acc_pass:
                            st.error("⚠️ Vui lòng nhập đầy đủ tên nhân sự và mật khẩu!")
                        elif len(new_acc_pass) < 6:
                            st.error("⚠️ Mật khẩu phải có ít nhất 6 ký tự!")
                        else:
                            try:
                                check_exist = supabase.table("user_accounts").select("*").eq("name", new_acc_name.strip()).execute()
                                if check_exist.data and len(check_exist.data) > 0:
                                    st.error(f"❌ Tài khoản hoặc nhân sự '{new_acc_name.strip()}' đã tồn tại trong hệ thống!")
                                else:
                                    supabase.table("user_accounts").insert({
                                        "name": new_acc_name.strip(),
                                        "password_hash": hash_password(new_acc_pass),
                                        "role": new_acc_role,
                                        "perm_input": True if new_acc_role == "Admin" else False,
                                        "perm_report": True if new_acc_role == "Admin" else False,
                                        "perm_attendance": True,
                                        "perm_rules": True if new_acc_role == "Admin" else False
                                    }).execute()
                                    st.success(f"✅ Đã tạo thành công tài khoản cho **{new_acc_name.strip()}**!")
                                    st.cache_data.clear()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Lỗi khi tạo tài khoản: {e}")

            try:
                staff_list_names = get_staff_list_db()
                for s_name in staff_list_names:
                    chk = supabase.table("user_accounts").select("*").eq("name", s_name).execute() if supabase else None
                    if chk and not chk.data:
                        supabase.table("user_accounts").insert({
                            "name": s_name,
                            "password_hash": hash_password("123456"),
                            "role": "Staff",
                            "perm_input": False,
                            "perm_report": False,
                            "perm_attendance": True,
                            "perm_rules": False
                        }).execute()

                res_roles = supabase.table("user_accounts").select("*").execute() if supabase else None
                if res_roles and res_roles.data:
                    roles_df = pd.DataFrame(res_roles.data)
                    
                    with st.form("manage_accounts_form"):
                        edited_roles_df = st.data_editor(
                            roles_df,
                            column_config={
                                "id": st.column_config.NumberColumn("ID", disabled=True),
                                "name": st.column_config.TextColumn("Họ và tên nhân sự", disabled=True),
                                "password_hash": None,
                                "role": st.column_config.SelectboxColumn("Vai trò", options=["Admin", "Manager", "Staff"], required=True),
                                "perm_input": st.column_config.CheckboxColumn("Nhập sản lượng"),
                                "perm_report": st.column_config.CheckboxColumn("Xem báo cáo"),
                                "perm_attendance": st.column_config.CheckboxColumn("Chấm công"),
                                "perm_rules": st.column_config.CheckboxColumn("Sửa định mức")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        if st.form_submit_button("💾 Lưu Cập Nhật Quyền Hạn Hàng Loạt", use_container_width=True):
                            for _, row in edited_roles_df.iterrows():
                                r_id = row["id"]
                                supabase.table("user_accounts").update({
                                    "role": row["role"],
                                    "perm_input": bool(row["perm_input"]),
                                    "perm_report": bool(row["perm_report"]),
                                    "perm_attendance": bool(row["perm_attendance"]),
                                    "perm_rules": bool(row["perm_rules"])
                                }).eq("id", r_id).execute()
                            st.cache_data.clear()
                            st.success("✅ Đã cập nhật quyền hạn chi tiết thành công!")
                            st.rerun()

                    st.markdown("---")
                    
                    with st.form("change_password_form_standalone"):
                        st.markdown("##### 🔑 Đổi mật khẩu nhanh cho nhân sự")
                        all_account_names = roles_df["name"].tolist() if "name" in roles_df.columns else staff_list_names
                        col_p1, col_p2, col_p3 = st.columns([1.5, 1.5, 1])
                        with col_p1:
                            target_staff_pw = st.selectbox("Chọn nhân sự cần đổi mật khẩu", ["--- Chọn nhân sự ---"] + all_account_names)
                        with col_p2:
                            new_staff_pass = st.text_input("Mật khẩu mới", type="password", placeholder="Nhập mật khẩu mới...")
                        with col_p3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            btn_update_pw = st.form_submit_button("Cập Nhật Mật Khẩu", use_container_width=True)

                        if btn_update_pw:
                            if target_staff_pw != "--- Chọn nhân sự ---" and new_staff_pass:
                                if len(new_staff_pass) >= 6:
                                    supabase.table("user_accounts").update({
                                        "password_hash": hash_password(new_staff_pass)
                                    }).eq("name", target_staff_pw).execute()
                                    st.success(f"✅ Đã đổi mật khẩu thành công cho **{target_staff_pw}**!")
                                else:
                                    st.error("⚠️ Mật khẩu phải có ít nhất 6 ký tự!")
                            else:
                                st.warning("⚠️ Vui lòng chọn nhân sự và nhập mật khẩu mới!")

                    with st.expander("🗑️ Xóa Tài Khoản Nhân Sự", expanded=False):
                        with st.form("delete_account_form_standalone"):
                            all_account_names = roles_df["name"].tolist() if "name" in roles_df.columns else staff_list_names
                            col_d1, col_d2 = st.columns([2, 1])
                            with col_d1:
                                target_staff_del = st.selectbox("Chọn nhân sự cần xóa tài khoản", ["--- Chọn nhân sự ---"] + all_account_names, key="select_del_staff_acc")
                            with col_d2:
                                st.markdown("<br>", unsafe_allow_html=True)
                                btn_execute_delete = st.form_submit_button("🔥 Xóa Tài Khoản Này", use_container_width=True)

                            if btn_execute_delete:
                                if target_staff_del == "--- Chọn nhân sự ---":
                                    st.warning("⚠️ Vui lòng chọn nhân sự cần xóa!")
                                else:
                                    try:
                                        supabase.table("user_accounts").delete().eq("name", target_staff_del).execute()
                                        supabase.table("staff").delete().eq("name", target_staff_del).execute()
                                        supabase.table("production_logs").delete().eq("nhan_su", target_staff_del).execute()
                                        supabase.table("attendance").delete().eq("nhan_su", target_staff_del).execute()
                                        supabase.table("error_logs").delete().eq("nhan_su", target_staff_del).execute()
                                        
                                        st.success(f"✅ Đã xóa thành công nhân sự **{target_staff_del}** cùng toàn bộ dữ liệu sản lượng, chấm công và lỗi liên quan!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Lỗi khi xóa nhân sự và dữ liệu liên quan: {e}")
                else:
                    st.info("Chưa có tài khoản nhân sự nào trong hệ thống.")
            except Exception as e:
                st.error(f"Lỗi quản lý tài khoản: {e}")

    # ==================== LÀM SẠCH DỮ LIỆU ====================
    elif current_menu_name == "🧹 Làm Sạch Dữ Liệu":
        col_cd_h1, col_cd_h2 = st.columns([3, 1])
        with col_cd_h1:
            st.header("🧹 Làm Sạch & Tối Ưu Dữ Liệu Hệ Thống")
        with col_cd_h2:
            if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_cd"):
                st.cache_data.clear()
                st.rerun()

        if current_user_role != "Admin":
            st.warning("🔒 Tính năng làm sạch dữ liệu chỉ dành cho Admin.")
        else:
            st.markdown("---")
            
            col_box1, col_box2 = st.columns(2)
            with col_box1:
                with st.container(border=True):
                    st.markdown("##### 🗑️ Xóa Vĩnh Viễn Thùng Rác")
                    st.caption("Dọn dẹp toàn bộ các bản ghi đã đưa vào thùng rác và tự động xóa vĩnh viễn tệp ảnh liên quan trên Cloud Storage.")
                    if st.button("🔥 Làm Sạch Thùng Rác Vĩnh Viễn", use_container_width=True, type="primary", key="btn_clean_trash_all"):
                        trash_df = get_production_logs_db(is_deleted=True, limit_rows=1000)
                        if not trash_df.empty:
                            from database import permanent_delete_db
                            permanent_delete_db(trash_df["db_id"].tolist())
                            st.success("✅ Đã dọn sạch toàn bộ thùng rác và giải phóng dung lượng storage thành công!")
                            st.rerun()
                        else:
                            st.info("ℹ️ Thùng rác hiện đang trống.")

            with col_box2:
                with st.container(border=True):
                    st.markdown("##### 🚀 Quét Toàn Bộ Ứng Dụng & Dọn Rác")
                    st.caption("Tự động quét toàn bộ ứng dụng, tìm kiếm và loại bỏ triệt để các tệp hình ảnh mồ côi (không liên kết với bất kỳ dữ liệu nào).")
                    if st.button("🔍 Chạy Quét & Làm Sạch Hệ Thống", use_container_width=True, key="btn_deep_system_scan"):
                        with st.spinner("⏳ Đang quét toàn bộ hệ thống ứng dụng và kiểm tra tệp rác trên Cloud Storage..."):
                            count, msg = cleanup_orphan_storage_files()
                            st.cache_data.clear()
                            if count > 0:
                                st.success(f"✅ Quét và dọn dẹp hệ thống thành công! Đã loại bỏ **{count} tệp rác mồ côi** khỏi Cloud Storage.")
                            else:
                                st.info("✨ Hệ thống rất sạch sẽ! Không tìm thấy tệp rác mồ côi nào cần loại bỏ.")
    else:
        st.subheader(current_menu_name)
        st.info(f"Đang hiển thị nội dung cho mục: {current_menu_name}")

# ==================== THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR) ====================
with st.sidebar:
    st.markdown('<div class="fixed-avatar-container">', unsafe_allow_html=True)
    
    has_custom_avatar = False
    avatar_bytes_obj = None
    if st.session_state.get("avatar_base64"):
        try:
            pure_b64 = st.session_state.avatar_base64.split(",")[1] if "," in st.session_state.avatar_base64 else st.session_state.avatar_base64
            pure_b64 += "=" * (-len(pure_b64) % 4)
            avatar_bytes_obj = base64.b64decode(pure_b64)
            has_custom_avatar = True
        except Exception:
            pass

    st.markdown('<div class="avatar-wrapper">', unsafe_allow_html=True)
    if has_custom_avatar:
        with st.popover(" ", use_container_width=False):
            st.markdown("##### 🔍 Xem Ảnh Đại Diện Lớn")
            st.image(avatar_bytes_obj, use_container_width=True)
        encoded_img = base64.b64encode(avatar_bytes_obj).decode("utf-8")
        st.markdown(f'<div style="cursor: pointer; text-align: center;"><img src="data:image/jpeg;base64,{encoded_img}" style="width:140px; height:140px; border-radius:50%; object-fit:cover; border:3px solid {st.session_state.primary_color}; box-shadow:0 4px 10px rgba(0,0,0,0.3);"></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="width:140px; height:140px; border-radius:50%; background:#cbd5e1; display:flex; align-items:center; justify-content:center; font-size:50px; border:3px solid {st.session_state.primary_color}; box-shadow:0 4px 10px rgba(0,0,0,0.3); margin: 0 auto;">👤</div>', unsafe_allow_html=True)

    st.markdown('<div style="position: absolute; bottom: 2px; right: 10px; z-index: 9999999;">', unsafe_allow_html=True)
    with st.popover("⚙️"):
        st.markdown("##### ⚙️️ Cài Đặt Ảnh Đại Diện")
        avatar_file = st.file_uploader("Tải ảnh mới", type=["png", "jpg", "jpeg"], key="avatar_uploader_popover_unique", label_visibility="collapsed")
        if avatar_file is not None:
            current_file_sig = f"{avatar_file.name}_{avatar_file.size}"
            if st.session_state.get("last_processed_avatar") != current_file_sig:
                compressed_avatar = compress_image_to_base64(avatar_file, max_size=(300, 300), quality=60)
                if compressed_avatar:
                    st.session_state.avatar_base64 = compressed_avatar
                    st.session_state["last_processed_avatar"] = current_file_sig
                    save_app_settings_db({
                        "primary_color": st.session_state.primary_color, 
                        "bg_color": st.session_state.bg_color,
                        "sidebar_bg": st.session_state.sidebar_bg, 
                        "sidebar_opacity": st.session_state.sidebar_opacity,
                        "text_color": st.session_state.text_color, 
                        "bg_image_base64": st.session_state.get("bg_image_base64"),
                        "avatar_base64": st.session_state.avatar_base64
                    })
                    st.success("✅ Đã cập nhật ảnh đại diện thành công!")
                    st.rerun()
        if st.session_state.get("avatar_base64"):
            st.markdown("---")
            if st.button("🗑️ Xóa Ảnh Đại Diện", use_container_width=True, key="btn_remove_avatar_unique"):
                st.session_state.avatar_base64 = None
                st.session_state["last_processed_avatar"] = None
                save_app_settings_db({
                    "primary_color": st.session_state.primary_color, 
                    "bg_color": st.session_state.bg_color,
                    "sidebar_bg": st.session_state.sidebar_bg, 
                    "sidebar_opacity": st.session_state.sidebar_opacity,
                    "text_color": st.session_state.text_color, 
                    "bg_image_base64": st.session_state.get("bg_image_base64"),
                    "avatar_base64": None
                })
                st.success("✅ Đã xóa ảnh đại diện!")
                st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

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

    st.markdown("---")
    st.markdown("### 📂 CHỨC NĂNG HỆ THỐNG")
    
    dynamic_menu_items = [
        "⏱️️ Chấm Công Ca Làm Việc",
        "1. Nhập Sản Lượng",
        "📊 Báo Cáo & Biểu Đồ",
        "📂 Thư Mục Báo Cáo",
        "📋 Định Mức Công Việc",
        "🛠️ Quản Lý Lỗi",
        "🗑️ Thùng Rác"
    ]
    
    if "current_menu" not in st.session_state: 
        st.session_state.current_menu = "1. Nhập Sản Lượng"

    if "radio_selection" not in st.session_state:
        st.session_state.radio_selection = "1. Nhập Sản Lượng"

    if st.session_state.current_menu in dynamic_menu_items:
        st.session_state.radio_selection = st.session_state.current_menu

    current_index = 0
    if st.session_state.radio_selection in dynamic_menu_items:
        current_index = dynamic_menu_items.index(st.session_state.radio_selection)

    chosen_menu = st.radio(
        "📌 Danh Mục Nghiệp Vụ", 
        dynamic_menu_items, 
        index=current_index,
        label_visibility="collapsed",
        key="sidebar_radio_menu"
    )

    if chosen_menu != st.session_state.current_menu:
        st.session_state.current_menu = chosen_menu
        st.session_state.radio_selection = chosen_menu

    if current_user_role == "Admin":
        st.markdown("---")
        st.markdown("### ⚙️ Cấu Hình Hệ Thống\n(Admin)")
        if st.button("🎨 Cài Đặt Giao Diện", use_container_width=True):
            st.session_state.current_menu = "🎨 Cài Đặt Giao Diện"
        if st.button("🛡️ Quản Lý Tài Khoản & Phân Quyền", use_container_width=True):
            st.session_state.current_menu = "🛡️ Quản Lý Tài Khoản & Phân Quyền"
        if st.button("🧹 Làm Sạch Dữ Liệu", use_container_width=True):
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

# ==================== GỌI THỰC THI HIỂN THỊ NỘI DUNG ====================
render_main_content(st.session_state.current_menu)
