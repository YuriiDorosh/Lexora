FROM nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY ./docker_compose/nginx/nginx.conf /etc/nginx/nginx.conf