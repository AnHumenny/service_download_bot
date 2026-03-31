async def check_args(text: str) -> str:
    """Generates a path from the command arguments."""
    parts = text.split()[1:]
    if not parts:
        return ""
    return "/".join(parts)
