"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi.
"""
from datetime import datetime, timedelta
import functools

# ============================================================
# MOCK DATABASE (thay bằng gọi API/DB thật khi tích hợp)
# ============================================================

MOCK_ORDERS_DB = {
    "DH001": {
        "khach_hang": "Nguyễn Văn A",
        "sdt": "0901234567",
        "trang_thai": "Đã giao",
        "ngay_dat": "2026-07-15",
        "ngay_giao": "2026-07-18",
        "san_pham": [{"ma": "SP-DT01", "ten": "Tai nghe Bluetooth X1", "gia": 590000, "so_luong": 1}],
        "tong_tien": 590000,
        "ma_van_don": "VD998877",
    },
    "DH002": {
        "khach_hang": "Trần Thị B",
        "sdt": "0912345678",
        "trang_thai": "Đang giao",
        "ngay_dat": "2026-07-25",
        "ngay_giao": None,
        "san_pham": [{"ma": "SP-TT02", "ten": "Áo thun Cotton", "gia": 199000, "so_luong": 2}],
        "tong_tien": 398000,
        "ma_van_don": "VD998878",
    },
}

MOCK_PRODUCT_POLICY = {
    "SP-DT01": {"loai": "Điện tử", "han_doi_tra_ngay": 7, "dieu_kien": "Chỉ áp dụng nếu lỗi do NSX, còn nguyên hộp"},
    "SP-TT02": {"loai": "Thời trang", "han_doi_tra_ngay": 30, "dieu_kien": "Chưa qua sử dụng, còn tem mác"},
}

MOCK_RETURN_REQUESTS = {}  # ma_yeu_cau -> {...}
_return_counter = 0


# ============================================================
# NHÓM 1 — TRA CỨU ĐƠN HÀNG
# ============================================================

def tra_cuu_don_hang(ma_don_hang: str) -> str:
    """
    Tra cứu chi tiết một đơn hàng theo mã đơn.

    Args:
        ma_don_hang (str): Mã đơn hàng (Ví dụ: 'DH001')

    Returns:
        str: Thông tin chi tiết đơn hàng, hoặc thông báo lỗi nếu không tìm thấy
    """
    don = MOCK_ORDERS_DB.get(ma_don_hang.upper())
    if not don:
        return f"LỖI: Không tìm thấy đơn hàng '{ma_don_hang}'."

    sp_list = "\n".join(
        f"  - {sp['ten']} (x{sp['so_luong']}) - {sp['gia']:,} VNĐ" for sp in don["san_pham"]
    )
    return (
        f"Đơn hàng {ma_don_hang.upper()}:\n"
        f"Trạng thái: {don['trang_thai']}\n"
        f"Ngày đặt: {don['ngay_dat']} | Ngày giao: {don['ngay_giao'] or 'Chưa giao'}\n"
        f"Sản phẩm:\n{sp_list}\n"
        f"Tổng tiền: {don['tong_tien']:,} VNĐ"
    )


def tra_cuu_don_hang_theo_khach_hang(so_dien_thoai: str) -> str:
    """
    Tìm các đơn hàng gần nhất theo số điện thoại khách hàng.

    Args:
        so_dien_thoai (str): Số điện thoại đã dùng khi đặt hàng

    Returns:
        str: Danh sách mã đơn hàng khớp, hoặc thông báo không tìm thấy
    """
    ket_qua = [ma for ma, don in MOCK_ORDERS_DB.items() if don["sdt"] == so_dien_thoai]
    if not ket_qua:
        return f"LỖI: Không tìm thấy đơn hàng nào gắn với số điện thoại '{so_dien_thoai}'."
    return f"Tìm thấy {len(ket_qua)} đơn hàng: {', '.join(ket_qua)}"


def tra_cuu_van_chuyen(ma_van_don: str) -> str:
    """
    Tra cứu trạng thái vận chuyển thực tế theo mã vận đơn.

    Args:
        ma_van_don (str): Mã vận đơn (Ví dụ: 'VD998877')

    Returns:
        str: Trạng thái vận chuyển hiện tại
    """
    for don in MOCK_ORDERS_DB.values():
        if don["ma_van_don"] == ma_van_don.upper():
            return f"Vận đơn {ma_van_don.upper()}: {don['trang_thai']} (cập nhật gần nhất)."
    return f"LỖI: Không tìm thấy vận đơn '{ma_van_don}'."


# ============================================================
# NHÓM 2 — KIỂM TRA CHÍNH SÁCH ĐỔI TRẢ
# ============================================================

def kiem_tra_dieu_kien_doi_tra(ma_don_hang: str) -> str:
    """
    Kiểm tra đơn hàng có còn trong hạn đổi trả hay không.

    Args:
        ma_don_hang (str): Mã đơn hàng cần kiểm tra

    Returns:
        str: Kết quả đủ/không đủ điều kiện kèm lý do
    """
    don = MOCK_ORDERS_DB.get(ma_don_hang.upper())
    if not don:
        return f"LỖI: Không tìm thấy đơn hàng '{ma_don_hang}'."
    if don["trang_thai"] != "Đã giao":
        return f"KHÔNG ĐỦ ĐIỀU KIỆN: Đơn hàng chưa giao xong (trạng thái: {don['trang_thai']})."

    ngay_giao = datetime.strptime(don["ngay_giao"], "%Y-%m-%d")
    san_pham_dau = don["san_pham"][0]["ma"]
    chinh_sach = MOCK_PRODUCT_POLICY.get(san_pham_dau, {"han_doi_tra_ngay": 7})
    han = ngay_giao + timedelta(days=chinh_sach["han_doi_tra_ngay"])
    hom_nay = datetime.now()

    if hom_nay <= han:
        return f"ĐỦ ĐIỀU KIỆN: Còn hạn đến {han.strftime('%Y-%m-%d')} (chính sách {chinh_sach['han_doi_tra_ngay']} ngày)."
    return f"KHÔNG ĐỦ ĐIỀU KIỆN: Đã quá hạn đổi trả (hết hạn {han.strftime('%Y-%m-%d')})."


def tra_cuu_chinh_sach_san_pham(ma_san_pham: str) -> str:
    """
    Lấy chính sách đổi trả riêng theo loại sản phẩm.

    Args:
        ma_san_pham (str): Mã sản phẩm (Ví dụ: 'SP-DT01')

    Returns:
        str: Mô tả chính sách đổi trả áp dụng cho sản phẩm
    """
    cs = MOCK_PRODUCT_POLICY.get(ma_san_pham.upper())
    if not cs:
        return f"LỖI: Không tìm thấy chính sách cho sản phẩm '{ma_san_pham}'."
    return (
        f"Sản phẩm {ma_san_pham.upper()} ({cs['loai']}): "
        f"Hạn đổi trả {cs['han_doi_tra_ngay']} ngày. Điều kiện: {cs['dieu_kien']}."
    )


def tinh_toan_hoan_tien(ma_don_hang: str, ly_do: str) -> str:
    """
    Ước tính số tiền hoàn lại dựa trên lý do trả hàng.

    Args:
        ma_don_hang (str): Mã đơn hàng
        ly_do (str): Lý do trả hàng (Ví dụ: 'lỗi nhà sản xuất', 'đổi ý')

    Returns:
        str: Số tiền hoàn lại ước tính và phí áp dụng (nếu có)
    """
    don = MOCK_ORDERS_DB.get(ma_don_hang.upper())
    if not don:
        return f"LỖI: Không tìm thấy đơn hàng '{ma_don_hang}'."

    tong = don["tong_tien"]
    ly_do_lower = ly_do.lower()
    if "lỗi" in ly_do_lower or "nsx" in ly_do_lower:
        return f"Hoàn tiền 100%: {tong:,} VNĐ (miễn phí do lỗi nhà sản xuất)."
    phi_xu_ly = round(tong * 0.05)
    return (
        f"Hoàn tiền dự kiến: {tong - phi_xu_ly:,} VNĐ "
        f"(trừ phí xử lý 5% = {phi_xu_ly:,} VNĐ do đổi ý)."
    )


# ============================================================
# NHÓM 3 — THỰC HIỆN HÀNH ĐỘNG (có side-effect)
# ============================================================

def tao_yeu_cau_doi_tra(ma_don_hang: str, loai_yeu_cau: str, ly_do: str) -> str:
    """
    Tạo yêu cầu đổi/trả hàng mới cho một đơn hàng.

    Args:
        ma_don_hang (str): Mã đơn hàng
        loai_yeu_cau (str): 'đổi hàng' hoặc 'trả hàng hoàn tiền'
        ly_do (str): Lý do đổi/trả

    Returns:
        str: Mã yêu cầu (RMA) vừa tạo để khách theo dõi
    """
    global _return_counter
    if ma_don_hang.upper() not in MOCK_ORDERS_DB:
        return f"LỖI: Không tìm thấy đơn hàng '{ma_don_hang}'."

    _return_counter += 1
    ma_yeu_cau = f"RMA{_return_counter:04d}"
    MOCK_RETURN_REQUESTS[ma_yeu_cau] = {
        "ma_don_hang": ma_don_hang.upper(),
        "loai": loai_yeu_cau,
        "ly_do": ly_do,
        "trang_thai": "Đang chờ duyệt",
        "ngay_tao": datetime.now().strftime("%Y-%m-%d"),
    }
    return f"Đã tạo yêu cầu {ma_yeu_cau} ({loai_yeu_cau}) cho đơn {ma_don_hang.upper()}. Trạng thái: Đang chờ duyệt."


def tra_cuu_trang_thai_yeu_cau_doi_tra(ma_yeu_cau: str) -> str:
    """
    Tra cứu tiến độ xử lý của một yêu cầu đổi/trả đã tạo.

    Args:
        ma_yeu_cau (str): Mã yêu cầu (Ví dụ: 'RMA0001')

    Returns:
        str: Trạng thái xử lý hiện tại
    """
    yc = MOCK_RETURN_REQUESTS.get(ma_yeu_cau.upper())
    if not yc:
        return f"LỖI: Không tìm thấy yêu cầu '{ma_yeu_cau}'."
    return f"Yêu cầu {ma_yeu_cau.upper()} ({yc['loai']}): {yc['trang_thai']} (tạo ngày {yc['ngay_tao']})."


def huy_don_hang(ma_don_hang: str) -> str:
    """
    Huỷ đơn hàng nếu đơn chưa chuyển sang trạng thái đang giao.

    Args:
        ma_don_hang (str): Mã đơn hàng cần huỷ

    Returns:
        str: Kết quả huỷ đơn thành công hay không
    """
    don = MOCK_ORDERS_DB.get(ma_don_hang.upper())
    if not don:
        return f"LỖI: Không tìm thấy đơn hàng '{ma_don_hang}'."
    if don["trang_thai"] in ("Đang giao", "Đã giao"):
        return f"KHÔNG THỂ HUỶ: Đơn hàng đang ở trạng thái '{don['trang_thai']}'."
    don["trang_thai"] = "Đã huỷ"
    return f"Đã huỷ đơn hàng {ma_don_hang.upper()} thành công."


def tra_cuu_diem_gui_tra_hang(khu_vuc: str) -> str:
    """
    Tìm điểm gửi trả hàng/bưu cục gần nhất theo khu vực.

    Args:
        khu_vuc (str): Tên quận/thành phố (Ví dụ: 'Quận 1, TP.HCM')

    Returns:
        str: Danh sách điểm gửi trả gần khu vực
    """
    return (
        f"Điểm gửi trả hàng gần '{khu_vuc}':\n"
        f"1. Bưu cục Trung tâm - 8h-20h, T2-CN\n"
        f"2. Điểm gửi hàng Viettel Post - 8h-18h, T2-T7"
    )


# ============================================================
# NHÓM 4 — HỖ TRỢ & AN TOÀN (guardrail)
# ============================================================

def chuyen_nhan_vien_ho_tro(ma_don_hang: str, ly_do: str) -> str:
    """
    Escalate ca xử lý sang nhân viên thật khi ngoài phạm vi tự động.

    Args:
        ma_don_hang (str): Mã đơn hàng liên quan
        ly_do (str): Lý do cần escalate (Ví dụ: 'nghi gian lận', 'khiếu nại giá trị lớn')

    Returns:
        str: Xác nhận đã chuyển ca cho nhân viên hỗ trợ
    """
    return f"Đã chuyển đơn {ma_don_hang} cho nhân viên hỗ trợ xử lý. Lý do: {ly_do}. Ticket sẽ được phản hồi trong 24h."


def gui_thong_bao_xac_nhan(kenh: str, noi_dung: str) -> str:
    """
    Gửi thông báo xác nhận (email/SMS) tới khách hàng.

    Args:
        kenh (str): 'email' hoặc 'sms'
        noi_dung (str): Nội dung thông báo cần gửi

    Returns:
        str: Xác nhận đã gửi thông báo
    """
    return f"Đã gửi thông báo qua {kenh}: \"{noi_dung}\""


def safe_tool(func):
    """
    Bọc một tool function: nếu bên trong ném exception bất kỳ (KeyError, AttributeError,
    ValueError khi parse ngày tháng, v.v.) thì bắt lại và trả về chuỗi "LỖI: ..." thay vì
    để exception lan lên làm crash vòng lặp ReAct của agent.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return f"LỖI: Tool '{func.__name__}' gặp sự cố khi thực thi ({type(e).__name__}: {e})."
    return wrapper


