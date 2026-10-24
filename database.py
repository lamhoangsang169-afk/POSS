import time
import datetime
import io
from PIL import Image
import streamlit as st
import pandas as pd
from supabase import create_client, Client

@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL", "https://mnwyewgsxvpjwnpmgyhj.supabase.co")
        key = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ud3lld2dzeHZwanducG1neWhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA3MjMwNjgsImV4cCI6MjEwNjI5OTA2OH0.eeTU1a16zY5c4XHr7YobwRRJXstgkQjt3lyIosUMVQk")
        return create_client(url, key)
    except Exception as e:
        try:
            url = "https://mnwyewgsxvpjwnpmgyhj.supabase.co"
            key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ud3lld2dzeHZwanducG1neWhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA3MjMwNjgsImV4cCI6MjEwNjI5OTA2OH0.eeTU1a16zY5c4XHr7YobwRRJXstgkQjt3lyIosUMVQk"
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
        except:
            pass

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
        def _query(client):
            return client.table("production_logs").insert(data).execute()
        response = safe_supabase_call(_query)
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"Lỗi database: {e}")
        return None

def get_production_logs_db(is_deleted=False, limit_rows=1000):
    if supabase is None:
        return pd.DataFrame()
    try:
        def _query(client):
            return client.table("production_logs").select("*").eq("is_deleted", is_deleted).order("id", desc=True).limit(limit_rows).execute()
        res = safe_supabase_call(_query)
        if res and res.data:
            df = pd.DataFrame(res.data)
            rename_dict = {
                "id": "db_id", "ngay": "Ngày", "thoi_gian": "Thời Gian",
                "nhan_su": "Nhân Sự", "hang_muc_cong_viec": "Hạng Mục Công Việc",
                "hinh_anh_url": "Hình Ảnh", "don_vi": "Đơn Vị", "so_luong": "Số Lượng",
                "tong_diem": "Tổng Điểm", "ghi_chu": "Ghi Chú"
            }
            if "he_so_diem" in df.columns:
                rename_dict["he_so_diem"] = "Hệ Số"
            elif "he_so" in df.columns:
                rename_dict["he_so"] = "Hệ Số"
            df = df.rename(columns=rename_dict)
            df.insert(0, "STT", range(1, len(df) + 1))
            return df
    except Exception:
        pass
    return pd.DataFrame()

def get_production_logs_by_date_range(start_date, end_date):
    if supabase is None:
        return pd.DataFrame()
    try:
        def _query(client):
            return client.table("production_logs").select("*").eq("is_deleted", False).gte("ngay", str(start_date)).lte("ngay", str(end_date)).execute()
        res = safe_supabase_call(_query)
        if res and res.data:
            df = pd.DataFrame(res.data)
            rename_dict = {
                "id": "db_id", "ngay": "Ngày", "thoi_gian": "Thời Gian",
                "nhan_su": "Nhân Sự", "hang_muc_cong_viec": "Hạng Mục Công Việc",
                "hinh_anh_url": "Hình Ảnh", "don_vi": "Đơn Vị", "so_luong": "Số Lượng",
                "tong_diem": "Tổng Điểm", "ghi_chu": "Ghi Chú"
            }
            if "he_so_diem" in df.columns:
                rename_dict["he_so_diem"] = "Hệ Số"
            elif "he_so" in df.columns:
                rename_dict["he_so"] = "Hệ Số"
            df = df.rename(columns=rename_dict)
            return df
    except Exception:
        pass
    return pd.DataFrame()

def get_total_production_count_db():
    if supabase is None:
        return 0
    try:
        def _query(client):
            return client.table("production_logs").select("id", count="exact").eq("is_deleted", False).execute()
        res = safe_supabase_call(_query)
        return res.count if res and res.count is not None else 0
    except Exception:
        return 0

@st.cache_data(ttl=600, show_spinner=False)
def get_attendance_db():
    if supabase is None:
        return pd.DataFrame()
    try:
        def _query(client):
            return client.table("attendance").select("*").order("id", desc=True).limit(100).execute()
        res = safe_supabase_call(_query)
        if res and res.data:
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
        def _query(client):
            return client.table("app_settings").select("*").eq("id", 1).execute()
        res = safe_supabase_call(_query)
        if res and res.data and len(res.data) > 0:
            return res.data[0]
    except Exception:
        pass
    return {}

