from pyshop import ShopSession

from fastapi import HTTPException

import datetime as dt

from typing import List


class UserSession:

    def __init__(self, username: str, expires: dt.datetime):
        self.username = username
        self.expires = expires
        self.shopsessions = {}
        self.shopsessions_time_resolution_is_set = {}
        self.sessioncounter = 0

    def add_shop_session(self) -> int:
        self.sessioncounter += 1
        self.shopsessions[self.sessioncounter] = ShopSession(license_path='', silent=False, log_file='')
        self.shopsessions_time_resolution_is_set[self.sessioncounter] = False
        return self.sessioncounter

    def remove_shop_session(self, session_id: int) -> bool:
        if session_id in self.shopsessions:
            session = self.shopsessions.pop(session_id)
            del session
            return True
        else:
            return False

    def get_shop_session(self, session_id: int) -> ShopSession:
        if session_id in self.shopsessions:
            return self.shopsessions[session_id]
        else:
            return None

    def list_shop_sessions(self) -> List[int]:
        return list(self.shopsessions.keys())

    def update_expiry_time(self, expires: dt.datetime):
        self.expires = expires
        dt.datetime.utcnow()


class SessionManager:

    usersessions = {}

    @staticmethod
    def get_user_session_list() -> List[str]:
        return list(SessionManager.usersessions.keys())

    @staticmethod
    def add_user_session(username: str, expires) -> UserSession:
        SessionManager.usersessions[username] = UserSession(username, expires)
        return SessionManager.usersessions[username]

    @staticmethod
    def remove_user_session(username) -> bool:
        if username in SessionManager.usersessions:
            SessionManager.usersessions.pop(username)
            return True
        else:
            return False

    @staticmethod
    def get_user_session(username: str) -> UserSession:
        if username in SessionManager.usersessions:
            return SessionManager.usersessions[username]
        else:
            return None

    @staticmethod
    def list_shop_sessions(username: str) -> List[int]:
        usersession = SessionManager.get_user_session(username)
        if usersession:
            return list(usersession.list_shop_sessions())
        else:
            return []

    @staticmethod
    def get_shop_session(username: str, session_id: int, raises=False) -> ShopSession:

        usersession = SessionManager.get_user_session(username)

        if usersession:
            sess = usersession.get_shop_session(int(session_id))
            if sess is None and raises:
                raise HTTPException(400, f'Session {{{session_id}}} does not exist.')
            return sess
        elif raises:
            raise HTTPException(400, f'User {{{username}}} does not exist.')

        return None

    @staticmethod
    def add_shop_session(username: str) -> int:
        usersession = SessionManager.get_user_session(username)
        if usersession:
            idd = usersession.add_shop_session()
            return idd
        else:
            return None

    @staticmethod
    def remove_shop_session(username: str, session_id: int) -> bool:
        usersession = SessionManager.get_user_session(username)
        if usersession:
            return usersession.remove_shop_session(int(session_id))
        else:
            return False

    @staticmethod
    def cleanup_user_sessions() -> None:
        for user in SessionManager.get_user_session_list():
            usersession = SessionManager.get_user_session(user)
            if dt.datetime.utcnow() > usersession.expires:
                SessionManager.remove_user_session(user)

    @staticmethod
    def update_expiry_time(username: str, expires: dt.datetime) -> None:
        usersession = SessionManager.get_user_session(username)
        usersession.update_expiry_time(expires)
    
    @staticmethod
    def get_model_object_type(username: str, session_id: int, object_type: str):
        model = SessionManager.get_shop_session(username, session_id, raises=True).model
        if object_type not in model._all_types:
            raise HTTPException(400, f'object_type {{{object_type}}} is not implemented.')
        return model[object_type]
            
    @staticmethod
    def get_model_object_type_object_name(username: str, session_id: int, object_type: str, object_name: str):
        model_object_type = SessionManager.get_model_object_type(username, session_id, object_type)
        if object_name not in model_object_type._names:
            raise HTTPException(400, f'object_name {{{object_name}}} is not an instance of object_type {{{object_type}}}.')
        return model_object_type[object_name]