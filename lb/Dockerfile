FROM nginx:1.27-alpine
# LB_MODE=internal -> UPSTREAM_1 / UPSTREAM_2 as host:port   (docker compose)
# LB_MODE=public   -> UPSTREAM_1_HOST / UPSTREAM_2_HOST over HTTPS (e.g. Render public URLs)
ENV PORT=80 LB_MODE=internal UPSTREAM_PORT=443 UPSTREAM_SCHEME=https
COPY internal.conf.template public.conf.template /opt/lb/
COPY select-template.sh /docker-entrypoint.d/15-select-template.sh
RUN chmod +x /docker-entrypoint.d/15-select-template.sh
