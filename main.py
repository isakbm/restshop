from datetime import datetime, timedelta
from typing import Optional, List, Union, Any, Dict

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from fastapi.openapi.models import SchemaBase

from src.sessions import SessionManager
from enum import Enum

from fastapi import Path, Header

import pandas as pd
import numpy as np

from schemas import *

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(
    title="SHOP",
    description="SHOP RESTful, SINTEF Energy",
    version="0.1.0",
    openapi_tags=[
        {
            'name': 'Authentication',
            'description': 'Not required during development - Used to authenticate user.',
        },
        {
            'name': 'Session',
            'description': 'All model objects and operations are tied to a Session'
        },
        {
            'name': 'Model',
            'description': 'The model of a given Session. Use this endpoint to create, read, update, destroy model objects',
        },
        {
            'name': 'Time Resolution',
            'description': 'Specify the time resolution for the optimization problem',
        },
        {
            'name': 'Connection',
            'description': 'Configure connections between model objects',
        }
    ]
)

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}

def http_raise_internal(msg: str, e: Exception):
    raise HTTPException(500, f'{msg} -- Internal Exception: {e}')

def get_session_id(session_id: int = Header(1)) -> int:
    return session_id

test_user = 'test_user'
SessionManager.add_user_session('test_user', None)
SessionManager.add_shop_session(test_user)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token", response_model=Token, tags=['Authentication'])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):

    user = authenticate_user(fake_users_db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

# ------- session

@app.get("/sessions", response_model=List[Session], tags=['Session'])
async def get_sessions():
    sessions = [ Session(**{"session_id": id}) for id in SessionManager.list_shop_sessions(test_user)]
    return sessions


@app.get("/session/{session_id}", response_model=Session, tags=['Session'])
async def get_session(session_id: int):
    if session_id in SessionManager.list_shop_sessions(test_user):
        return Session(**{"session_id": session_id})
    else:
        return None


@app.post("/session", tags=['Session'])
async def create_session(session: Session):
    session_id = SessionManager.add_shop_session(test_user)
    return Session(**{"session_id": session_id})


# --------- time_resolution

class TimeResolution(BaseModel):
    start_time: datetime = Field(description="optimization start time")
    end_time: datetime = Field(description="optimization end time")
    time_unit: str = Field('hour', description="optimization time unit")
    time_resolution: Optional[Series] = None


@app.put("/time_resolution", tags=["Time Resolution"])
async def set_time_resolution(time_resolution: TimeResolution, session_id = Depends(get_session_id)):
    SessionManager.get_shop_session(test_user, session_id, raises=True).set_time_resolution(
        starttime=time_resolution.start_time,
        endtime=time_resolution.end_time,
        timeunit=time_resolution.time_unit # TODO: also use time_resolution series
    )
    return None


@app.get("/time_resolution", response_model=TimeResolution, tags=["Time Resolution"])
async def get_time_resolution(session_id = Depends(get_session_id)):

    try:
        tr = SessionManager.get_shop_session(test_user, session_id, raises=True).get_time_resolution()
    except HTTPException as e:
        raise e
    except Exception as e:
        http_raise_internal(    "Something whent wrong, maybe time_resolution has not been set yet", e)

    time_resolution = dict(
        start_time=tr['starttime'],
        end_time=tr['endtime'],
        timeunit=tr['timeunit'],
        time_resolution=Series_from_pd(tr['timeresolution'])
    )
    return TimeResolution(**time_resolution)

# ------ model

@app.get("/model", response_model=Model, response_model_exclude_unset=True, tags=['Model'])
async def get_model_object_types(session_id = Depends(get_session_id)):
    types = list(SessionManager.get_shop_session(test_user, session_id, raises=True).model._all_types)
    return Model(**{'object_types': types})

# ------ object_type

@app.get("/model/{object_type}", response_model=ObjectType, response_model_exclude_unset=True, tags=['Model'])
async def get_model_object_type_information(object_type: ObjectTypeEnum, session_id = Depends(get_session_id)):
    ot = SessionManager.get_model_object_type(test_user, session_id, object_type)
    instances = list(ot.get_object_names())
    sess = SessionManager.get_shop_session(test_user, session_id, raises=True)
    attribute_names: List[str] = list(sess.shop_api.GetObjectTypeAttributeNames(object_type))
    attribute_types: List[str] = list(sess.shop_api.GetObjectTypeAttributeDatatypes(object_type))
    attributes = {
        n: ObjectAttribute(**{
            'attribute_name': n,
            'attribute_type': new_attribute_type_name_from_old(t),
        }) for n, t in zip(attribute_names, attribute_types)
    }

    return ObjectType(**{
        'object_type': object_type,
        'instances': instances, 
        'attributes': attributes,
    })

# ------ object_name

@app.put("/model/{object_type}/{object_name}", response_model=ObjectInstance, response_model_exclude_unset=True, tags=['Model'])
async def create_or_modify_existing_model_object(object_type: ObjectTypeEnum, object_name: str, instance: ObjectInstance = None, session_id = Depends(get_session_id)):
    
    session = SessionManager.get_shop_session(test_user, session_id, raises=True)
    try:
        object_generator = session.model[object_type]
    except Exception as e:
        raise HTTPException(500, f'model does not implement object_type {{{object_type}}}') 
        
    try:
        object_generator.add_object(object_name)
    except Exception as e:
        raise HTTPException(500, f'object_name {{{object_name}}} is in conflict with existing instance')

    model_object = session.model[object_type][object_name]

    if instance.attributes:
        for (k,v) in instance.attributes.items():

            try:
                datatype = model_object[k].info()['datatype']
            except Exception as e:
                http_raise_internal(f'unknown object_attribute {{{k}}} for object_type {{{object_type}}}', e)

            try:
                if datatype == 'txy':
                    # ser = pd.Series(json.loads(v.replace('\'', '\"')))
                    # ser.index = pd.to_datetime(ser.index)
                    # ser = ser.tz_localize(None)
                    # model_object[k].set(ser)
                    print(f'dtype = {datatype}')

                elif datatype == 'xy':
                    # ser = pd.Series(json.loads(v.replace('\'', '\"')))
                    # ser.index = list(map(float, ser.index))
                    # ret = model_object[k].set(ser)
                    # print(ret)
                    print(f'dtype = {datatype}')

                elif datatype == 'xy_array':
                    # ser_arr = []
                    # arr = json.loads(v.replace('\'', '\"'))
                    # for name, data in arr.items():
                    #     ser = pd.Series(data)
                    #     ser.name = name
                    #     ser_arr.append(ser)
                    # model_object[k].set(ser_arr)
                    print(f'dtype = {datatype}')
                    
                elif datatype == 'double':
                    # model_object[k].set(float(v))
                    print(f'dtype = {datatype}')

                elif datatype == 'int':
                # model_object[k].set(int(v))
                    print(f'dtype = {datatype}')

                else:
                    # model_object[k].set(json.loads(v))
                    print(f'dtype = {datatype}')

            except:
                HTTPException(400, f'Wrong attribute name {k} or invalid attribute value {v}')

    return ObjectInstance(**{
        'object_type': object_type,
        'object_name': object_name,
    })

@app.get("/model/{object_type}/{object_name}", response_model=ObjectInstance, tags=['Model'])
async def get_model_object_attributes(object_type: ObjectTypeEnum, object_name: str, session_id = Depends(get_session_id)):

    o = SessionManager.get_model_object_type_object_name(test_user, session_id, object_type, object_name)
    attribute_names = list(o._attr_names)

    return ObjectInstance(**{
        'object_type': o.get_type(),
        'object_name': o.get_name(),
        'attributes': {
            name: serialize_model_object_attribute((getattr(o, name))) for name in attribute_names
        }
    })

# ------ attribute

@app.get("/model/{object_type}/{object_name}/{attribute_name}", response_model=ObjectAttribute, tags=['Model'])
async def get_attribute(object_type: ObjectTypeEnum, object_name: str, attribute_name: str, session_id = Depends(get_session_id)):
    o = SessionManager.get_model_object_type_object_name(test_user, session_id, object_type, object_name)
    
    try:
        attribute = o[attribute_name]
    except Exception as e:
        raise HTTPException(500, f'object_type {{{object_type}}} does not have attribute {{{attribute_name}}}')
    
    return serialize_model_object_attribute(attribute)

# ------ connection

@app.get("/connection", response_model=List[Connection], tags=['Connection'])
async def get_connection(session_id = Depends(get_session_id)):
    return Connection

@app.put("/connection", tags=['Connection'])
async def add_connection(connections: List[Connection] = None, session_id = Depends(get_session_id)):
    return None

# ------ commands

@app.post("/internal/commands", response_model=CommandStatus, tags=['__internals'])
async def post_list_of_api_commands(commands: Commands = None, session_id = Depends(get_session_id)):
    return CommandStatus(**{'message': 'ok'})

# ------ view_show_api

@app.get("/internal/commands", response_model=ApiCommands, tags=['__internals'])
async def get_available_api_commands(session_id = Depends(get_session_id)):
    shopsession = SessionManager.get_shop_session(test_user, session_id)
    command_types = shopsession.shop_api.__dir__()
    command_types = list(filter(lambda x: x[0] != '_', command_types))
    return ApiCommands(**{'command_types': command_types})

# ------ call_shop_api

@app.get("/internal/command/{command}", response_model=ApiCommandDescription, tags=['__internals'])
async def get_api_command_description(command: ApiCommandEnum, session_id = Depends(get_session_id)):
    shopsession = SessionManager.get_shop_session(test_user, session_id)
    doc = getattr(shopsession.shop_api, command).__doc__
    return ApiCommandDescription(**{'description': str(doc)})

@app.post("/internal/command/{command}", response_model=CommandStatus, tags=['__internals'])
async def post_api_command(command: ApiCommandEnum, session_id = Depends(get_session_id)):
    return CommandStatus(**{'message': 'ok'})

# ------- example

# @app.get("/users/me/", response_model=User, tags=['__fast api example'])
# async def read_users_me(current_user: User = Depends(get_current_active_user)):
#     return current_user


# @app.get("/users/me/items/",  tags=['__fast api example'])
# async def read_own_items(current_user: User = Depends(get_current_active_user)):
#     return [{"item_id": "Foo", "owner": current_user.username}]


# @app.post("/items/",  tags=['__fast api example'])
# async def create_item(item: Item):
#     return item