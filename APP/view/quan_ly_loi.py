for idx, row in page_df.iterrows():
                db_id = row.get('db_id')
                stt_hien_thi = start_idx + idx + 1
                ngay_val = row.get('Ngày', '')
                nhan_su_val = row.get('Nhân Sự', '')
                phan_loai_val = row.get('Phân Loại Lỗi', '')
                so_luong_val = row.get('Số Lượng', 0)
                ghi_chu_val = row.get('Ghi Chú', '')
                img_url_val = row.get("Số Ảnh Đính Kèm", "")

                row_c1, row_c2 = st.columns([4, 1])
                with row_c1:
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.85); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 4px; font-size: 0.9rem;">
                        <b>STT: {stt_hien_thi} (ID: {db_id})</b> &nbsp;|&nbsp; 📅 <b>Ngày:</b> {ngay_val} &nbsp;|&nbsp; 👤 <b>Nhân sự:</b> {nhan_su_val}<br>
                        📌 <b>Loại lỗi:</b> <span style="color: #d9534f; font-weight: bold;">{phan_loai_val}</span> &nbsp;|&nbsp; 📦 <b>Số lượng:</b> {so_luong_val} Cái<br>
                        💬 <i>Ghi chú:</i> {ghi_chu_val if ghi_chu_val and str(ghi_chu_val).lower() != 'nan' else 'Không có ghi chú'}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Ô checkbox tích chọn xóa nằm ngay dưới khung thông tin giống mẫu
                    if st.checkbox(f"Chọn xóa bản ghi STT {stt_hien_thi}", key=f"chk_loi_{db_id}"):
                        selected_db_ids.append(db_id)
                        
                with row_c2:
                    if img_url_val and isinstance(img_url_val, str) and img_url_val.strip():
                        urls = [u.strip() for u in img_url_val.split(",") if u.strip()]
                        if urls:
                            sub_cols = st.columns(min(len(urls), 4), gap="small")
                            for i, u in enumerate(urls):
                                with sub_cols[i]:
                                    try:
                                        if u.startswith("http://") or u.startswith("https://"):
                                            with st.popover("🔍", help="Xem ảnh lớn"): 
                                                st.image(u, use_container_width=True)
                                            st.image(u, width=40)
                                        else:
                                            st.caption("⚠️ Không ảnh")
                                    except Exception:
                                        st.caption("❌ Lỗi")
                    else:
                        st.markdown("<small style='color: gray;'>Không ảnh</small>", unsafe_allow_html=True)

                st.markdown("---")
