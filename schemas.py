import collections

from typing import List, Dict, Optional, Union, Any, OrderedDict
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import HTTPException

import numpy as np
import pandas as pd

from sessions import SessionManager

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

    return Series(
        name = series.name,
        index = array_to_list_str(series.index),
        values = array_to_list_str(series.values)
    )

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

    return DataFrame(
        name = data_frame[data_frame.columns[0]].name,
        columns = columns,
        data_frame_index = array_to_list_str(data_frame.index),
    )


# ----------------- Primitive data types

class TimeSeries(BaseModel):
    name: Optional[str] = Field(None, description="name of the series")
    unit: Optional[str] = Field('NOK', description='unit of time series values')
    # values: Dict[datetime, List[float]] = Field({}, description='values')
    timestamps: List[datetime]
    values: List[List[float]]

class Curve(BaseModel):
    x_unit: Optional[str] = Field('MW', description='unit of x_values')
    y_unit: Optional[str] = Field('%', description='unit of y_values')
    x_values: List[float]
    y_values: List[float]

#
# Notice
# - xy             <-> Curve 
# - xy_array, xyn  <-> OrderedDict[float, Curve]
# - xyt            <-> OrderedDict[datetime, Curve]
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
    float_array = 'float_array',
    integer_array = 'integer_array',
    Curve = 'Curve'
    MapFloatCurve = 'OrderedDict[float, Curve]'
    MapTimeCurve = 'OrderedDict[datetime, Curve]'
    TimeSeries = 'TimeSeries'


def new_attribute_type_name_from_old(name: str) -> ObjectAttributeTypeEnum:
    
    conversion_map = {
        'bool': ObjectAttributeTypeEnum.boolean,
        'int': ObjectAttributeTypeEnum.integer,
        'double': ObjectAttributeTypeEnum.float,
        'str': ObjectAttributeTypeEnum.string,
        'double_array': ObjectAttributeTypeEnum.float_array,
        'int_array': ObjectAttributeTypeEnum.integer_array,
        'xy': ObjectAttributeTypeEnum.Curve,
        'xy_array': ObjectAttributeTypeEnum.MapFloatCurve,
        'xyn': ObjectAttributeTypeEnum.MapFloatCurve,
        'xyt': ObjectAttributeTypeEnum.MapTimeCurve,
        'txy': ObjectAttributeTypeEnum.TimeSeries,
    }

    if name in conversion_map:
        return conversion_map[name]
    else:
        raise HTTPException(500, f'name {{{name}}} not in understood type_name list ... needs to be handled ...')
    return name
    

AttributeValue = Union[None, float, str, List[float], Curve, OrderedDict[float, Curve], OrderedDict[datetime, Curve], TimeSeries]

class ObjectAttribute(BaseModel):
    attribute_name: str
    attribute_type: ObjectAttributeTypeEnum
    is_input: Optional[bool]
    is_output: Optional[bool]
    legacy_datatype: Optional[str]
    x_unit: Optional[str]
    y_unit: Optional[str]
    license_name: Optional[str]
    full_name: Optional[str]
    data_func_name: Optional[str]
    description: Optional[str]
    documentation_url: Optional[str]
    example_url_prefix: Optional[str]
    example: Optional[str]


class ObjectInstance(BaseModel):
    object_name: str = Field('example_res', description='name of instance')
    object_type: str = Field('reservoir', description='type of instance')
    attributes: Optional[Dict[str, AttributeValue]] = Field(None, description='attributes that can be set on the given object_type')

class ObjectType(BaseModel):
    object_type: str = Field(description='name of the object_type')
    instances: List[str] = Field(description='list of instances of this type')
    attributes: Optional[Dict[str, Union[ObjectAttributeTypeEnum, ObjectAttribute]]]  \
        = Field(description='attributes that can be set on the given object_type')

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
    info = attribute.info()

    attribute_y_unit = info['yUnit'] if 'yUnit' in info else 'unknown'
    attribute_x_unit = info['xUnit'] if 'xUnit' in info else 'unknown'

    value = attribute.get()

    if value is None:
        return None

    if attribute_type == ObjectAttributeTypeEnum.boolean:
        return bool(value)

    if attribute_type == ObjectAttributeTypeEnum.integer:
        return int(value)

    if attribute_type == ObjectAttributeTypeEnum.float:
        return float(value)

    if attribute_type == ObjectAttributeTypeEnum.string:
        return str(value)

    if attribute_type == ObjectAttributeTypeEnum.datetime:
        return str(value)

    if attribute_type == ObjectAttributeTypeEnum.float_array:
        return str(value) # TODO: fixme

    if attribute_type == ObjectAttributeTypeEnum.integer_array:
        return str(value) # TODO: fixme

    if attribute_type == ObjectAttributeTypeEnum.TimeSeries:

        if isinstance(value, pd.Series) or isinstance(value, pd.DataFrame):
            
            if isinstance(value, pd.Series):
                # values = {t: [v] for t, v in zip(value.index.values, value.values)}
                timestamps = value.index.values.tolist()
                values = value.values.reshape(1, value.values.size).tolist()

            if isinstance(value, pd.DataFrame):
                # values = {t: v for t, v in zip(value.index.values, value.values.tolist())}
                timestamps = value.index.value.tolist()
                values = value.values.transpose().tolist()

            return TimeSeries(
                name = value.name,
                unit = attribute_y_unit,
                timestamps = timestamps,
                values = values
            )

    if attribute_type == ObjectAttributeTypeEnum.Curve:

        if isinstance(value, pd.Series):
            return Curve(
                x_unit = attribute_x_unit,
                y_unit = attribute_y_unit,
                x_values = value.index.values.tolist(),
                y_values = value.values.tolist()
            )

    if attribute_type == ObjectAttributeTypeEnum.MapTimeCurve:
        return f'{attribute_type}: {type(value)}'

    if attribute_type == ObjectAttributeTypeEnum.MapFloatCurve:

        if type(value) == list and isinstance(value[0], pd.Series):

            return { ser.name: # reference value is stored in series.name
                Curve(
                    x_unit = attribute_x_unit,
                    y_unit = attribute_y_unit,
                    x_values = ser.index.values.tolist(),
                    y_values = ser.values.tolist()
                ) for ser in value
            }

    raise HTTPException(500, f"{attribute_type}: cannot parse <{type(value)}>")


def serialize_model_object_instance(o: Any) -> ObjectInstance:

    attribute_names = list(o._attr_names)

    return ObjectInstance(
        object_type = o.get_type(),
        object_name = o.get_name(),
        attributes = {
            name: serialize_model_object_attribute((getattr(o, name))) for name in attribute_names
        }
    )


class CommandArguments(BaseModel):
    options: Optional[List[str]] = None
    values: Optional[List[str]] = None


class Command(str, Enum):
    start_sim = 'start_sim'
    set_code = 'set_code'

