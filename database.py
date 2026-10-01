import time
import datetime
import io
from PIL import Image
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Khởi tạo kết nối Supabase an toàn qua st.secrets (hoặc fallback nếu chưa cấu hình secrets)
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
is_supabase_connected = supabase is not None

def init_db_data():
    """Đảm bảo các bảng cấu hình luôn có sẵn dòng id = 1 để F5 không bị mất dữ liệu"""
    if supabase is None:
        return
    try:
        # Khởi tạo app_settings nếu trống
        res_settings = supabase.table("app_settings").select("id").eq("id", 1).execute()
        if not res_settings.data:
            default_settings = {
                "id": 1,
                "primary_color": "#1f77b4",
                "bg_color": "#ffffff",
                "sidebar_bg": "#f0f2f6"
            }
            supabase.table("app_settings").upsert(default_settings).execute()

        # Khởi tạo app_folders nếu trống
        res_folder = supabase.table("app_folders").select("id").eq("id", 1).execute()
        if not res_folder.data:
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
            supabase.table("app_folders").upsert({"id": 1, "folders_json": default_folders}).execute()

        # Khởi tạo error_settings nếu trống
        res_error = supabase.table("error_settings").select("id").eq("id", 1).execute()
        if not res_error.data:
            default_categories = ["Sản phẩm hỏng", "Lỗi nguyên vật liệu", "Lỗi thao tác", "Lỗi máy móc / thiết bị", "Khác"]
            supabase.table("error_settings").upsert({"id": 1, "categories_json": default_categories}).execute()
    except Exception:
        pass

# Gọi khởi tạo ngầm an toàn
init_db_data()

@st.cache_data(ttl=10, show_spinner=False)
def get_staff_df_db():
    """Lấy DataFrame nhân sự từ bảng user_accounts (Đồng bộ tập trung)"""
    if supabase is None:
        return pd.DataFrame(columns=["id", "name", "role"])
    try:
        res = supabase.table("user_accounts").select("id, name, role").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            if "name" not in df.columns and "ten" in df.columns:
                df = df.rename(columns={"ten": "name"})
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=["id", "name", "role"])

def get_staff_list_db():
    """Lấy danh sách tên nhân sự từ bảng user_accounts"""
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

def save_app_settings_db(settings_dict):
    """Lưu cài đặt giao diện/màu sắc vào Supabase để không bị mất khi F5"""
    if supabase is None:
        return None
    try:
        settings_dict["id"] = 1
        response = supabase.table("app_settings").upsert(settings_dict).execute()
        load_app_settings_db.clear()
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"Lỗi khi lưu cài đặt ứng dụng: {e}")
        return None

@st.cache_data(ttl=10, show_spinner=False)
def load_folders_db():
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
    if supabase is None:
        return default_folders
    try:
        res = supabase.table("app_folders").select("*").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            folders_data = res.data[0].get("folders_json")
            if folders_data and isinstance(folders_data, list):
                items = folders_data[0].get("items", [])
                if not any(str(item.get("name", "")).startswith("6.") for item in items):
                    items.append({"id": "menu_6", "name": "6. Quản Lý Lỗi"})
                    folders_data[0]["items"] = items
                return folders_data
    except Exception as e:
        st.warning(f"⚠️ Không đọc được dữ liệu thư mục từ Database: {e}")
    return default_folders

def save_folders_db(folders_list):
    if supabase is None:
        st.error("⚠️ Chưa kết nối Supabase!")
        return None
    try:
        payload = {"id": 1, "folders_json": folders_list}
        response = supabase.table("app_folders").upsert(payload).execute()
        load_folders_db.clear()
        st.cache_data.clear()
        st.success("✅ Lưu cấu hình vào Supabase thành công!")
        return response
    except Exception as e:
        st.error(f"❌ Lỗi khi lưu vào Supabase: {e}")
        return None

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

def upload_multiple_images_to_storage(uploaded_files, bucket_name="production_images", max_size=(800, 600), target_kb=50):
    """Nén tự động ảnh sao cho dung lượng đạt xấp xỉ mục tiêu (mặc định ~50KB) trước khi tải lên"""
    if not uploaded_files or supabase is None:
        return ""
    
    uploaded_urls = []

    for file in uploaded_files:
        try:
            # 1. Đọc tệp ảnh gốc
            image_bytes = file.read()
            img = Image.open(io.BytesIO(image_bytes))

            # Chuyển đổi định dạng sang RGB nếu ảnh ở dạng RGBA / PNG trong suốt
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 2. Thu nhỏ kích thước khung hình (giữ tỉ lệ)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # 3. Vòng lặp tự động giảm chất lượng (quality) để ép dung lượng về sát mức target_kb (50KB)
            quality = 85
            output_io = io.BytesIO()
            img.save(output_io, format="JPEG", quality=quality, optimize=True)
            compressed_file_bytes = output_io.getvalue()

            while len(compressed_file_bytes) > target_kb * 1024 and quality > 20:
                quality -= 10
                output_io = io.BytesIO()
                img.save(output_io, format="JPEG", quality=quality, optimize=True)
                compressed_file_bytes = output_io.getvalue()

            # 4. Tạo tên tệp độc lập và tiến hành upload lên Supabase Storage
            clean_filename = file.name.rsplit('.', 1)[0].replace(' ', '_')
            unique_filename = f"{int(time.time())}_{clean_filename}.jpg"
            
            supabase.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=compressed_file_bytes,
                file_options={"content-type": "image/jpeg"}
            )
            
            # 5. Lấy URL công khai sau khi upload thành công
            public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
            uploaded_urls.append(public_url)
            
        except Exception as e:
            st.error(f"Lỗi nén và upload ảnh {file.name}: {e}")
            
    return ",".join(uploaded_urls)

