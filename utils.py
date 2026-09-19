import pytz
import base64
from PIL import Image
import io
import datetime

# Cấu hình múi giờ Việt Nam chuẩn xác
VN_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

def compress_image_to_base64(uploaded_file, max_size=(800, 800), quality=70):
    """Nén ảnh tải lên để tối ưu dung lượng hiển thị"""
    try:
        image = Image.open(uploaded_file)
        image.thumbnail(max_size)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=quality)
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        print(f"Lỗi nén ảnh: {e}")
        return None

def calculate_exact_minutes(start_date_str, start_time_str, end_date_str, end_time_str):
    """Tính chính xác tổng số phút làm việc giữa giờ vào và giờ ra"""
    try:
        dt_start_str = f"{start_date_str} {start_time_str}"
        dt_end_str = f"{end_date_str} {end_time_str}"
        dt_start = datetime.datetime.strptime(dt_start_str, "%Y-%m-%d %H:%M:%S")
        dt_end = datetime.datetime.strptime(dt_end_str, "%Y-%m-%d %H:%M:%S")
        diff = dt_end - dt_start
        total_minutes = int(diff.total_seconds() / 60)
        return max(0, total_minutes)
    except Exception as e:
        print(f"Lỗi tính thời gian: {e}")
        return 0

def hex_to_rgba(hex_code, alpha=1.0):
    """Chuyển đổi mã màu Hex sang định dạng RGBA"""
    try:
        hex_code = hex_code.lstrip('#')
        lv = len(hex_code)
        rgb = tuple(int(hex_code[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"
    except Exception:
        return f"rgba(0, 0, 0, {alpha})"
