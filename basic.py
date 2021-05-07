from fastapi.testclient import TestClient

from restshop.schemas import *
from main import app

import matplotlib.pyplot as plt
import pandas as pd

client = TestClient(app)

# ==================================

# Create a new SHOP session.
# default session is enough in restshop
# pyshop -> shop = ShopSession(license_path='', silent=False, log_file='')


# Set time resolution

start_time = '2018-02-27T00:00:00'
end_time = '2018-02-28T00:00:00'

resp = client.put(
    '/time_resolution',
    json={
        'start_time': start_time,
        'end_time': end_time,
        'time_unit': 'hour'
    }
)

assert resp.status_code == 200

# pyshop -> starttime = pd.Timestamp('2018-02-27')
# pyshop -> endtime = pd.Timestamp('2018-02-28')
# pyshop -> shop.set_time_resolution(starttime=starttime, endtime=endtime, timeunit='hour')

# Add topology

resp = client.put(
    '/model/reservoir?object_name=Reservoir1',
    json={
        'attributes': {
            'max_vol': 12,
            'lrl': 90,
            'hrl': 100,
            'vol_head': { # Curve
                'y_values': [90, 100, 101],
                'x_values': [0, 12, 14]
            },
            'flow_descr': { # Curve 
                'y_values': [0, 1000],
                'x_values': [100, 101]
            }
        }
    }
)

assert resp.status_code == 200

# pyshop -> rsv1 = shop.model.reservoir.add_object('Reservoir1')
# pyshop -> rsv1.max_vol.set(12)
# pyshop -> rsv1.lrl.set(90)
# pyshop -> rsv1.hrl.set(100)
# pyshop -> rsv1.vol_head.set(pd.Series([90, 100, 101], index=[0, 12, 14], name=0))
# pyshop -> rsv1.flow_descr.set(pd.Series([0, 1000], index=[100, 101], name=0))

resp = client.put(
    '/model/plant?object_name=Plant1',
    json={
        'attributes': {
            'outlet_line': 40,
            'main_loss': [0.0002],
            'penstock_loss': [0.0001]
        }
    }
)

assert resp.status_code == 200

# plant1 = shop.model.plant.add_object('Plant1')
# plant1.outlet_line.set(40)
# plant1.main_loss.set([0.0002])
# plant1.penstock_loss.set([0.0001])

resp = client.put(
    '/model/generator?object_name=Plant1_G1',
    json={
        'attributes': {
            'penstock': 1,
            'p_min': 25,
            'p_max': 100,
            'p_nom': 100,
            'startcost': 500,
            'gen_eff_curve': { #Curve 
                'y_values': [95, 98],
                'x_values': [0, 100]
            },
            'turb_eff_curves': { #Dict[float, Curve]
                '90': { # Curve
                    'y_values': [80, 95, 90],
                    'x_values': [25, 90, 100]
                },
                '100': { # Curve
                    'y_values': [82, 98, 92],
                    'x_values': [25, 90, 100]
                }
            }
        }
    }
)

assert resp.status_code == 200


resp = client.put(
    '/connections',
    json=[
        {
            'from_object': { #ObjectID
                'object_type': 'plant',
                'object_name': 'Plant1'
            },
            'to_object': { #ObjectID
                'object_type': 'generator',
                'object_name': 'Plant1_G1'
            }
        }
    ]
)

assert resp.status_code == 200

# p1g1 = shop.model.generator.add_object('Plant1_G1')
# plant1.connect().generator.Plant1_G1.add()
# p1g1.penstock.set(1)
# p1g1.p_min.set(25)
# p1g1.p_max.set(100)
# p1g1.p_nom.set(100)
# p1g1.startcost.set(500)
# p1g1.gen_eff_curve.set(pd.Series([95, 98], index=[0, 100]))
# p1g1.turb_eff_curves.set([pd.Series([80, 95, 90], index=[25, 90, 100], name=90),
#                           pd.Series([82, 98, 92], index=[25, 90, 100], name=100)])

resp = client.put(
    '/model/reservoir?object_name=Reservoir2',
    json={
        'attributes': {
            'max_vol': 5,
            'lrl': 40,
            'hrl': 50,
            'vol_head': { # Curve
                'y_values': [40, 50, 51],
                'x_values': [0, 5, 6]
            },
            'flow_descr': { # Curve 
                'y_values': [0, 1000],
                'x_values': [50, 51]
            }
        }
    }
)

assert resp.status_code == 200

