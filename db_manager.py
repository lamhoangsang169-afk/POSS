import streamlit as st

def get_database_connection():
    """
    Trả về cấu hình/kết nối database phù hợp theo công tắc.
    """
    use_new = st.secrets.get("USE_NEW_DB", False)
    
    if use_new:
        # --- LUỒNG MỚI: Kết nối Neon ---
        connection_string = st.secrets["neon"]["connection_string"]
        # Trả về kết nối hoặc client dùng connection_string của Neon
        return connection_string
    
    else:
        # --- LUỒNG CŨ: Kết nối Supabase Database ---
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        return {"url": supabase_url, "key": supabase_key}
