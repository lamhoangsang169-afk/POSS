# database.py
import time
import datetime
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Khởi tạo kết nối Supabase an toàn từ st.secrets
def init_supabase():
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_supabase()
is_supabase_connected = supabase is not None

def init_db_data():
    pass

@st.cache_data(ttl=600, show_spinner=False)
def get_staff_df_db():
    if supabase is None:
        return pd.DataFrame(columns=["id", "name"])
    try:
        res = supabase.table("staff").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            if "name" not in df.columns and "ten" in df.columns:
                df = df.rename(columns={"ten": "name"})
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=["id", "name"])

def get_staff_list_db():
    df = get_staff_df_db()
    if not df.empty and "name" in df.columns:
        return df["name"].dropna().tolist()
    return []

@st.cache_data(ttl=600, show_spinner=False)
def add_production_log_db(ngay, gio, nhan_su, hang_muc, anh, don_vi, so_luong, he_so, tong_diem, ghi_chu):
    try:
        data = {
            "ngay": ngay,
            "thoi_gian": gio,
            "nhan_su": nhan_su,
            "hang_muc_cong_viec": hang_muc,
            "hinh_anh_url": anh,
            "don_vi": don_vi,
            "so_luong": so_luong,
            "he_so_diem": he_so,
            "tong_diem": tong_diem,
            "ghi_chu": ghi_chu,
            "is_deleted": False
        }
        response = supabase.table("production_logs").insert(data).execute()
        return response
    except Exception as e:
        st.error(f"Lỗi database: {e}")
        return None

def get_production_logs_db(is_deleted=False, limit_rows=1000):
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("production_logs").select("*").eq("is_deleted", is_deleted).order("id", desc=True).limit(limit_rows).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.rename(columns={
                "id": "db_id", "ngay": "Ngày", "thoi_gian": "Thời Gian",
                "nhan_su": "Nhân Sự", "hang_muc_cong_viec": "Hạng Mục Công Việc",
                "hinh_anh_url": "Hình Ảnh", "don_vi": "Đơn Vị", "so_luong": "Số Lượng",
                "he_so": "Hệ Số", "tong_diem": "Tổng Điểm", "ghi_chu": "Ghi Chú"
            })
            df.insert(0, "STT", range(1, len(df) + 1))
            return df
    except Exception:
        pass
    return pd.DataFrame()

def get_production_logs_by_date_range(start_date, end_date):
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("production_logs").select("*").eq("is_deleted", False).gte("ngay", str(start_date)).lte("ngay", str(end_date)).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.rename(columns={
                "id": "db_id", "ngay": "Ngày", "thoi_gian": "Thời Gian",
                "nhan_su": "Nhân Sự", "hang_muc_cong_viec": "Hạng Mục Công Việc",
                "hinh_anh_url": "Hình Ảnh", "don_vi": "Đơn Vị", "so_luong": "Số Lượng",
                "he_so": "Hệ Số", "tong_diem": "Tổng Điểm", "ghi_chu": "Ghi Chú"
            })
            return df
    except Exception:
        pass
    return pd.DataFrame()

def get_total_production_count_db():
    if supabase is None:
        return 0
    try:
        res = supabase.table("production_logs").select("id", count="exact").eq("is_deleted", False).execute()
        return res.count if res and res.count is not None else 0
    except Exception:
        return 0

@st.cache_data(ttl=600, show_spinner=False)
def get_attendance_db():
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("attendance").select("*").order("id", desc=True).limit(100).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.rename(columns={
                "id": "db_id", "ngay": "Ngày", "nhan_su": "Nhân Sự",
                "gio_vao_ca": "Giờ Vào Ca", "gio_ra_ca": "Giờ Ra Ca",
                "so_phut_lam_viec": "Số Phút Làm Việc", "ghi_chu": "Ghi Chú"
            })
            df.insert(0, "STT", range(1, len(df) + 1))
            return df
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def load_app_settings_db():
    if supabase is None:
        return {}
    try:
        res = supabase.table("app_settings").select("*").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception:
        pass
    return {}

