from datetime import datetime, timedelta
from typing import Optional, List, Union, Any, Dict

from fastapi import Depends, FastAPI, HTTPException, status, Body, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from fastapi.openapi.models import SchemaBase

import restshop
from restshop.sessions import SessionManager
from restshop.schemas import *

from enum import Enum

from fastapi import Path, Header

import pandas as pd
import numpy as np

def shop_session(user_name: str, session_id: str):
    return SessionManager.get_shop_session(user_name, session_id)

api_description = """ """

if __name__ == 'main':

    # to get a string like this run:
    # openssl rand -hex 32
    SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    app = FastAPI(
        title="REST SHOP",
        description=api_description,
        version=restshop.__version__,
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
                'name': 'Time Resolution',
                'description': 'Specify the time resolution for the optimization problem',
            },
            {
                'name': 'Model',
                'description': 'The model of a given Session. Use this endpoint to create, read, update, destroy model objects',
            },
            {
                'name': 'Connections',
                'description': 'Configure connections between model objects',
            },
            {
                'name': 'Simulation',
                'description': 'Interact with the simulation using SHOP commands',
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

    def check_that_time_resolution_is_set(session_id: int = Depends(get_session_id)):
        is_set = SessionManager.get_user_session(test_user).shop_sessions_time_resolution_is_set[session_id]
        if is_set == False:
            raise HTTPException(400, 'First you must set the time_resolution of the session')
        

    test_user = 'test_user'
    SessionManager.add_user_session('test_user', None)
    SessionManager.add_shop_session(test_user, 'default_session')

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

    @app.post("/session", tags=['Session'])
    async def create_session(s: Session = Body(Session(session_name='unnamed'), example={'name': 'unnamed'})):
        s = SessionManager.add_shop_session(test_user, session_name=s.session_name)
        return Session(session_id = s._id, session_name=s._name)


    @app.get("/sessions", response_model=List[Session], tags=['Session'])
    async def get_sessions():
        return [
            Session(
                session_id = s._id,
                session_name = s._name
            ) for _, s in SessionManager.get_shop_sessions(test_user).items()
        ]


    @app.get("/session", response_model=Session, tags=['Session'])
    async def get_session(session_id: int = Query(1)):
        if session_id in SessionManager.get_shop_sessions(test_user):
            s = shop_session(test_user, session_id)
            return Session(session_id = s._id, session_name = s._name)
        else:
            raise HTTPException(404, f'Session with id {{{session_id}}} not found')


    # --------- time_resolution

    class TimeResolution(BaseModel):
        start_time: datetime = Field(description="optimization start time")
        end_time: datetime = Field(description="optimization end time")
        time_unit: str = Field('hour', description="optimization time unit")
        time_resolution: Optional[Series] = None


    @app.put("/time_resolution", tags=["Time Resolution"])
    async def set_time_resolution(
        time_resolution: TimeResolution = Body(
            ...,
            example={
                "start_time": "2021-05-02T00:00:00.00Z",
                "end_time": "2021-05-03T00:00:00.00Z",
                "time_unit": "hour"
            }
        ),
        session_id = Depends(get_session_id)):

        # validate
        start = pd.Timestamp(time_resolution.start_time)
        end = pd.Timestamp(time_resolution.end_time)

        if (end <= start):
            raise HTTPException(400, 'end_time must be strictly greater than start_time')

        shop_session(test_user, session_id).set_time_resolution(
            starttime=time_resolution.start_time,
            endtime=time_resolution.end_time,
            timeunit=time_resolution.time_unit # TODO: also use time_resolution series
        )


        # store the fact that time_resolution has been set
        us = SessionManager.get_user_session(test_user)
        us.shop_sessions_time_resolution_is_set[session_id] = True
        return None


    @app.get("/time_resolution", response_model=TimeResolution, dependencies=[Depends(check_that_time_resolution_is_set)], tags=["Time Resolution"])
    async def get_time_resolution(session_id = Depends(get_session_id)):

        try:
            tr = shop_session(test_user, session_id).get_time_resolution()
        except HTTPException as e:
            raise e
        except Exception as e:
            http_raise_internal(    "Something whent wrong, maybe time_resolution has not been set yet", e)

        return TimeResolution(
            start_time=tr['starttime'],
            end_time=tr['endtime'],
            timeunit=tr['timeunit'],
            time_resolution=Series_from_pd(tr['timeresolution'])
        )

    # ------ model

    @app.get("/model", response_model=Model, response_model_exclude_unset=True, tags=['Model'])
    async def get_model_object_types(session_id = Depends(get_session_id)):
        types = list(shop_session(test_user, session_id).model._all_types)
        return Model(object_types = types)

    # ------ object_type

    @app.get("/model/{object_type}/information", response_model=ObjectType, response_model_exclude_unset=True, tags=['Model'])
    async def get_model_object_type_information(
        object_type: ObjectTypeEnum,
        attribute_filter: str = Query('*', description='filter attributes by regex'),
        verbose: bool = Query(False, description='toggles additional attribute information, e.g is_input, is_output, etc ...'),
        session_id = Depends(get_session_id)
    ):

        if attribute_filter != '*':
            raise HTTPException(500, 'setting attribute_filter != * is not support yet')

        ot = SessionManager.get_model_object_generator(test_user, session_id, object_type)
        instances = list(ot.get_object_names())
        sess = shop_session(test_user, session_id)
        attribute_names: List[str] = list(sess.shop_api.GetObjectTypeAttributeNames(object_type))
        attribute_types: List[str] = list(sess.shop_api.GetObjectTypeAttributeDatatypes(object_type))

        if not verbose:
            attributes = {
                n: new_attribute_type_name_from_old(t)
                for n, t in zip(attribute_names, attribute_types)
            }
        else:

            # TODO: Create this kind of dictionary once at startup, since this might be expensive?
            attr_info = {
                attr_name: {
                    info_key: sess.shop_api.GetAttributeInfo(object_type, attr_name, info_key)
                    for info_key in sess.shop_api.GetValidAttributeInfoKeys()
                } for attr_name in attribute_names
            }

            attributes = {
                n: ObjectAttribute(
                    attribute_name = n,
                    attribute_type = new_attribute_type_name_from_old(t),
                    is_input = attr_info[n]['isInput'],
                    is_output = attr_info[n]['isOutput'],
                    legacy_datatype = attr_info[n]['datatype'],
                    x_unit = attr_info[n]['xUnit'],
                    y_unit = attr_info[n]['yUnit'],
                    license_name = attr_info[n]['licenseName'],
                    full_name = attr_info[n]['fullName'],
                    data_func_name = attr_info[n]['dataFuncName'],
                    description = attr_info[n]['description'],
                    documentation_url = attr_info[n]['documentationUrl'],
                    example_url_prefix = attr_info[n]['exampleUrlPrefix'],
                    example = attr_info[n]['example']
                )
                for n, t in zip(attribute_names, attribute_types)
            }

        return ObjectType(
            object_type = object_type,
            instances = instances, 
            attributes = attributes,
        )

    # ------ object_name

    @app.put("/model/{object_type}",
        response_model=ObjectInstance,
        dependencies=[Depends(check_that_time_resolution_is_set)],
        response_model_exclude_unset=True, tags=['Model'])
    async def create_or_modify_existing_model_object_instance(
        object_type: ObjectTypeEnum,
        object_name: str = Query('example_reservoir'),
        object_instance: ObjectInstance = Body(
            None,
            example={
                'attributes': {
                    'vol_head': {
                        'x_values': [10.0, 20.0, 30.0],
                        'y_values': [42.0, 43.0, 45.0]
                    },
                    'water_value_input': {
                        '0.0': {
                            'x_values': [10.0, 9.0, 8.0],
                            'y_values': [42.0, 20.0, 10.0]
                        }
                    },
                    'inflow': {
                        #'values': {'2020-01-01T00:00:00': [ 42.0 ] }
                        'timestamps': ['2020-01-01T00:00:00', '2020-01-01T05:00:00' ],
                        'values': [[42.0, 50.0]]
                    }
                }
            }
        ),
        session_id = Depends(get_session_id)
        ):
        
        session = shop_session(test_user, session_id)
        try:
            object_generator = session.model[object_type]
        except Exception as e:
            raise HTTPException(500, f'model does not implement object_type {{{object_type}}}') 

        if object_name not in object_generator.get_object_names():
            try:
                object_generator.add_object(object_name)
            except Exception as e:
                raise HTTPException(500, f'object_name {{{object_name}}} is in conflict with existing instance')

        model_object = session.model[object_type][object_name]

        if object_instance and object_instance.attributes:
            for (k,v) in object_instance.attributes.items():

                try:
                    datatype = model_object[k].info()['datatype']
                except Exception as e:
                    http_raise_internal(f'unknown object_attribute {k} for object_type {object_type}', e)

                if datatype == 'txy':

                    # convert scalar values to timestamp
                    if type(v) == float or type(v) == int:
                        start_time = shop_session(test_user, session_id).get_time_resolution()['starttime']
                        v = TimeSeries(
                            timestamps=[start_time],
                            values=[[v]]
                        )
                    try:
                        time_series: TimeSeries = v # time_series
                        # index, values = zip(*time_series.values.items())
                        index, values = time_series.timestamps, np.transpose(time_series.values)
                        df = pd.DataFrame(index=index, data=values)
                        model_object[k].set(df)
                    except Exception as e:
                        http_raise_internal(f'trouble setting {{{datatype}}} ', e)

                elif datatype == 'xy':
                    try:
                        curve: Curve = v # curve
                        ser = pd.Series(index=curve.x_values, data=curve.y_values)
                        model_object[k].set(ser)
                    except Exception as e:
                        http_raise_internal(f'trouble setting {{{datatype}}} ', e)

                elif datatype in ['xy_array', 'xyn']:
                    try:
                        curves: OrderedDict[float, Curve] = v # OrderedDict[float, Curve]
                        ser_list = []
                        for ref, curve in curves.items():
                            ser_list += [pd.Series(index=curve.x_values, data=curve.y_values, name=ref)]
                        model_object[k].set(ser_list)
                    except Exception as e:
                        http_raise_internal(f'trouble setting {{{datatype}}} ', e)

                elif datatype == 'xyt':
                    try:
                        curves: OrderedDict[datetime, Curve] = v
                        ser_list = []
                        for ref, curve in curves.items():
                            ser_list += [pd.Series(index=curve.x_values, data=curve.y_values, name=ref)]
                        model_object[k].set(ser_list)
                    except Exception as e:
                        http_raise_internal(f'trouble setting {{{datatype}}} ', e)
                    
                elif datatype == 'double':
                    model_object[k].set(float(v))

                elif datatype == 'int':
                    model_object[k].set(int(v))

                else:
                    try:
                        model_object[k].set(v)
                    except Exception as e:
                        http_raise_internal(f'trouble setting {{{datatype}}} ', e)

        o = SessionManager.get_model_object_instance(test_user, session_id, object_type, object_name)
        return serialize_model_object_instance(o)

    @app.get("/model/{object_type}", response_model=ObjectInstance, dependencies=[Depends(check_that_time_resolution_is_set)], tags=['Model'])
    async def get_model_object_instance(
        object_type: ObjectTypeEnum,
        object_name: str = Query('example_reservoir'),
        attribute_filter: str = Query('*', description='filter attributes by regex'),
        session_id = Depends(get_session_id)
        ):

        if attribute_filter != '*':
            raise HTTPException(500, 'setting attribute_filter != * is not support yet')

        o = SessionManager.get_model_object_instance(test_user, session_id, object_type, object_name)
        return serialize_model_object_instance(o)


    # ------ connection


    @app.get("/connections", response_model=List[Connection], dependencies=[Depends(check_that_time_resolution_is_set)], tags=['Connections'])
    async def get_connections(session_id = Depends(get_session_id)):

        connections = []

        for object_type in shop_session(test_user, session_id).model._all_types:
            generator = SessionManager.get_model_object_generator(test_user, session_id, object_type)
            for object_name in generator.get_object_names():
                from_object = generator[object_name]
                for relation_direction in RelationDirectionEnum:
                    for relation_type in RelationTypeEnum:
                        for r in from_object.get_relations(
                            direction=relation_direction,
                            relation_type=relation_type
                        ):
                            to_object = serialize_model_object_instance(r)
                            connections += [Connection(
                                from_object=serialize_model_object_instance(from_object),
                                to_object=to_object,
                                relation_type=relation_type,
                                relation_direction=relation_direction,
                            )]

        return connections

    @app.put("/connections", dependencies=[Depends(check_that_time_resolution_is_set)], tags=['Connections'])
    async def add_connections(connections: List[Connection], session_id = Depends(get_session_id)):

        for connection in connections:

            fo_type, fo_name = connection.from_object.object_type, connection.from_object.object_name
            to_type, to_name = connection.to_object.object_type, connection.to_object.object_name
            relation_type = connection.relation_type if connection.relation_type != 'default' else ''

            fo = SessionManager.get_model_object_instance(test_user, session_id, fo_type, fo_name)
            to = SessionManager.get_model_object_instance(test_user, session_id, to_type, to_name)

            fo.connect(connection_type=relation_type)[to_type][to_name].add()

    @app.put("/connect/{from_type}/{from_name}/{to_type}/{to_name}", dependencies=[Depends(check_that_time_resolution_is_set)], tags=['Connections'])
    async def add_connection(
        from_type: ObjectTypeEnum, from_name: str,
        to_type: ObjectTypeEnum, to_name: str,
        connection_type: RelationTypeEnum=Query(RelationTypeEnum.default),
        session_id = Depends(get_session_id)):

        connection_type = connection_type if connection_type != 'default' else ''

        fo = SessionManager.get_model_object_instance(test_user, session_id, from_type, from_name)
        to = SessionManager.get_model_object_instance(test_user, session_id, to_type, to_name)
        fo.connect(connection_type=connection_type)[to_type][to_name].add()

    # ------ shop commands

    @app.post("/simulation/{command}", response_model=CommandStatus, dependencies=[Depends(check_that_time_resolution_is_set)], tags=['Simulation'])
    async def post_simulation_command(command: ShopCommandEnum, args: CommandArguments = None, session_id = Depends(get_session_id)):

        sess = shop_session(test_user, session_id)
        sess._command = command
        try:
            status: bool = sess._execute_command(args.options, args.values) # does this return anything
        except Exception as e:
            http_raise_internal('failed to execute simulation command', e)
        return CommandStatus(
            message=('ok' if status else 'something went wrong ...'),
            status=status
        )

    # ------ internal methods


    @app.get("/internal", response_model=ApiCommands, dependencies=[Depends(check_that_time_resolution_is_set)], tags=['__internals'])
    async def get_available_internal_methods(session_id = Depends(get_session_id)):
        command_types = shop_session(test_user, session_id).shop_api.__dir__()
        command_types = list(filter(lambda x: x[0] != '_', command_types))
        return ApiCommands(command_types = command_types)

    @app.get("/internal/{command}", dependencies=[Depends(check_that_time_resolution_is_set)], response_model=ApiCommandDescription, tags=['__internals'])
    async def get_internal_method_description(command: ApiCommandEnum, session_id = Depends(get_session_id)):
        doc = getattr(shop_session(test_user, session_id).shop_api, command).__doc__
        return ApiCommandDescription(description = str(doc))

    @app.post("/internal/{command}", dependencies=[Depends(check_that_time_resolution_is_set)], response_model=CommandStatus, tags=['__internals'])
    async def call_internal_method(command: ApiCommandEnum, session_id = Depends(get_session_id)):
        return CommandStatus(message = 'ok')

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