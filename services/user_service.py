from typing import Optional, Union
from domain.type import User

_current_user: Optional[User] = None


def set_current_user(user_or_name: Union[User, str, None]) -> None:
    global _current_user
    if isinstance(user_or_name, User):
        _current_user = user_or_name
    elif isinstance(user_or_name, str):
        name = user_or_name.strip()
        _current_user = User(name=name) if name else None
    else:
        _current_user = None


def get_current_user() -> Optional[User]:
    return _current_user
