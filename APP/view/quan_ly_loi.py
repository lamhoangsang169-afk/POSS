import streamlit as st
import pandas as pd
import datetime
import os
import requests
import database as db

# ==================== HÀM PHỤ TRỢ: LẤY DUNG LƯỢNG ẢNH AN TOÀN ====================
@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_image_size(u):
    try:
        if u.startswith("http://") or u.startswith("https://"):
            res = requests.head(u, timeout=0.8)
            length = int(res.headers.get('Content-Length', 0))
            if length > 0:
                if length >= 1024 * 1024:
                    return f"~{length / (1024 * 1024):.1f} MB"
                return f"~{max(1, int(length / 1024))} KB"
        elif os.path.exists(u):
            length = os.path.getsize(u)
            if length >= 1024 * 1024:
                return f"~{length / (1024 * 1024):.1f} MB"
            return f"~{max(1, int(length / 1024))} KB"
    except Exception:
        pass
    return "~150 KB"

# Định nghĩa modal dialog hiển thị ảnh kích thước đầy đủ khi bấm nút xem lớn
@st.dialog("Chi Tiết Hình Ảnh Lỗi")
def show_image_dialog(img_url):
    try:
        st.image(img_url, use_container_width=True)
    except Exception:
        st.error("Không thể tải ảnh phóng to.")
    if st.button("Đóng", use_container_width=True):
        st.rerun()

