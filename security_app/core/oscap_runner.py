import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Dict

from security_app.models import Rule
from security_app.reporting.stats import compute_stats
from security_app.utils.log import internal_logger

class OscapNotInstalledError(Exception):
    pass

def is_oscap_installed() -> bool:
    return shutil.which("oscap") is not None

def run_oscap(file_path: str, rules: list[Rule]) -> dict[str, Any]:
    """
    Chạy oscap để đánh giá XCCDF/Datastream file.
    Trả về stats dictionary tương thích với security_app pipeline.
    """
    if not is_oscap_installed():
        raise OscapNotInstalledError(
            "Lệnh 'oscap' không tồn tại. Vui lòng cài đặt OpenSCAP bằng lệnh:\n"
            "sudo apt-get update && sudo apt-get install libopenscap8"
        )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        res_file = os.path.join(tmpdir, "oscap_results.xml")
        
        cmd = ["oscap", "xccdf", "eval", "--results", res_file, file_path]
        
        internal_logger.info(f"Running OpenSCAP: {' '.join(cmd)}")
        try:
            # oscap có thể trả về 0 (pass all), 1 (error), 2 (fail some rules)
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            internal_logger.error(f"Error executing oscap: {e}")
        
        if not os.path.exists(res_file):
            raise RuntimeError("oscap chạy thất bại, không tạo ra file results.xml")
        
        return parse_oscap_results(res_file, rules)

def parse_oscap_results(results_file: str, rules: list[Rule]) -> dict[str, Any]:
    """Parse file results.xml của oscap để map vào cấu trúc stats."""
    tree = ET.parse(results_file)
    root = tree.getroot()
    
    ns_url = "http://checklists.nist.gov/xccdf/1.2"
    if root.tag.startswith("{") and "xccdf/1.1" in root.tag:
        ns_url = "http://checklists.nist.gov/xccdf/1.1"
    ns = {"xccdf": ns_url}
    
    # Build dictionary id -> result
    oscap_results = {}
    for rr in root.findall(".//xccdf:rule-result", ns):
        rid = rr.get("idref")
        result_elem = rr.find("xccdf:result", ns)
        if rid and result_elem is not None:
            rtext = (result_elem.text or "").strip().lower()
            oscap_results[rid] = rtext
    
    # Map back to rules
    all_results = []
    
    for i, rule in enumerate(rules):
        rid = rule.id
        status = oscap_results.get(rid, "notapplicable")
        
        if status in ("pass", "fixed"):
            num_ok = 1
            num_fail = 0
        elif status in ("fail", "error", "unknown"):
            num_ok = 0
            num_fail = 1
        else:
            # notapplicable, notselected, informational ...
            num_ok = 0
            num_fail = 0
            
        # Thêm 1 dummy command để giao diện CLI không bị lỗi 0 commands
        # security_app.reporting.stats compute_stats sẽ đếm cmds
        # Nên chúng ta mô phỏng có 1 command tương ứng rule đó.
        cmds = []
        if num_ok > 0 or num_fail > 0:
            cmds = [{
                "cmd": f"OVAL Check: {rid}",
                "rc": 0 if num_fail == 0 else 1,
                "duration": 0.1,
                "stdout": f"OpenSCAP Result: {status}",
                "stderr": "",
                "status": "ok" if num_fail == 0 else "fail"
            }]

        all_results.append({
            "rule_index": i + 1,
            "rule": {
                "id": rule.id,
                "title": rule.title,
                "severity": rule.severity,
                "description": rule.description,
                "check": rule.check,
                "fix": rule.fix,
            },
            "num_ok": num_ok,
            "num_fail": num_fail,
            "cmds": cmds
        })
    
    stats = compute_stats(all_results)
    return stats
