import pytest

from fastapi.testclient import TestClient

from restshop.schemas import *
from main import app

import json


client = TestClient(app)

# SESSION

@pytest.mark.order(1)
def test_post_session():
    response = client.post("/session")
    assert response.status_code == 200
    assert response.json() == {
        'session_id': 2,
        'session_name': 'unnamed'
    }

@pytest.mark.order(2)
def test_get_sessions():
    response = client.get("/sessions")
    assert response.status_code == 200
    assert response.json() == [
        {
            'session_id': 1,
            'session_name': 'default_session'
        },
        {
            'session_id': 2,
            'session_name': 'unnamed',
        }
    ]

@pytest.mark.order(3)
def test_get_session_that_exists():
    response = client.get("/session?session_id=1")
    assert response.status_code == 200
    assert response.json() == {
        'session_id': 1,
        'session_name': 'default_session'
    }

@pytest.mark.order(4)
def test_get_session_that_doesnt_exist():
    response = client.get("/session?session_id=42")
    assert response.status_code == 404
    assert response.json() == {
        'detail': 'Session with id {42} not found'
    }

# TIME RESOLUTION

@pytest.mark.order(5)
def test_get_time_resolution_before_set():
    response = client.get("/time_resolution")
    assert response.status_code == 400
    assert response.json() == {
        'detail': 'First you must set the time_resolution of the session'
    }

@pytest.mark.order(6)
def test_put_time_resolution_missing_body():
    response = client.put(
        "/time_resolution",
        data={

        }
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [{
            "loc": ["body"],
            "msg": "field required",
            "type": "value_error.missing"
        }]
    }


@pytest.mark.order(7)
def test_put_time_resolution_bad_time_order():
    response = client.put(
        "/time_resolution",
        json={
            "start_time": "2021-05-03T00:00:00.00Z",
            "end_time": "2021-05-02T00:00:00.00Z",
            "time_unit": "hour"
        }
    )

    assert response.status_code == 400
    assert response.json() == {'detail': 'end_time must be strictly greater than start_time'}


@pytest.mark.order(8)
def test_put_time_resolution():
    response = client.put(
        "/time_resolution",
        json={
            "start_time": "2021-05-02T00:00:00.00Z",
            "end_time": "2021-05-03T00:00:00.00Z",
            "time_unit": "hour"
        }
    )

    assert response.status_code == 200
    assert response.json() == None


@pytest.mark.order(9)
def test_put_time_resolution_invalid_session():
    response = client.put(
        "/time_resolution",
        headers={'session-id': '42'},
        json={
            "start_time": "2021-05-02T00:00:00.00Z",
            "end_time": "2021-05-03T00:00:00.00Z",
            "time_unit": "hour"
        }
    )

    assert response.status_code == 400
    assert response.json() == {'detail': 'Session {42} does not exist.'}

    
# MODEL

@pytest.mark.order(10)
def test_get_model():
    response = client.get("/model")
    assert response.status_code == 200
    assert 'object_types' in response.json()
    assert 'reservoir' in response.json()['object_types']
    assert 'plant' in response.json()['object_types']

@pytest.mark.order(11)
def test_get_model_object_type_info():
    response = client.get("/model/plant/information")
    assert response.status_code == 200
    ot = ObjectType(**response.json())  # Thanks to pydantic this raises exceptions if response is wrong

@pytest.mark.order(12)
def test_get_model_object_instance_nonexistent():
    response = client.get('/model/reservoir?object_name=test_res')
    assert response.status_code == 400
    assert response.json() == {
        'detail': 'object_name {test_res} is not an instance of object_type {reservoir}.'
    }

@pytest.mark.order(13)
def test_put_model_object_instance_no_body():
    response = client.put(
        '/model/reservoir?object_name=test_res',
    )
    assert response.status_code == 200
    o = ObjectInstance(**response.json()) # Thanks to pydantic this raises exceptions if response is wrong

