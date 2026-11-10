import time
import datetime
import io
import os
import unicodedata
from PIL import Image
import streamlit as st
import pandas as pd
from supabase import create_client, Client

@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url:
        url = "https://mnwyewgsxvpjwnpmgyhj.supabase.co"
    if not key:
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ud3lld2dzeHZwanducG1neWhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA3MjMwNjgsImV4cCI6MjEwNjI5OTA2OH0.eeTU1a16zY5c4XHr7YobwRRJXstgkQjt3lyIosUMVQk"
        
    try:
        return create_client(url, key)
    except Exception as ex:
        st.error(f"Lỗi khởi tạo Supabase: {ex}")
        return None

supabase = init_supabase()

def safe_supabase_call(query_func):
    global supabase
    if supabase is None:
        supabase = init_supabase()
    try:
        return query_func(supabase)
    except Exception as e:
        err_str = str(e)
        if "JWT expired" in err_str or "PGRST303" in err_str or "Unauthorized" in err_str:
            st.cache_resource.clear()
            supabase = init_supabase()
            try:
                return query_func(supabase)
            except Exception as inner_e:
                st.error(f"Lỗi sau khi làm mới kết nối: {inner_e}")
                return None
        else:
            raise e

is_supabase_connected = supabase is not None

def init_db_data():
    """Đảm bảo các bảng cấu hình luôn có sẵn dòng id = 1 để F5 không bị mất dữ liệu"""
    if supabase is None:
        return
    try:
        def _q1(client):
            return client.table("app_settings").select("id").eq("id", 1).execute()
        res_settings = safe_supabase_call(_q1)
        
        if not res_settings or not res_settings.data:
            default_settings = {
                "id": 1,
                "primary_color": "#1f77b4",
                "bg_color": "#ffffff",
                "sidebar_bg": "#f0f2f6"
            }
            def _u1(client):
                return client.table("app_settings").upsert(default_settings).execute()
            safe_supabase_call(_u1)

        def _q2(client):
            return client.table("app_folders").select("id").eq("id", 1).execute()
        res_folder = safe_supabase_call(_q2)
        
        if not res_folder or not res_folder.data:
            default_folders = [{
                "folder_name": "📌 Quản Lý Nghiệp Vụ",
                "items": [
                    {"id": "menu_1", "name": "1. Nhập Sản Lượng"},
                    {"id": "menu_2", "name": "2. Báo Cáo Thống Kê"},
                    {"id": "menu_3", "name": "3. Tham Chiếu Định Mức"},
                    {"id": "menu_4", "name": "4. Thùng Rác Sản Lượng"},
                    {"id": "menu_5", "name": "5. Thư Mục Báo Cáo"},
                    {"id": "menu_6", "name": "6. Quản Lý Lỗi"}
                ]
            }]
            def _u2(client):
                return client.table("app_folders").upsert({"id": 1, "folders_json": default_folders}).execute()
            safe_supabase_call(_u2)

        def _q3(client):
            return client.table("error_settings").select("id").eq("id", 1).execute()
        res_error = safe_supabase_call(_q3)
        
        if not res_error or not res_error.data:
            default_categories = ["Sản phẩm hỏng", "Lỗi nguyên vật liệu", "Lỗi thao tác", "Lỗi máy móc / thiết bị", "Khác"]
            def _u3(client):
                return client.table("error_settings").upsert({"id": 1, "categories_json": default_categories}).execute()
            safe_supabase_call(_u3)
    except Exception:
        pass

init_db_data()

@st.cache_data(ttl=10, show_spinner=False)
def get_staff_df_db():
    if supabase is None:
        return pd.DataFrame(columns=["id", "name", "role"])
    try:
        def _query(client):
            return client.table("user_accounts").select("id, name, role").order("id", desc=False).execute()
        res = safe_supabase_call(_query)
        if res and res.data:
            df = pd.DataFrame(res.data)
            if "name" not in df.columns and "ten" in df.columns:
                df = df.rename(columns={"ten": "name"})
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=["id", "name", "role"])

def get_staff_list_db():
    df = get_staff_df_db()
    if not df.empty and "name" in df.columns:
        return df["name"].dropna().tolist()
    return []

def add_production_log_db(ngay, gio, nhan_su, hang_muc, anh, don_vi, so_luong, he_so, tong_diem, ghi_chu):
    try:
        try:
            tong_diem = round(float(str(tong_diem).replace(",", ".").strip()), 2)