def delete_images_from_storage_by_urls(image_urls_str, bucket_name="production_images"):
    """Hàm phụ trợ: Xóa các tệp ảnh trên Supabase Storage dựa vào chuỗi URL lưu trong database"""
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
        print(f"Lỗi khi xóa ảnh trên Supabase Storage: {e}")

def permanent_delete_db(db_ids):
    """Xóa vĩnh viễn bản ghi sản lượng đồng thời xóa luôn các tệp ảnh liên quan trên Storage"""
    if supabase is None or not db_ids:
        return None
    try:
        for db_id in db_ids:
            # 1. Truy vấn lấy đường dẫn ảnh của bản ghi trước khi xóa
            res = supabase.table("production_logs").select("hinh_anh_url").eq("id", db_id).execute()
            if res.data and len(res.data) > 0:
                img_url = res.data[0].get("hinh_anh_url", "")
                if img_url:
                    delete_images_from_storage_by_urls(img_url, bucket_name="production_images")
            
            # 2. Thực hiện xóa dòng dữ liệu khỏi bảng production_logs
            supabase.table("production_logs").delete().eq("id", db_id).execute()
            
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi khi xóa vĩnh viễn: {e}")
        return None

def cleanup_orphan_storage_files():
    """Quét toàn bộ ứng dụng: tìm và xóa các file rác/mồ côi trên Supabase Storage không được liên kết với Database"""
    if supabase is None:
        return 0, "Chưa kết nối Database"
    cleaned_count = 0
    try:
        buckets = ["production_images", "reports-storage"]
        # Lấy tất cả các URL ảnh đang được sử dụng trong production_logs
        res_logs = supabase.table("production_logs").select("hinh_anh_url").eq("is_deleted", False).execute()
        used_urls = set()
        if res_logs.data:
            for row in res_logs.data:
                url_str = row.get("hinh_anh_url", "")
                if url_str:
                    for u in url_str.split(","):
                        if u.strip():
                            used_urls.add(u.strip())
                            
        for b_name in buckets:
            files_list = supabase.storage.from_(b_name).list()
            if files_list:
                files_to_delete = []
                for file_info in files_list:
                    filename = file_info.get("name")
                    if filename:
                        is_used = any(filename in u or u.endswith(filename) for u in used_urls)
                        if not is_used:
                            files_to_delete.append(filename)
                
                if files_to_delete:
                    supabase.storage.from_(b_name).remove(files_to_delete)
                    cleaned_count += len(files_to_delete)
        return cleaned_count, "Thành công"
    except Exception as e:
        return 0, str(e)

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
    return pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def get_error_logs_db(limit_rows=1000):
    if supabase is None:
        return pd.DataFrame()
    try:
        res = supabase.table("error_logs").select("*").order("id", desc=True).limit(limit_rows).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.rename(columns={
                "id": "db_id", "ngay": "Ngày", "nhan_su": "Nhân Sự",
                "phan_loai_loi": "Phân Loại Lỗi", "so_luong": "Số Lượng",
                "ghi_chu": "Ghi Chú", "so_anh_dinh_kem": "Số Ảnh Đính Kèm"
            })
            return df
    except Exception:
        pass
    return pd.DataFrame()

def add_error_log_with_images_db(ngay, nhan_su, phan_loai_loi, so_luong, ghi_chu, images_base64_str):
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
    if supabase is None:
        return None
    try:
        data = {"id": 1, "categories_json": categories_list}
        response = supabase.table("error_settings").upsert(data).execute()
        load_error_categories_db.clear()
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"Lỗi lưu danh mục lỗi: {e}")
        return None

def delete_storage_files_by_date_range(start_date, end_date):
    if supabase is None:
        return 0, "Chưa kết nối Supabase"
    
    deleted_count = 0
    try:
        res = supabase.table("production_logs")\
            .select("hinh_anh_url")\
            .gte("ngay", start_date.strftime("%Y-%m-%d"))\
            .lte("ngay", end_date.strftime("%Y-%m-%d"))\
            .execute()
            
        if not res.data:
            return 0, "Không tìm thấy tệp ảnh nào trong khoảng thời gian này."

        file_paths_to_delete = []
        for row in res.data:
            img_url = row.get("hinh_anh_url")
            if img_url:
                for u in img_url.split(","):
                    u = u.strip()
                    if "production_images/" in u:
                        path_part = u.split("production_images/")[-1]
                        file_paths_to_delete.append(path_part)

        if file_paths_to_delete:
            supabase.storage.from_("production_images").remove(file_paths_to_delete)
            deleted_count = len(file_paths_to_delete)
            
            supabase.table("production_logs")\
                .update({"hinh_anh_url": None})\
                .gte("ngay", start_date.strftime("%Y-%m-%d"))\
                .lte("ngay", end_date.strftime("%Y-%m-%d"))\
                .execute()

        return deleted_count, f"Đã xóa thành công {deleted_count} tệp ảnh."
    except Exception as e:
        return 0, f"Lỗi khi xóa ảnh theo ngày: {e}"