@st.cache_data(ttl=60, show_spinner=False)
def load_folders_db():
    default_folders = [{
        "folder_name": "📌 Quản Lý Nghiệp Vụ",
        "items": [
            {"id": "menu_1", "name": "1. Nhập Sản Lượng"},
            {"id": "menu_2", "name": "2. Báo Cáo Thống Kê"},
            {"id": "menu_3", "name": "3. Tham Chiếu Định Mức"},
            {"id": "menu_4", "name": "4. Thùng Rác Sản Lượng"},
            {"id": "menu_5", "name": "5. Thư Mục Báo Cáo"}
        ]
    }]
    if supabase is None:
        return default_folders
    try:
        res = supabase.table("app_folders").select("folders_json").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            folders_data = res.data[0].get("folders_json")
            if folders_data:
                return folders_data
    except Exception:
        pass
    return default_folders

def update_production_log_deleted_status(db_ids, is_deleted):
    if supabase is None or not db_ids:
        return None
    try:
        for db_id in db_ids:
            supabase.table("production_logs").update({"is_deleted": is_deleted}).eq("id", db_id).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi khi cập nhật trạng thái xóa: {e}")
        return None

def upload_multiple_images_to_storage(uploaded_files):
    if not uploaded_files or supabase is None:
        return ""
    
    uploaded_urls = []
    bucket_name = "production_images"

    for file in uploaded_files:
        try:
            file_ext = file.name.split(".")[-1]
            unique_filename = f"{int(time.time())}_{file.name.replace(' ', '_')}"
            file_bytes = file.read()
            
            supabase.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_bytes,
                file_options={"content-type": file.type}
            )
            
            public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
            uploaded_urls.append(public_url)
        except Exception as e:
            st.error(f"Lỗi upload ảnh {file.name}: {e}")
            
    return ",".join(uploaded_urls)

def permanent_delete_db(db_ids):
    if supabase is None or not db_ids:
        return None
    try:
        for db_id in db_ids:
            supabase.table("production_logs").delete().eq("id", db_id).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi khi xóa vĩnh viễn: {e}")
        return None

def add_attendance_log_db(ngay, nhan_su, gio_vao):
    if supabase is None:
        return None
    try:
        data = {
            "ngay": ngay,
            "nhan_su": nhan_su,
            "gio_vao_ca": gio_vao,
            "gio_ra_ca": "Chưa kết thúc",
            "so_phut_lam_viec": 0,
            "ghi_chu": ""
        }
        response = supabase.table("attendance").insert(data).execute()
        return response
    except Exception as e:
        st.error(f"Lỗi Check-in: {e}")
        return None

def update_attendance_checkout_db(db_id, gio_ra, so_phut, ghi_chu=""):
    if supabase is None:
        return None
    try:
        data = {
            "gio_ra_ca": gio_ra,
            "so_phut_lam_viec": so_phut,
            "ghi_chu": ghi_chu
        }
        response = supabase.table("attendance").update(data).eq("id", db_id).execute()
        return response
    except Exception as e:
        st.error(f"Lỗi Check-out: {e}")
        return None

@st.cache_data(ttl=600, show_spinner=False)
def get_rules_db():
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("rules").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            rename_map = {}
            if "hang_muc" in df.columns: rename_map["hang_muc"] = "Hạng Mục Công Việc"
            if "hang_muc_cong_viec" in df.columns: rename_map["hang_muc_cong_viec"] = "Hạng Mục Công Việc"
            if "he_so_diem" in df.columns: rename_map["he_so_diem"] = "Hệ Số Điểm"
            if "don_vi" in df.columns: rename_map["don_vi"] = "Đơn Vị"
            if "ghi_chu" in df.columns: rename_map["ghi_chu"] = "Ghi Chú"
            
            df = df.rename(columns=rename_map)
            return df
    except Exception as e:
        st.error(f"Lỗi khi tải bảng định mức: {e}")
        pass
    return pd.DataFrame()

