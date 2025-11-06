#!/bin/bash

# Tên file để lưu kết quả thời gian
LOG_FILE="time_results2.log"

# Xóa file log cũ nếu tồn tại (tùy chọn)
> "$LOG_FILE"

echo "Bắt đầu chạy 10 lần..."

# Vòng lặp 10 lần (từ 1 đến 10)
for i in {1..20}
do
    echo "--- Lần chạy $i ---" | tee -a "$LOG_FILE"
    
    # Chạy lệnh 'time' và ghi (append) stderr vào file log
    # ( ... ) 2>> "$LOG_FILE" nhóm lệnh 'time' và chuyển hướng stderr của nó
    ( time security-app data/canonical_ubuntu_24.04_lts.json ) 2>> "$LOG_FILE"
    
    echo "Hoàn thành lần $i."
done

echo "Đã chạy xong 10 lần. Kết quả được lưu tại: $LOG_FILE"a
