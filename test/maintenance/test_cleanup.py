# tests/maintenance/test_cleanup.py
import pytest
from security_app.maintenance.cleanup import _human

@pytest.mark.parametrize("bytes_in, expected_str", [
    (100, "100.0 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (1024 * 1024, "1.0 MB"),
    (1024 * 1024 * 5.2, "5.2 MB"),
    (1024**3 * 2, "2.0 GB"),
    (1024**4 * 1.1, "1.1 TB"),
    (0, "0.0 B"),
    (-100, "-100.0 B"), # Có thể không mong muốn, nhưng test hành vi
])
def test_human_readable_size(bytes_in, expected_str):
    assert _human(bytes_in) == expected_str

# Lưu ý: Kiểm thử các hàm như prune_runs, prune_tmp sẽ phức tạp hơn
# vì chúng tương tác với hệ thống file. Bạn cần sử dụng mocking
# (ví dụ: thư viện `unittest.mock` hoặc `pytest-mock`) để giả lập
# các hàm os.path.exists, os.listdir, os.stat, shutil.rmtree, v.v.
# Hoặc sử dụng `tmp_path` fixture của pytest để tạo cây thư mục tạm thời.