def add_rule_db(hang_muc, he_so, don_vi, ghi_chu=""):
    if supabase is None:
        return None
    try:
        data = {
            "hang_muc_cong_viec": hang_muc,
            "he_so_diem": he_so,
            "don_vi": don_vi,
            "ghi_chu": ghi_chu
        }
        response = supabase.table("rules").insert(data).execute()
        return response
    except Exception as e:
        st.error(f"Lỗi thêm định mức: {e}")
        return None

def update_rule_db(db_id, hang_muc, he_so, don_vi, ghi_chu=""):
    if supabase is None:
        return None
    try:
        data = {
            "hang_muc_cong_viec": hang_muc,
            "he_so_diem": he_so,
            "don_vi": don_vi,
            "ghi_chu": ghi_chu
        }
        response = supabase.table("rules").update(data).eq("id", db_id).execute()
        return response
    except Exception as e:
        st.error(f"Lỗi cập nhật định mức: {e}")
        return None

def delete_rule_db(db_id):
    if supabase is None:
        return None
    try:
        response = supabase.table("rules").delete().eq("id", db_id).execute()
        return response
    except Exception:
        pass
    return None


# --- CÁC HÀM XỬ LÝ CHO QUẢN LÝ LỖI SẢN XUẤT ---

@st.cache_data(ttl=600, show_spinner=False)
def get_error_logs_db(limit_rows=1000):
    """Tải danh sách báo cáo lỗi từ Supabase"""
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("error_logs").select("*").order("id", desc=True).limit(limit_rows).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.rename(columns={
                "id": "db_id", 
                "ngay": "Ngày", 
                "nhan_su": "Nhân Sự",
                "phan_loai_loi": "Phân Loại Lỗi", 
                "so_luong": "Số Lượng",
                "ghi_chu": "Ghi Chú", 
                "so_anh_dinh_kem": "Số Ảnh Đính Kèm"
            })
            return df
    except Exception:
        pass
    return pd.DataFrame()

def add_error_log_with_images_db(ngay, nhan_su, phan_loai_loi, so_luong, ghi_chu, images_base64_str):
    """Thêm một báo cáo lỗi mới kèm chuỗi ảnh base64 vào Supabase"""
    if supabase is None:
        return None
    try:
        data = {
            "ngay": str(ngay),
            "nhan_su": nhan_su,
            "phan_loai_loi": phan_loai_loi,
            "so_luong": so_luong,
            "ghi_chu": ghi_chu,
            "so_anh_dinh_kem": images_base64_str
        }
        response = supabase.table("error_logs").insert(data).execute()
        return response
    except Exception as e:
        st.error(f"Lỗi ghi nhận báo cáo lỗi: {e}")
        return None

@st.cache_data(ttl=10, show_spinner=False)
def get_error_categories_db():
    """Tải danh mục loại lỗi từ bảng riêng error_settings trên Supabase"""
    default_categories = ["Sản phẩm hỏng", "Lỗi nguyên vật liệu", "Lỗi thao tác", "Lỗi máy móc / thiết bị", "Khác"]
    if supabase is None:
        return default_categories
    try:
        res = supabase.table("error_settings").select("*").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            categories = res.data[0].get("categories_json")
            if categories and isinstance(categories, list):
                return categories
    except Exception:
        pass
    return default_categories

def save_error_categories_db(categories_list):
    """Lưu hoặc cập nhật danh mục loại lỗi lên bảng error_settings"""
    if supabase is None:
        return None
    try:
        data = {
            "id": 1,
            "categories_json": categories_list
        }
        response = supabase.table("error_settings").upsert(data).execute()
        return response
    except Exception as e:
        st.error(f"Lỗi lưu danh mục lỗi: {e}")
        return None