def render_quan_ly_loi(current_menu_name):
    if "loi_start_date" not in st.session_state:
        st.session_state.loi_start_date = datetime.date.today()
    if "loi_end_date" not in st.session_state:
        st.session_state.loi_end_date = datetime.date.today()

    if "loi_filter_ns" not in st.session_state:
        st.session_state.loi_filter_ns = "Tất cả"
    if "loi_filter_cat" not in st.session_state:
        st.session_state.loi_filter_cat = "Tất cả"
    if "loi_page_num" not in st.session_state:
        st.session_state.loi_page_num = 1

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.header(f"🛠️ {current_menu_name}")
    with col_h2:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True, key="btn_refresh_loi"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("### ⚠️ Khai Báo Lỗi Phát Sinh")
    
    raw_cats = db.get_error_categories_db()
    ds_loai_loi_hien_tai = list(raw_cats) if isinstance(raw_cats, (list, tuple)) else ["Sản phẩm hỏng", "Lỗi nguyên vật liệu", "Lỗi thao tác", "Lỗi máy móc / thiết bị", "Khác"]

    with st.form("form_khai_bao_loi", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ngay_phat_sinh = st.date_input("Ngày phát sinh", value=datetime.date.today(), key="input_ngay_loi")
        with col2:
            staff_options = ["--- Vui lòng chọn nhân sự ---"] + st.session_state.get("staff_list", [])
            nhan_su_phat_hien = st.selectbox("Nhân sự chịu trách nhiệm/phát hiện", staff_options, key="select_nhan_su_loi")
        with col3:
            phan_loai_loi = st.selectbox("Phân loại lỗi", ds_loai_loi_hien_tai, key="select_phan_loai_loi")
            
        uploaded_images = st.file_uploader(
            "Tải ảnh đính kèm (Tối đa nhiều ảnh)", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True, 
            key="uploader_loi_images"
        )
            
        col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
        with col_s1:
            so_luong_loi = st.number_input("Số lượng lỗi", min_value=0.0, value=0.0, step=0.1, format="%.2f", key="num_so_luong_loi")
        with col_s2:
            he_so_diem = st.number_input("Hệ số (Điểm/lỗi)", min_value=0.0, value=1.0, step=0.1, format="%.2f", key="num_he_so_loi")
        with col_s3:
            ghi_chu_loi = st.text_input("Ghi chú", placeholder="Nhập ghi chú nguyên nhân / hướng khắc phục...", key="txt_ghi_chu_loi")
            
        tong_diem_tam_tinh = so_luong_loi * he_so_diem
        st.markdown(f"📊 **Tạm tính tổng điểm lỗi:** `{so_luong_loi} × {he_so_diem} = **{tong_diem_tam_tinh:,.2f} điểm**`")
            
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚨 Ghi Nhận Lỗi Sản Xuất", use_container_width=True)

    if submitted:
        if nhan_su_phat_hien == "--- Vui lòng chọn nhân sự ---":
            st.warning("⚠ Vui lòng chọn nhân sự liên quan!")
        elif so_luong_loi <= 0:
            st.warning("⚠️ Vui lòng nhập số lượng sản phẩm lỗi lớn hơn 0!")
        else:
            uploaded_urls = ""
            if uploaded_images:
                uploaded_urls = db.upload_multiple_images_to_storage(uploaded_images)
            
            tong_diem_ghi_nhan = so_luong_loi * he_so_diem
            
            response = db.add_error_log_with_images_db(
                ngay=ngay_phat_sinh,
                nhan_su=nhan_su_phat_hien,
                phan_loai_loi=phan_loai_loi,
                so_luong=so_luong_loi,
                ghi_chu=ghi_chu_loi,
                images_base64_str=uploaded_urls,
                he_so_diem=he_so_diem,
                tong_diem=tong_diem_ghi_nhan
            )
            
            if response is not None:
                st.cache_data.clear()
                st.success("✅ Đã ghi nhận báo cáo lỗi, tính điểm và lưu lên hệ thống thành công!")
                st.rerun()

    with st.expander("⚙️ Tùy Chỉnh Danh Mục Loại Lỗi (Thêm/Bớt)", expanded=False):
        current_cats = list(db.get_error_categories_db())
        
        with st.form("form_add_loi_cat"):
            st.markdown("##### ➕ Thêm loại lỗi mới")
            new_loai_loi = st.text_input("Nhập tên loại lỗi mới...", placeholder="Nhập tên loại lỗi...")
            btn_add_cat = st.form_submit_button("Thêm Loại Lỗi", use_container_width=True)
            
            if btn_add_cat:
                clean_name = new_loai_loi.strip()
                if not clean_name:
                    st.error("⚠️ Vui lòng nhập tên loại lỗi!")
                elif clean_name in current_cats:
                    st.warning("⚠️ Loại lỗi này đã tồn tại!")
                else:
                    current_cats.append(clean_name)
                    try:
                        db.save_error_categories_db(current_cats)
                        st.cache_data.clear()
                        st.success(f"✅ Đã thêm loại lỗi: '{clean_name}' vào Database thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi lưu danh mục lỗi: {e}")

        st.markdown("---")

        with st.form("form_del_loi_cat"):
            st.markdown("##### ➖ Xóa loại lỗi không dùng")
            loai_loi_can_xoa = st.selectbox("Chọn loại lỗi để xóa", current_cats, key="select_del_loi_box")
            btn_del_cat = st.form_submit_button("Xóa Loại Lỗi", use_container_width=True)
            
            if btn_del_cat:
                if len(current_cats) > 1:
                    if loai_loi_can_xoa in current_cats:
                        current_cats.remove(loai_loi_can_xoa)
                        try:
                            db.save_error_categories_db(current_cats)
                            st.cache_data.clear()
                            st.success(f"✅ Đã xóa loại lỗi: '{loai_loi_can_xoa}' khỏi Database thành công!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi lưu danh mục lỗi: {e}")
                else:
                    st.error("⚠️ Cần giữ lại ít nhất một phân loại lỗi!")

    st.markdown("---")
    st.subheader("📋 Danh Sách Lỗi & Bộ Lọc Nâng Cao")
    
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
    
    with f_col1:
        st.session_state.loi_start_date = st.date_input("Từ ngày", value=st.session_state.loi_start_date, key="widget_loi_start")
    with f_col2:
        st.session_state.loi_end_date = st.date_input("Đến ngày", value=st.session_state.loi_end_date, key="widget_loi_end")
    with f_col3:
        staff_filter_opts = ["Tất cả"] + st.session_state.get("staff_list", [])
        curr_ns_idx = staff_filter_opts.index(st.session_state.loi_filter_ns) if st.session_state.loi_filter_ns in staff_filter_opts else 0
        st.session_state.loi_filter_ns = st.selectbox("Lọc theo Nhân Sự", staff_filter_opts, index=curr_ns_idx, key="widget_loi_ns")

    df_loi = db.get_error_logs_db(limit_rows=2000)
    
    if not df_loi.empty:
        df_loi["Ngày_DT"] = pd.to_datetime(df_loi["Ngày"], errors="coerce").dt.date
        df_temp_date = df_loi[(df_loi["Ngày_DT"] >= st.session_state.loi_start_date) & (df_loi["Ngày_DT"] <= st.session_state.loi_end_date)]
        
        if st.session_state.loi_filter_ns != "Tất cả":
            df_temp_staff = df_temp_date[df_temp_date["Nhân Sự"] == st.session_state.loi_filter_ns]
            dynamic_cats = sorted(df_temp_staff["Phân Loại Lỗi"].dropna().unique().tolist())
        else:
            dynamic_cats = sorted(df_temp_date["Phân Loại Lỗi"].dropna().unique().tolist())
            
        cat_filter_opts = ["Tất cả"] + dynamic_cats
    else:
        cat_filter_opts = ["Tất cả"] + ds_loai_loi_hien_tai

    if st.session_state.loi_filter_cat not in cat_filter_opts:
        st.session_state.loi_filter_cat = "Tất cả"

    with f_col4:
        curr_cat_idx = cat_filter_opts.index(st.session_state.loi_filter_cat) if st.session_state.loi_filter_cat in cat_filter_opts else 0
        st.session_state.loi_filter_cat = st.selectbox("Lọc theo Phân Loại Lỗi", cat_filter_opts, index=curr_cat_idx, key="widget_loi_cat")
    with f_col5:
        st.session_state.loi_page_num = st.number_input("Trang hiển thị", min_value=1, value=st.session_state.loi_page_num, step=1, key="widget_loi_pagenum")

    if st.session_state.loi_start_date > st.session_state.loi_end_date:
        st.error("⚠️ Ngày bắt đầu không thể lớn hơn ngày kết thúc!")
        return
    
    if not df_loi.empty:
        filtered_df = df_loi[(df_loi["Ngày_DT"] >= st.session_state.loi_start_date) & (df_loi["Ngày_DT"] <= st.session_state.loi_end_date)]
        
        if st.session_state.loi_filter_ns != "Tất cả":
            filtered_df = filtered_df[filtered_df["Nhân Sự"] == st.session_state.loi_filter_ns]
            
        if st.session_state.loi_filter_cat != "Tất cả":
            filtered_df = filtered_df[filtered_df["Phân Loại Lỗi"] == st.session_state.loi_filter_cat]

        total_records = len(filtered_df)
        st.info(f"📅 Khoảng ngày có: {total_records} bản ghi lỗi")

        if total_records > 0:
            total_qty_filtered = 0.0
            total_points_filtered = 0.0
            
            for _, r_item in filtered_df.iterrows():
                q_val = float(r_item.get("Số Lượng", 0) or 0)
                total_qty_filtered += q_val
                
                h_val = r_item.get('Hệ Số Điểm', r_item.get('he_so_diem', 1.0))
                try:
                    h_val = float(h_val) if pd.notna(h_val) else 1.0
                except:
                    h_val = 1.0
                    
                t_val = r_item.get('Tổng Điểm', r_item.get('tong_diem', q_val * h_val))
                try:
                    t_val = float(t_val) if pd.notna(t_val) else q_val * h_val
                except:
                    t_val = q_val * h_val
                total_points_filtered += t_val

            st.markdown(
                f"""
                <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 12px; border-radius: 8px; text-align: center; font-size: 1.05rem; font-weight: bold; color: #0c5460; margin-bottom: 15px; margin-top: 10px;">
                    📊 Tổng số lượng lỗi: <span style="color: #d9534f;">{total_qty_filtered:,.1f}</span> &nbsp;|&nbsp; 🏆 Tổng số điểm: <span style="color: #0284c7;">{total_points_filtered:,.1f} điểm</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            page_size = 10
            total_pages = max(1, (total_records + page_size - 1) // page_size)
            
            if st.session_state.loi_page_num > total_pages:
                st.session_state.loi_page_num = total_pages

            start_idx = (st.session_state.loi_page_num - 1) * page_size
            end_idx = start_idx + page_size
            page_df = filtered_df.iloc[start_idx:end_idx].reset_index(drop=True)

            with st.form("form_danh_sach_loi"):
                st.markdown("---")
                col_act1, col_act2 = st.columns([2, 2])
                with col_act1:
                    btn_del_selected = st.form_submit_button("🗑️ Xóa các dòng đã chọn", use_container_width=True)
                with col_act2:
                    confirm_del_all = st.checkbox("Xác nhận xóa tất cả bản ghi trong trang này", value=False, key="chk_confirm_del_page")
                    btn_del_all = st.form_submit_button("🗑️ Xóa tất cả trang này", use_container_width=True)
                st.markdown("---")

                selected_items = []

                for idx, row in page_df.iterrows():
                    db_id = None
                    for key_candidate in ["db_id", "id"]:
                        if key_candidate in page_df.columns:
                            val = row.get(key_candidate)
                            if pd.notna(val) and str(val).strip() != "" and str(val).lower() != "none":
                                db_id = val
                                break

                    stt_hien_thi = start_idx + idx + 1
                    ngay_val = row.get('Ngày', '')
                    nhan_su_val = row.get('Nhân Sự', '')
                    phan_loai_val = row.get('Phân Loại Lỗi', '')
                    so_luong_val = row.get('Số Lượng', 0)
                    
                    he_so_val = row.get('Hệ Số Điểm', row.get('he_so_diem', 1.0))
                    try:
                        he_so_val = float(he_so_val) if pd.notna(he_so_val) else 1.0
                    except:
                        he_so_val = 1.0

                    tong_diem_val = row.get('Tổng Điểm', row.get('tong_diem', float(so_luong_val) * he_so_val))
                    try:
                        tong_diem_val = float(tong_diem_val) if pd.notna(tong_diem_val) else float(so_luong_val) * he_so_val
                    except:
                        tong_diem_val = float(so_luong_val) * he_so_val

                    ghi_chu_val = row.get('Ghi Chú', '')
                    img_url_val = row.get("Số Ảnh Đính Kèm", "")

                    row_c1, row_c2 = st.columns([4, 1])
                    with row_c1:
                        st.markdown(
                            f"""
                            <div style="background: rgba(255,255,255,0.85); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 4px; font-size: 0.9rem;">
                                <b>STT: {stt_hien_thi} (ID: {db_id if db_id else 'None'})</b> &nbsp;|&nbsp; 📅 <b>Ngày:</b> {ngay_val} &nbsp;|&nbsp; 👤 <b>Nhân sự:</b> {nhan_su_val}<br>
                                📌 <b>Loại lỗi:</b> <span style="color: #d9534f; font-weight: bold;">{phan_loai_val}</span> &nbsp;|&nbsp; 📦 <b>Số lượng:</b> {so_luong_val} &nbsp;|&nbsp; ⚙️ <b>Hệ số:</b> {he_so_val} &nbsp;|&nbsp; 🏆 <b>Tổng điểm:</b> <span style="color: #0284c7; font-weight: bold;">{tong_diem_val:,.1f} điểm</span><br>
                                💬 <i>Ghi chú:</i> {ghi_chu_val if ghi_chu_val and str(ghi_chu_val).lower() != 'nan' else 'Không có ghi chú'}
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        if st.checkbox(f"Chọn xóa bản ghi STT {stt_hien_thi}", key=f"chk_loi_item_{idx}"):
                            selected_items.append({
                                "db_id": db_id,
                                "ngay": str(ngay_val),
                                "nhan_su": str(nhan_su_val),
                                "phan_loai": str(phan_loai_val)
                            })
                            
                    with row_c2:
                        if img_url_val and isinstance(img_url_val, str) and img_url_val.strip():
                            urls = [u.strip() for u in img_url_val.split(",") if u.strip()]
                            if urls:
                                sub_cols = st.columns(min(len(urls), 4), gap="small")
                                for i, u in enumerate(urls):
                                    with sub_cols[i]:
                                        try:
                                            if u.startswith("http://") or u.startswith("https://"):
                                                st.image(u, width=40)
                                            else:
                                                st.caption("⚠️ Không ảnh")
                                            
                                            size_str = get_cached_image_size(u)
                                            st.markdown(f"<div style='text-align: center; font-size: 0.72rem; color: #64748b; margin-top: -4px;'>{size_str}</div>", unsafe_allow_html=True)
                                        except Exception:
                                            st.caption("❌ Lỗi")
                        else:
                            st.markdown("<small style='color: gray;'>Không ảnh</small>", unsafe_allow_html=True)

                    st.markdown("---")

                if btn_del_selected:
                    if selected_items:
                        try:
                            for item in selected_items:
                                curr_id = item.get("db_id")
                                if curr_id is not None and str(curr_id).strip() != "" and str(curr_id).lower() != "none":
                                    db.safe_supabase_call(lambda client, did=int(float(curr_id)): client.table("error_logs").delete().eq("id", did).execute())
                                else:
                                    db.safe_supabase_call(lambda client, it=item: client.table("error_logs").delete()
                                        .eq("ngay", str(it["ngay"]))
                                        .eq("nhan_su", str(it["nhan_su"]))
                                        .eq("phan_loai_loi", str(it["phan_loai"]))
                                        .execute())
                            st.cache_data.clear()
                            st.success(f"✅ Đã xóa thành công {len(selected_items)} bản ghi lỗi đã chọn!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa bản ghi: {e}")
                    else:
                        st.warning("⚠️ Vui lòng tích chọn ít nhất một dòng ở danh sách bên dưới để xóa!")

                if btn_del_all:
                    if confirm_del_all:
                        try:
                            for _, r in page_df.iterrows():
                                f_id = None
                                for key_candidate in ["db_id", "id"]:
                                    if key_candidate in page_df.columns:
                                        v = r.get(key_candidate)
                                        if pd.notna(v) and str(v).strip() != "" and str(v).lower() != "none":
                                            f_id = v
                                            break
                                if f_id is not None:
                                    db.safe_supabase_call(lambda client, fid=int(float(f_id)): client.table("error_logs").delete().eq("id", fid).execute())
                                else:
                                    db.safe_supabase_call(lambda client, row_data=r: client.table("error_logs").delete()
                                        .eq("ngay", str(row_data.get("Ngày", "")))
                                        .eq("nhan_su", str(row_data.get("Nhân Sự", "")))
                                        .eq("phan_loai_loi", str(row_data.get("Phân Loại Lỗi", "")))
                                        .execute())
                            st.cache_data.clear()
                            st.success(f"✅ Đã xóa toàn bộ bản ghi trong trang này!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa: {e}")
                    else:
                        st.warning("⚠ Vui lòng tích vào ô 'Xác nhận xóa tất cả bản ghi trong trang này'!")
        else:
            st.info("Không có bản ghi lỗi nào trong khoảng thời gian và bộ lọc đã chọn.")
    else:
        st.info("Chưa có bản ghi lỗi nào trong hệ thống.")