# rsv2 = shop.model.reservoir.add_object('Reservoir2')
# rsv2.max_vol.set(5)
# rsv2.lrl.set(40)
# rsv2.hrl.set(50)
# rsv2.vol_head.set(pd.Series([40, 50, 51], index=[0, 5, 6]))
# rsv2.flow_descr.set(pd.Series([0, 1000], index=[50, 51]))

resp = client.put(
    '/model/plant?object_name=Plant2',
    json={
        'attributes': {
            'outlet_line': 0,
            'main_loss': [0.0002],
            'penstock_loss': [0.0001]
        }
    }
)

assert resp.status_code == 200

# plant2 = shop.model.plant.add_object('Plant2')
# plant2.outlet_line.set(0)
# plant2.main_loss.set([0.0002])
# plant2.penstock_loss.set([0.0001])

resp = client.put(
    '/model/generator?object_name=Plant2_G1',
    json={
        'attributes': {
            'penstock': 1,
            'p_min': 25,
            'p_max': 100,
            'p_nom': 100,
            'startcost': 500,
            'gen_eff_curve': { #Curve 
                'y_values': [95, 98],
                'x_values': [0, 100]
            },
            'turb_eff_curves': { #Dict[float, Curve]
                '90': { # Curve
                    'y_values': [80, 95, 90],
                    'x_values': [25, 90, 100]
                },
                '100': { # Curve
                    'y_values': [82, 98, 92],
                    'x_values': [25, 90, 100]
                }
            }
        }
    }
)

assert resp.status_code == 200

resp = client.put(
    '/connections',
    json=[
        {
            'from_object': { #ObjectID
                'object_type': 'plant',
                'object_name': 'Plant2'
            },
            'to_object': { #ObjectID
                'object_type': 'generator',
                'object_name': 'Plant2_G1'
            }
        }
    ]
)

assert resp.status_code == 200

# p2g1 = shop.model.generator.add_object('Plant2_G1')
# plant2.connect().generator.Plant2_G1.add()
# p2g1.penstock.set(1)
# p2g1.p_min.set(25)
# p2g1.p_max.set(100)
# p2g1.p_nom.set(100)
# p2g1.startcost.set(500)
# p2g1.gen_eff_curve.set(pd.Series([95, 98], index=[0, 100]))
# p2g1.turb_eff_curves.set([pd.Series([80, 95, 90], index=[25, 90, 100], name=90),
#                           pd.Series([82, 98, 92], index=[25, 90, 100], name=100)])

# Connect objects

resp = client.put(
    '/connections',
    json=[
        { #Reservoir1 -> Plant1
            'from_object': { #ObjectID
                'object_type': 'reservoir',
                'object_name': 'Reservoir1'
            },
            'to_object': { #ObjectID
                'object_type': 'plant',
                'object_name': 'Plant1'
            }
        },
        { # Plant1 -> Reservoir2
            'from_object': { #ObjectID
                'object_type': 'plant',
                'object_name': 'Plant1'
            },
            'to_object': { #ObjectID
                'object_type': 'reservoir',
                'object_name': 'Reservoir2'
            }
        },
        { # Reservoir2 -> Plant2
            'from_object': { #ObjectID
                'object_type': 'reservoir',
                'object_name': 'Reservoir2'
            },
            'to_object': { #ObjectID
                'object_type': 'plant',
                'object_name': 'Plant2'
            }
        }
    ]
)

assert resp.status_code == 200

# Connect objects (alternative way)

# Doing this repeatedly causes segmentation fault TODO: investigate this SHOP side bug
# assert client.put('/connect/reservoir/Reservoir1/plant/Plant1').status_code == 200 # Reservoir1 -> Plant1
# assert client.put('/connect/plant/Plant1/reservoir/Reservoir2').status_code == 200 # Plant1 -> Reservoir2
# assert client.put('/connect/reservoir/Reservoir2/plant/Plant2').status_code == 200 # Reservoir2 -> Plant2

# rsv1.connect().plant.Plant1.add()
# plant1.connect().reservoir.Reservoir2.add()
# rsv2.connect().plant.Plant2.add()

resp = client.put(
    '/model/reservoir?object_name=Reservoir1',
    json={
        'attributes': {
           'start_head': 92,
           'energy_value_input': 39.7
        }
    }
)

assert resp.status_code == 200

resp = client.put(
    '/model/reservoir?object_name=Reservoir2',
    json={
        'attributes': {
           'start_head': 43,
           'energy_value_input': 38.6
        }
    }
)

assert resp.status_code == 200

