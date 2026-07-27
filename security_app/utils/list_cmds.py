from security_app.core.command_extractor import extract_all_commands
from security_app.models import Rule, Rule_cmd


def list_cmds(rules: list[Rule], marker: str = "$ ") -> list[Rule_cmd]:
    rule_cmds: list[Rule_cmd] = []   
    
    for r in rules:
        cmds = extract_all_commands(getattr(r, "check", "") or "")
        list_cmd: list[str] = []
        for c in cmds:
            list_cmd.append(c)  # Sửa: append(c) thay vì append(cmds)
        rule_cmds.append(Rule_cmd(id_rule=r.id, cmd=list_cmd))  # SỬA QUAN TRỌNG Ở ĐÂY
    return rule_cmds