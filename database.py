import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==================== CẤU HÌNH KẾT NỐI SUPABASE ====================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        is_supabase_connected = True
    else:
        supabase = None
        is_supabase_connected = False
except Exception as e:
    supabase = None
    is_supabase_connected = False

def init_db_data():
    """Khởi tạo dữ liệu cơ bản nếu cần"""
    pass

# ==================== QUẢN LÝ NHÂN SỰ & TÀI KHOẢN ====================
@st.cache_data(ttl=10)
def get_staff_list_db():
    """Lấy danh sách tên nhân sự trực tiếp từ bảng user_accounts (Đồng bộ tập trung)"""
    if supabase is None:
        return []
    try:
        res = supabase.table("user_accounts").select("name").execute()
        if res.data:
            return [row["name"] for row in res.data if row.get("name")]
    except Exception as e:
        print(f"Lỗi khi lấy danh sách nhân sự từ user_accounts: {e}")
    return []

@st.cache_data(ttl=10)
def get_staff_df_db():
    """Lấy DataFrame nhân sự từ bảng user_accounts"""
    if supabase is None:
        return pd.DataFrame(columns=["id", "name", "role"])
    try:
        res = supabase.table("user_accounts").select("id, name, role").execute()
        if res.data:
            return pd.DataFrame(res.data)
    except Exception as e:
        print(f"Lỗi khi tải DataFrame nhân sự: {e}")
    return pd.DataFrame(columns=["id", "name", "role"])

# ==================== ĐỊNH MỨC CÔNG VIỆC (RULES) ====================
@st.cache_data(ttl=10)
def get_rules_db():
    """Lấy danh mục định mức công việc từ bảng rules"""
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("rules").select("*").execute()
        if res.data:
            return pd.DataFrame(res.data)
    except Exception as e:
        print(f"Lỗi tải rules: {e}")
    return pd.DataFrame()

# ==================== SẢN LƯỢNG & CHẤM CÔNG ====================
def add_production_log_db(payload):
    """Thêm mới một bản ghi sản lượng vào cơ sở dữ liệu"""
    if supabase is None:
        return False
    try:
        supabase.table("production_logs").insert(payload).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Lỗi thêm sản lượng: {e}")
        return False

def update_production_log_deleted_status(log_id, is_deleted):
    """Cập nhật trạng thái xóa mềm của bản ghi sản lượng"""
    if supabase is None:
        return False
    try:
        supabase.table("production_logs").update({"is_deleted": is_deleted}).eq("id", log_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Lỗi cập nhật trạng thái xóa: {e}")
        return False

@st.cache_data(ttl=5)
def get_production_logs_db(is_deleted=False, limit_rows=500):
    if supabase is None:
        return pd.DataFrame()
    try:
        query = supabase.table("production_logs").select("*")
        try:
            query = query.eq("is_deleted", is_deleted)
        except Exception:
            pass
        res = query.order("id", desc=True).limit(limit_rows).execute()
        if res.data:
            return pd.DataFrame(res.data)
    except Exception as e:
        print(f"Lỗi tải production_logs: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=5)
def get_production_logs_by_date_range(start_date, end_date):
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("production_logs").select("*").gte("ngay", str(start_date)).lte("ngay", str(end_date)).execute()
        if res.data:
            return pd.DataFrame(res.data)
    except Exception as e:
        print(f"Lỗi tải production_logs theo ngày: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=5)
def get_total_production_count_db():
    if supabase is None:
        return 0
    try:
        res = supabase.table("production_logs").select("id", count="exact").execute()
        return res.count if res.count is not None else 0
    except Exception:
        return 0

@st.cache_data(ttl=5)
def get_attendance_db():
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("attendance").select("*").execute()
        if res.data:
            return pd.DataFrame(res.data)
    except Exception as e:
        print(f"Lỗi tải attendance: {e}")
    return pd.DataFrame()

# ==================== CẤU HÌNH ỨNG DỤNG ====================
@st.cache_data(ttl=30)
def load_app_settings_db():
    if supabase is None:
        return {}
    try:
        res = supabase.table("app_settings").select("*").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as e:
        print(f"Lỗi tải app_settings: {e}")
    return {}

def permanent_delete_db(ids_list):
    if supabase is None or not ids_list:
        return
    try:
        supabase.table("production_logs").delete().in_("id", ids_list).execute()
        st.cache_data.clear()
    except Exception as e:
        print(f"Lỗi xóa vĩnh viễn: {e}")