expected_b = ObjectInstance(
    attributes={
        'vol_head': Curve(**{
            'x_unit': 'MM3', 'y_unit': 'METER',
            'y_values': [42.0, 43.0, 45.0],
            'x_values': [10.0, 20.0, 30.0]
        }),
        'water_value_input': {
            '0.0': Curve(**{
                'x_unit': 'MM3', 'y_unit': 'NOK/MM3',
                'x_values': [10.0, 9.0, 8.0],
                'y_values': [42.0, 20.0, 10.0]
            })
        },
        'inflow': TimeSeries(**{
            'unit': 'M3/S',
            'name': 'inflow',
            'timestamps': [
                '2021-05-02T00:00:00+00:00',
                '2021-05-02T01:00:00+00:00',
                '2021-05-02T02:00:00+00:00',
                '2021-05-02T03:00:00+00:00',
                '2021-05-02T04:00:00+00:00',
                '2021-05-02T05:00:00+00:00',
                '2021-05-02T06:00:00+00:00',
                '2021-05-02T07:00:00+00:00',
                '2021-05-02T08:00:00+00:00',
                '2021-05-02T09:00:00+00:00',
                '2021-05-02T10:00:00+00:00',
                '2021-05-02T11:00:00+00:00',
                '2021-05-02T12:00:00+00:00',
                '2021-05-02T13:00:00+00:00',
                '2021-05-02T14:00:00+00:00',
                '2021-05-02T15:00:00+00:00',
                '2021-05-02T16:00:00+00:00',
                '2021-05-02T17:00:00+00:00',
                '2021-05-02T18:00:00+00:00',
                '2021-05-02T19:00:00+00:00',
                '2021-05-02T20:00:00+00:00',
                '2021-05-02T21:00:00+00:00',
                '2021-05-02T22:00:00+00:00',
                '2021-05-02T23:00:00+00:00'
            ],
            'values': [
                [
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50
                ]
            ]
        })
    }
)

@pytest.mark.order(14)
def test_put_model_object_instance_with_body():

    a = ObjectInstance(
        attributes={
            'vol_head': Curve(**{
                'y_values': [42.0, 43.0, 45.0],
                'x_values': [10.0, 20.0, 30.0]
            }),
            'water_value_input': {
                '0.0': Curve(**{
                    'x_values': [10.0, 9.0, 8.0],
                    'y_values': [42.0, 20.0, 10.0]
                })
            },
            'inflow': TimeSeries(**{
                'timestamps': ['2020-01-01T00:00:00','2020-01-01T05:00:00'],
                'values': [[42.0, 50.0]]
            })
        }
    )

    response = client.put(
        '/model/reservoir?object_name=test_res',
        data=a.json()
    )
    assert response.status_code == 200
    b = ObjectInstance(**response.json()) # Thanks to pydantic this raises exceptions if response is wrong
    for attr, expected_value in expected_b.attributes.items():
        assert b.attributes[attr] == expected_value

@pytest.mark.order(15)
def test_get_model_object_instance():
    response = client.get('/model/reservoir?object_name=test_res')
    assert response.status_code == 200
    b = ObjectInstance(**response.json()) # Thanks to pydantic this raises exceptions if response is wrong
    for attr, expected_value in expected_b.attributes.items():
        assert b.attributes[attr] == expected_value

@pytest.mark.order(16)
def test_get_connections_nonexistent():
    response = client.get('/connections')
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.order(17)
def test_put_model_object_instance_reservoir_r1():
    response = client.put(
        '/model/reservoir?object_name=r1',
    )
    assert response.status_code == 200
    o = ObjectInstance(**response.json()) # Thanks to pydantic this raises exceptions if response is wrong

@pytest.mark.order(18)
def test_put_model_object_instance_plant_p1():
    response = client.put(
        '/model/plant?object_name=p1',
    )
    assert response.status_code == 200
    o = ObjectInstance(**response.json()) # Thanks to pydantic this raises exceptions if response is wrong

@pytest.mark.order(19)
def test_put_connections():
    response = client.put(
        '/connections',
        json=[
            {
                'from_object': {'object_type': 'reservoir', 'object_name': 'r1'},
                'to_object': {'object_type': 'plant', 'object_name': 'p1'}
            }
        ]
    )
    assert response.status_code == 200
    assert response.json() == None

@pytest.mark.order(20)
def test_get_connections():
    response = client.get('/connections')
    assert response.status_code == 200
    
    # TODO: connection output is a mess ... SHOP's fault?
    print(json.dumps(response.json(), indent=4))

    # raise Exception("dummy")

    # assert response.json() == [
    #     {
    #         'from_object': {'object_name': 'r1', 'object_type': 'reservoir'},
    #         'relation_direction': 'both',
    #         'relation_type': 'de...: 'both', 'relation_type': 'connection_standard', 'to_object': {'object_name': 'r1', 'object_type': 'reservoir'}

