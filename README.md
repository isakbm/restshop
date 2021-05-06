
# 1 Clone

`git clone https://gitlab.com/sintef/restshop.git`

**From now on it is assumed that you're standing at the root of this repo**

# 2 Add missing dependencies from SHOP/SDK/pyshop to `SDK/pyshop`

> Use version 14.0.0 of SHOP to copy these files from.

- shop_cplex_interface.dll
- shop_osi_interface.dll
- shop_pybind.pyd

# 3 Make sure you have a python environment

Currently pyshop supports python versions 3.7.x and 3.8.x.
Be aware that python version must match same as that used to build `shop_pybind.pyd` from SHOP.

`conda create -n SHOP python=3.7`

# 4 Activate your environment

`conda activate SHOP`

# 5 Install pyshop in editable mode

`pip install -e SDK`

# 6 Install shop_rest in editable mode

`pip install -e .`

# 7 Test the server without starting it

`pytest`

# 8 Start up the server

`uvicorn main:app --reload`

# 9 Use the SwaggerUI to play around with requests

Open this link -> [localhost:8000/docs](localhost:8000/docs)

![swagger-ui](swagger-ui.png "swagger-ui")


# 10 Debug using vscode

Hit F5 and choose FastAPI

![vscode dropdown F5](debug_vscode_dropdown.png "vscode dropdown F5")
