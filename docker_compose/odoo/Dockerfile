FROM odoo:18

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core fonts-dejavu-extra gsfonts fonts-liberation fontconfig \
 && fc-cache -f -v \
 && rm -rf /var/lib/apt/lists/*

COPY ./requirements/base-requirements.txt /app/base-requirements.txt

RUN python3 -m pip install --no-cache-dir --break-system-packages -r /app/base-requirements.txt

RUN chown -R odoo:odoo /var/lib/odoo /app

USER odoo