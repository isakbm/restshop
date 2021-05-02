
from typing import List, Dict, Optional, Union, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

import numpy as np
import pandas as pd

from src.sessions import SessionManager

dummy_user = '__dummy_user__'
SessionManager.add_user_session('__dummy_user__', None)
SessionManager.add_shop_session(dummy_user)

class StrEnum(str, Enum):
    pass

# Auth schemas

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

# Session

class Session(BaseModel):
    session_id: int = Field(1, description="unique session identifier per user session")
    example_option: Optional[str] = None

# Commands

class Commands(BaseModel):
    commands: List[str] = Field(description="list of commands")

class CommandStatus(BaseModel):
    message: str
    error: Optional[str] = None

ApiCommandEnum = StrEnum(
    'ApiCommandEnum',
    names={
        name: name for name in filter(lambda x : x[0] != '_', SessionManager.get_shop_session(dummy_user, 1).shop_api.__dir__())
    }
)

class ApiCommands(BaseModel):
    command_types: List[str] = None
    
class ApiCommandArgs(BaseModel):
    args: tuple
    kwargs: dict

class ApiCommandDescription(BaseModel):
    description: str


# Pandas like schemas

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


# ----------------- Primitive data types

class TimeSeries(BaseModel):
    name: str
    timestamp: List[datetime]
    unit: Optional[str] = Field(description='physical unit -- inferred')
    values: List[List[float]]
    # stop_time: Optional[List[datetime]] = None
    # start_time: Optional[List[datetime]] = None

class XYPair(BaseModel):
    x: float
    y: float

class Curve(BaseModel):
    name: str
    x_unit: Optional[str] = Field(description='physical unit -- inferred')
    y_unit: Optional[str] = Field(description='physical unit -- inferred')
    values: List[XYPair]

class CurveList(BaseModel):
    curves: List[Curve]

class TimeCurves(BaseModel):
    curves: Dict[datetime, Curve]

#
# Notice
# - xy             <-> Curve 
# - xy_array, xyn  <-> CurveList
# - xyt            <-> TimeCurves
# - txy, #ttxy     <-> TimeSeries
#

ObjectTypeEnum = StrEnum(
    'ObjectTypeEnum',
    names={
        name: name for name in SessionManager.get_shop_session(dummy_user, 1).model._all_types
    }
)

class ObjectAttributeTypeEnum(str, Enum):
    boolean = 'boolean'
    integer = 'integer'
    float = 'float'
    string = 'string'
    datetime = 'datetime'
    Curve = 'Curve'
    CurveList = 'CurveList'
    TimeCurves = 'TimeCurves'
    TimeSeries = 'TimeSeries'


def new_attribute_type_name_from_old(name: str) -> ObjectAttributeTypeEnum:
    
    conversion_map = {
        'bool' : 'boolean',
        'int': 'integer',
        'double': 'float',
        'str': 'string',
        'xy': 'Curve',
        'xy_array': 'CurveList',
        'xyn': 'CurveList',
        'xyt': 'TimeCurves',
        'txy': 'TimeSeries'
    }

    if name in conversion_map:
        return conversion_map[name]

    return name
    

AttributeValue = Union[bool, int, float, str, Curve, CurveList, TimeCurves, TimeSeries]

class ObjectAttribute(BaseModel):
    attribute_name: str
    attribute_type: ObjectAttributeTypeEnum


class ObjectInstance(BaseModel):
    object_name: str = Field('example_res', description='name of instance')
    object_type: str = Field('reservoir', description='type of instance')
    attributes: Optional[Dict[str, AttributeValue]] = Field(None, description='attributes that can be set on the given object_type')

class ObjectType(BaseModel):
    object_type: str = Field(description='name of the object_type')
    instances: List[str] = Field(description='list of instances of this type')
    attributes: Optional[Dict[str, ObjectAttribute]] = Field(description='attributes that can be set on the given object_type')

# Connection

class ObjectID(BaseModel):
    object_type: str
    object_name: str

class Connection(BaseModel):
    from_object: ObjectID
    to_object: ObjectID
    relation_type: str = Field(desription="relation type")

# Model

class Model(BaseModel):
    object_types: List[str] = Field(description='list of implemented model object types and associated information')


    
def serialize_model_object_attribute(attribute: Any) -> AttributeValue:
    attribute_type = new_attribute_type_name_from_old(attribute.info()['datatype'])
    attribute_name = attribute._attr_name
    return str(attribute.get())

def serialize_model_object_instance(o: Any) -> ObjectInstance:

    attribute_names = list(o._attr_names)

    return ObjectInstance(**{
        'object_type': o.get_type(),
        'object_name': o.get_name(),
        'attributes': {
            name: serialize_model_object_attribute((getattr(o, name))) for name in attribute_names
        }
    })


class CommandArguments(BaseModel):
    options: Optional[List[str]] = None
    values: Optional[List[str]] = None


class Command(str, Enum):
    start_sim = 'start_sim'
    set_code = 'set_code'

