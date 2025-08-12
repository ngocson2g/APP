import re

def extract_all_commands(checktext: str):
    """
    Extract shell commands that start with "$ ".
    Supports multi-line commands that end with a backslash "\".
    Returns a list of complete commands (without the leading "$ ").
    """
    if not checktext:
        return []

    lines = checktext.splitlines()
    i = 0
    cmds = []
    current = None  # accumulating command string or None

    while i < len(lines):
        line = lines[i].strip()

        # start of a new command
        if line.startswith("$ "):
            # if we were accumulating, push previous one first
            if current:
                cmds.append(current.strip())
                current = None

            # start fresh (strip off the "$ ")
            current = line[2:].strip()

            # consume continuation lines
            while current.endswith("\\"):
                current = current[:-1].rstrip() + " "  # drop "\" and keep a space
                i += 1
                if i >= len(lines):
                    break
                next_line = lines[i].strip()
                # for continued lines, accept them as-is (even if not starting with "$")
                # but if they also start with "$ ", strip that to avoid duplication
                if next_line.startswith("$ "):
                    next_line = next_line[2:].strip()
                current += next_line

            # if no continuation at all, we’ll finalize below

        else:
            # not a command line; if we were in the middle of a command but hit
            # a non-continued line, finalize it.
            if current:
                cmds.append(current.strip())
                current = None

        i += 1

    # flush last command if file ends right after it
    if current:
        cmds.append(current.strip())

    return cmds
