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

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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

dummy_user = '__dummy_user__'
SessionManager.add_user_session('__dummy_user__', None)
SessionManager.add_shop_session(dummy_user)

class StrEnum(str, Enum):
    pass

ObjectTypeEnum = StrEnum(
    'ObjectTypeEnum',
    names={
        name: name for name in SessionManager.get_shop_session(dummy_user, 1).model._all_types
    }
)

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="SHOP",
    description="REST-SHOP, SINTEF Energy",
    version="0.1.0",
    openapi_tags=[
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


# ------ pandas-like schemas

class Series(BaseModel):

    name: Optional[str] = None
    index: List[str]
    values: List[str]

def array_to_list_str(array: np.array) -> List[str]:
    
    # convert pandas series and index object to array
    if isinstance(array, pd.Series) or isinstance(array, pd.Index):
        array = array.values
    
    # convert timestamps to ISO timestamps
    if type(array[0]) == np.datetime64 or type(array[0]) == pd.Timestamp:
        list(pd.to_datetime(array).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    
    # convert numpy array to list
    return list(array.astype(str))

    
def Series_from_pd(series: pd.Series) -> Series:

    if series is None or len(series) == 0:
        return None

    return Series(**{
        'name': series.name,
        'index': array_to_list_str(series.index),
        'values': array_to_list_str(series.values)
    })

class DataFrame(BaseModel):

    name: Optional[str] = None
    columns: Dict[str, List[str]]
    dataframe_index: List[str]

def DataFrame_from_pd(data_frame: pd.DataFrame) -> DataFrame:
    
    if data_frame is None or len(df) == 0:
        return None

    columns = {
        c_name: array_to_list_str(data_frame[c_name]) for c_name in data_frame.columns
    }

    return DataFrame(**{
        'name': data_frame[data_frame.columns[0]].name,
        'columns': columns,
        'data_frame_index': array_to_list_str(data_frame.index),
    })

# @app.get("/test/{path_var}", tags=['Test'])
# async def path_test(path_var: PathVar):
#     pass

# ------- session

class Session(BaseModel):
    session_id: int = Field(1, description="unique session identifier per user session")
    example_option: Optional[str] = None


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

class Model(BaseModel):
    object_types: List[str] = Field(description='list of implemented model object types')


@app.get("/model", response_model=Model, tags=['Model'])
async def get_model_object_types(session_id = Depends(get_session_id)):
    types = list(SessionManager.get_shop_session(test_user, session_id, raises=True).model._all_types)
    return Model(**{'object_types': types})

# ------ object_type

class ObjectAttributeType(str, Enum):
    txy = 'txy'
    double = 'double'
    int = 'int'
    xy_array = 'xy_array'
    xy = 'xy'

class ObjectAttribute(BaseModel):
    attribute_name: str
    attribute_type: ObjectAttributeType
    value: Any = {}

class ObjectInstance(BaseModel):
    object_name: str
    object_type: str
    attributes: Dict[str, ObjectAttribute] = Field(dict(), description='field to contain data associated with the instance')

class ObjectType(BaseModel):
    object_type: str = Field(description='name of the object_type')
    instances: List[str] = Field(description='list of instances of this type')
    attributes: List[ObjectAttribute] = Field(description='list of attributes that can be set on the given object_type')


@app.get("/model/{object_type}", response_model=ObjectType, tags=['Model'])
async def get_model_object_instances(object_type: ObjectTypeEnum, session_id = Depends(get_session_id)):
    ot = SessionManager.get_model_object_type(test_user, session_id, object_type)
    instances = list(ot.get_object_names())
    sess = SessionManager.get_shop_session(test_user, session_id, raises=True)
    attribute_names = list(sess.shop_api.GetObjectTypeAttributeNames(object_type))
    attribute_types = list(sess.shop_api.GetObjectTypeAttributeDatatypes(object_type))
    attributes = [ObjectAttribute(**{
        'attribute_name': n,
        'attribute_type': t
    }) for n, t in zip(attribute_names, attribute_types)]

    return ObjectType(**{
        'object_type': object_type,
        'instances': instances, 
        'attributes': attributes,
    })

# ------ object_name

def serialize_model_object_attribute(attribute: Any) -> ObjectAttribute:
    attribute_type = attribute.info()['datatype']
    attribute_name = attribute._attr_name
    return ObjectAttribute(**{
        'attribute_name': attribute_name,
        'attribute_type': attribute_type,
        'value' : str(attribute.get())
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

@app.put("/model/{object_type}/{object_name}", response_model=ObjectInstance, tags=['Model'])
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

    for (k,v) in instance.attributes.items():

        datatype = model_object[k].info()['datatype']

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
        'attributes': {}
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

class Connection(BaseModel):
    from_type: str = Field(description="type of object to connect from")
    from_name: str = Field(description="name of object to connect from")
    to_type: str = Field(description="type of object to connect to")
    to_name: str = Field(description="name of object to connect to")
    relation_type: str = Field(desription="relation type")


@app.get("/connection", response_model=List[Connection], tags=['Connection'])
async def get_connection(session_id = Depends(get_session_id)):
    return Connection

@app.put("/connection", tags=['Connection'])
async def add_connection(connections: List[Connection] = None, session_id = Depends(get_session_id)):
    return None

# ------ commands

class Commands(BaseModel):
    commands: List[str] = Field(description="list of commands")

class CommandStatus(BaseModel):
    message: str
    error: Optional[str] = None

@app.post("/commands", response_model=CommandStatus, tags=['__internals'])
async def post_list_of_api_commands(commands: Commands = None, session_id = Depends(get_session_id)):
    return CommandStatus(**{'message': 'ok'})

# ------ view_show_api

class ApiCommands(BaseModel):
    command_types: List[str] = None

@app.get("/shop_api", response_model=ApiCommands, tags=['__internals'])
async def get_available_api_commands(session_id = Depends(get_session_id)):
    return ApiCommands(**{'command_types': ['foo', 'bar']})

# ------ call_shop_api

class ApiCommandArgs(BaseModel):
    args: tuple
    kwargs: dict

class ApiCommandDescription(BaseModel):
    description: str

@app.get("/shop_api/{command}", response_model=ApiCommandDescription, tags=['__internals'])
async def get_api_command_description(command: str, session_id = Depends(get_session_id)):
    return ApiCommandDescription(**{'description': 'hello world'})

@app.post("/shop_api/{command}", response_model=CommandStatus, tags=['__internals'])
async def post_api_command(command: str, session_id = Depends(get_session_id)):
    return CommandStatus(**{'message': 'ok'})

# ------- example

@app.get("/users/me/", response_model=User, tags=['__fast api example'])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/users/me/items/",  tags=['__fast api example'])
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]


@app.post("/items/",  tags=['__fast api example'])
async def create_item(item: Item):
    return item