# Danh sách các tool được đăng ký để Agent sử dụng
# (mỗi tool được bọc qua safe_tool để đảm bảo luôn trả về string, không bao giờ crash)
_RAW_TOOLS = {
    "tra_cuu_don_hang": tra_cuu_don_hang,
    "tra_cuu_don_hang_theo_khach_hang": tra_cuu_don_hang_theo_khach_hang,
    "tra_cuu_van_chuyen": tra_cuu_van_chuyen,
    "kiem_tra_dieu_kien_doi_tra": kiem_tra_dieu_kien_doi_tra,
    "tra_cuu_chinh_sach_san_pham": tra_cuu_chinh_sach_san_pham,
    "tinh_toan_hoan_tien": tinh_toan_hoan_tien,
    "tao_yeu_cau_doi_tra": tao_yeu_cau_doi_tra,
    "tra_cuu_trang_thai_yeu_cau_doi_tra": tra_cuu_trang_thai_yeu_cau_doi_tra,
    "huy_don_hang": huy_don_hang,
    "tra_cuu_diem_gui_tra_hang": tra_cuu_diem_gui_tra_hang,
    "chuyen_nhan_vien_ho_tro": chuyen_nhan_vien_ho_tro,
    "gui_thong_bao_xac_nhan": gui_thong_bao_xac_nhan,
}
AVAILABLE_TOOLS = {name: safe_tool(fn) for name, fn in _RAW_TOOLS.items()}


