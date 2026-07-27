import logging
import os
import sys

def get_internal_logger(name: str = "security_app") -> logging.Logger:
    """Khởi tạo cấu hình logger cho các internal errors."""
    logger = logging.getLogger(name)
    
    # Nếu đã cấu hình rồi thì không làm lại (tránh lặp handler)
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.WARNING)
    
    # 1. Ghi ra file
    log_dir = os.environ.get("SECAPP_LOGS_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(log_dir, "internal_errors.log"), encoding="utf-8")
    file_fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s")
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)
    
    # 2. In ra stderr (tuỳ chọn)
    # stream_handler = logging.StreamHandler(sys.stderr)
    # stream_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    # stream_handler.setFormatter(stream_fmt)
    # logger.addHandler(stream_handler)
    
    # Để tránh việc log quá nhiều ra stderr trong lúc user xem output terminal,
    # chúng ta chỉ log ra file. (Trừ khi debug bật)
    
    return logger

# Logger mặc định dùng cho toàn project
internal_logger = get_internal_logger()