def save_app_settings_db(settings_dict):
    if supabase is None:
        return None
    try:
        payload = {"id": 1, **settings_dict}
        def _query(client):
            return client.table("app_settings").upsert(payload).execute()
        response = safe_supabase_call(_query)
        load_app_settings_db.clear()
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"Lỗi khi lưu cài đặt ứng dụng: {e}")
        return None

def update_production_log_deleted_status(db_ids, is_deleted):
    if supabase is None or not db_ids:
        return None
    try:
        for db_id in db_ids:
            def _query(client):
                return client.table("production_logs").update({"is_deleted": is_deleted}).eq("id", db_id).execute()
            safe_supabase_call(_query)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi khi cập nhật trạng thái xóa: {e}")
        return None

def upload_multiple_images_to_storage(uploaded_files, bucket_name="production_images", max_size=(800, 600), target_kb=50):
    if not uploaded_files or supabase is None:
        return ""
    
    uploaded_urls = []
    for file in uploaded_files:
        try:
            image_bytes = file.read()
            img = Image.open(io.BytesIO(image_bytes))

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            quality = 85
            output_io = io.BytesIO()
            img.save(output_io, format="JPEG", quality=quality, optimize=True)
            compressed_file_bytes = output_io.getvalue()

            while len(compressed_file_bytes) > target_kb * 1024 and quality > 20:
                quality -= 10
                output_io = io.BytesIO()
                img.save(output_io, format="JPEG", quality=quality, optimize=True)
                compressed_file_bytes = output_io.getvalue()

            clean_filename = file.name.rsplit('.', 1)[0].replace(' ', '_')
            unique_filename = f"{int(time.time())}_{clean_filename}.jpg"
            
            supabase.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=compressed_file_bytes,
                file_options={"content-type": "image/jpeg"}
            )
            
            public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
            uploaded_urls.append(public_url)
        except Exception as e:
            st.error(f"Lỗi nén và upload ảnh {file.name}: {e}")
            
    return ",".join(uploaded_urls)

def delete_images_from_storage_by_urls(image_urls_str, bucket_name="production_images"):
    if not image_urls_str or supabase is None:
        return
    try:
        urls = [u.strip() for u in str(image_urls_str).split(",") if u.strip()]
        file_paths_to_delete = []
        for url in urls:
            if "storage/v1/object/public/" in url:
                parts = url.split(f"/storage/v1/object/public/{bucket_name}/")
                if len(parts) > 1:
                    file_paths_to_delete.append(parts[1])
            elif "/" in url:
                file_paths_to_delete.append(url.split("/")[-1])
                
        if file_paths_to_delete:
            supabase.storage.from_(bucket_name).remove(file_paths_to_delete)
    except Exception as e:
        st.warning(f"⚠️ Lỗi khi xóa ảnh trên Supabase Storage: {e}")

def permanent_delete_db(db_ids):
    if supabase is None or not db_ids:
        return None
    try:
        for db_id in db_ids:
            def _query_sel(client):
                return client.table("production_logs").select("hinh_anh_url").eq("id", db_id).execute()
            res = safe_supabase_call(_query_sel)
            
            if res and res.data and len(res.data) > 0:
                img_url = res.data[0].get("hinh_anh_url", "")
                if img_url:
                    delete_images_from_storage_by_urls(img_url, bucket_name="production_images")
            
            def _query_del(client):
                return client.table("production_logs").delete().eq("id", db_id).execute()
            safe_supabase_call(_query_del)
            
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi khi xóa vĩnh viễn: {e}")
        return None

def cleanup_orphan_storage_files():
    if supabase is None:
        return 0, "Chưa kết nối Database"
    cleaned_count = 0
    try:
        buckets = ["production_images", "reports-storage"]
        def _query_logs(client):
            return client.table("production_logs").select("hinh_anh_url").eq("is_deleted", False).execute()
        res_logs = safe_supabase_call(_query_logs)
        
        used_urls = set()
        if res_logs and res_logs.data:
            for row in res_logs.data:
                url_str = row.get("hinh_anh_url", "")
                if url_str:
                    for u in url_str.split(","):
                        if u.strip():
                            used_urls.add
