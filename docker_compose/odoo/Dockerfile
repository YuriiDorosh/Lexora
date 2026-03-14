FROM odoo:18
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \

    fonts-dejavu-core fonts-dejavu-extra gsfonts fonts-liberation fontconfig \
 && fc-cache -f -v \
 && rm -rf /var/lib/apt/lists/*

RUN chown -R odoo:odoo /var/lib/odoo

USER odoo