"""
Những điều cần lưu ý:

1. MAX_ITERATIONS = 3 trong prompts.py sẽ không đủ. Một luồng đổi trả hợp lệ thường cần ít nhất: 
tra_cuu_don_hang → kiem_tra_dieu_kien_doi_tra → tao_yeu_cau_doi_tra = 3 vòng, chưa tính bước xác nhận với khách. Nên tăng lên ~5-6 nếu dùng bộ tool này.

2. Side-effect vs read-only phải phân biệt rõ trong prompt. tao_yeu_cau_doi_tra và huy_don_hang ghi dữ liệu thật — agent cần được chỉ dẫn (trong REACT_SYSTEM_PROMPT) 
là phải chạy xong kiem_tra_dieu_kien_doi_tra và xác nhận lại với khách trước khi gọi các tool này, không được gọi ngay khi khách vừa nói "tôi muốn trả hàng".

3. Không để agent tự "duyệt" hoàn tiền giá trị lớn. tinh_toan_hoan_tien chỉ nên là ước tính tham khảo; 
các case hoàn tiền lớn/nghi ngờ nên bắt buộc qua chuyen_nhan_vien_ho_tro — đây là lý do tool này tồn tại như một guardrail, không phải tool "cho vui".

4. Rò rỉ dữ liệu khách hàng khác. tra_cuu_don_hang_theo_khach_hang tra theo SĐT — cần đảm bảo agent không trả thông tin đơn hàng cho người không xác thực được là chủ đơn 
(trong bản mock chưa có xác thực, cần bổ sung khi nối API thật).

5. Trạng thái ngày tháng dùng datetime.now() trong kiem_tra_dieu_kien_doi_tra — khi test cần lưu ý giờ hệ thống, và khi tích hợp thật nên lấy 
timezone chuẩn (Asia/Ho_Chi_Minh) thay vì giờ server mặc định.

6. Tính idempotent còn thiếu: gọi tao_yeu_cau_doi_tra nhiều lần cho cùng 1 đơn sẽ tạo nhiều RMA trùng — 
nên thêm kiểm tra "đơn đã có yêu cầu đang xử lý chưa" trước khi tạo mới, để tránh agent lỡ gọi lặp lại do reasoning loop.

7. Cần cập nhật song song REACT_SYSTEM_PROMPT để liệt kê đủ 12 tool theo format tên[tham_số], 
nếu không agent sẽ không biết các tool này tồn tại dù đã đăng ký trong AVAILABLE_TOOLS.
"""


