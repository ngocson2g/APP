# security_app/core/command_extractor.py
from security_app.config import CMD_MARKER

def extract_all_commands(checktext: str):
    if not checktext:
        return []

    lines = checktext.splitlines()
    i = 0
    cmds = []
    current = None  # accumulating command string or None
    marker = CMD_MARKER

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        # start of a new command
        if line.startswith(marker):
            # flush cái trước (nếu có)
            if current:
                cmds.append(current.strip())
                current = None

            # bắt đầu mới (strip marker)
            current = line[len(marker):].strip()

            # consume continuation lines
            while current.endswith("\\"):
                current = current[:-1].rstrip() + " "
                i += 1
                if i >= len(lines):
                    break
                next_line = lines[i].strip()
                if next_line.startswith(marker):
                    next_line = next_line[len(marker):].strip()
                current += next_line
        else:
            # không phải dòng lệnh; nếu đang có current thì chốt
            if current:
                cmds.append(current.strip())
                current = None

        i += 1

    if current:
        cmds.append(current.strip())

    return cmds