# rsv1.start_head.set(92)
# rsv2.start_head.set(43)
# rsv1.energy_value_input.set(pd.Series([39.7], index=[0]))
# rsv2.energy_value_input.set(pd.Series([38.6], index=[0]))

resp = client.put(
    '/model/market?object_name=Day_ahead',
    json={
        'attributes': {
           'sale_price': 39.99,
           'buy_price': 40.01,
           'max_buy': 9999,
           'max_sale': 9999
        }
    }
)

assert resp.status_code == 200

# shop.model.market.add_object('Day_ahead')
# da = shop.model.market.Day_ahead
# da.sale_price.set(39.99)
# da.buy_price.set(40.01)
# da.max_buy.set(9999)
# da.max_sale.set(9999)

resp = client.put(
    '/model/reservoir?object_name=Reservoir1',
    json={
        'attributes': {
           'inflow': { # TimeSeries
                'timestamps': [ start_time, (pd.Timestamp(start_time) + pd.Timedelta(hours=1)).isoformat() ],
                'values': [[101, 50]]
           }
        }
    }
)

assert resp.status_code == 200

# rsv1.inflow.set(pd.DataFrame([101, 50], index=[starttime, starttime + pd.Timedelta(hours=1)]))

resp = client.post(
    '/simulation/start_sim',
    json={
        'options': [],
        'values': ['3']
    }
)

assert resp.status_code == 200

resp = client.post(
    '/simulation/set_code',
    json={
        'options': ['incremental'],
        'values': ['3']
    }
)

assert resp.status_code == 200

resp = client.post(
    '/simulation/start_sim',
    json={
        'options': [],
        'values': ['3']
    }
)

assert resp.status_code == 200

# shop.start_sim([], ['3'])
# shop.set_code(['incremental'], [])
# shop.start_sim([], ['3'])

plt.title('Production and price')
plt.xlabel('Time')
plt.ylabel('Production [MW]')

resp = client.get('/model/market/?object_name=Day_ahead')
assert resp.status_code == 200
market = resp.json()
sale_price = market['attributes']['sale_price']
ax = pd.Series(
    index=sale_price['timestamps'],
    data=np.array(sale_price['values']).flatten(),
).plot(legend='Price', secondary_y=True)

# ax = shop.model.market.Day_ahead.sale_price.get().plot(legend='Price', secondary_y=True)

resp = client.get('/model/plant/?object_name=Plant1')
assert resp.status_code == 200
plant_1 = resp.json()

resp = client.get('/model/plant/?object_name=Plant2')
assert resp.status_code == 200
plant_2 = resp.json()

pd.Series(
    index=plant_1['attributes']['production']['timestamps'],
    data=np.array(plant_1['attributes']['production']['values']).flatten(),
).plot(legend='Plant 1')

pd.Series(
    index=plant_2['attributes']['production']['timestamps'],
    data=np.array(plant_2['attributes']['production']['values']).flatten(),
).plot(legend='Plant 2')

ax.set_ylabel('Price [NOK]')
plt.show()

# shop.model.plant.Plant1.production.get().plot(legend='Plant 1')
# shop.model.plant.Plant2.production.get().plot(legend='Plant 2')
# ax.set_ylabel('Price [NOK]')
# plt.show()


resp = client.get('/model/reservoir/?object_name=Reservoir1')
assert resp.status_code == 200
reservoir_1 = resp.json()

resp = client.get('/model/reservoir/?object_name=Reservoir2')
assert resp.status_code == 200
reservoir_2 = resp.json()

plt.figure(2)

pd.Series(
    index=reservoir_1['attributes']['inflow']['timestamps'],
    data=np.array(reservoir_1['attributes']['inflow']['values']).flatten(),
).plot(legend='Reservoir 1 - inflow')

pd.Series(
    index=reservoir_1['attributes']['storage']['timestamps'],
    data=np.array(reservoir_1['attributes']['storage']['values']).flatten(),
).plot(legend='Reservoir 1 - storage')

pd.Series(
    index=reservoir_2['attributes']['storage']['timestamps'],
    data=np.array(reservoir_2['attributes']['storage']['values']).flatten(),
).plot(legend='Reservoir 2 - storage')

plt.show()

# plt.figure(2)
# prod = shop.model.reservoir.Reservoir1.inflow.get()
# prod.plot()

# prod = shop.model.reservoir.Reservoir1.storage.get()
# prod.plot()

# prod = shop.model.reservoir.Reservoir2.storage.get()
# prod.plot()

# plt.show()
