FROM new_shop as base

FROM python:3.8-rc-slim as app

WORKDIR /root/restshop
COPY . .

# remove any dlls and pyd's if they exist and replace with .so (for linux)
RUN rm SDK/pyshop/*.dll && rm SDK/pyshop/*.pyd
COPY --from=base /root/shop_repo/SDK/pyshop/*.so SDK/pyshop/.

# license
COPY --from=base /root/shop_repo/shop/bin/SHOP_license.dat .
ENV ICC_COMMAND_PATH=/root/restshop

RUN pip install SDK/. && pip install .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]