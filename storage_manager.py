import streamlit as st
import cloudinary
import cloudinary.uploader
# Import thư viện Supabase cũ của bạn ở đây
# from supabase import create_client 

def upload_image(file_obj):
    """
    Hàm tổng đài: Tự động chọn nơi lưu ảnh dựa vào cấu hình secrets.
    """
    use_new = st.secrets.get("USE_NEW_STORAGE", False)
    
    if use_new:
        # --- LUỒNG MỚI: Dùng Cloudinary ---
        cloudinary.config(
            cloud_name=st.secrets["cloudinary"]["cloud_name"],
            api_key=st.secrets["cloudinary"]["api_key"],
            api_secret=st.secrets["cloudinary"]["api_secret"]
        )
        upload_result = cloudinary.uploader.upload(file_obj)
        return upload_result.get("secure_url")
    
    else:
        # --- LUỒNG CŨ: Dùng Supabase Storage hiện tại ---
        # (Giữ nguyên đoạn code upload Supabase cũ của bạn ở đây)
        # supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        # ... logic upload supabase ...
        return "url_anh_tu_supabase_cu"
