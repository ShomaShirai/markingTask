_current_user_name: str | None = None


def set_current_user(name: str | None) -> None:
    global _current_user_name
    _current_user_name = name if name is not None and name.strip() else None


def get_current_user() -> str | None:
    return _current_user_name
