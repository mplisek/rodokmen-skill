# CapRover / Docker: web se sestaví na počítači (npm run deploy-caprover – data, build, pack) a tady se jen
# servíruje přes nginx s přihlašovací bránou (nginx.conf vyrábí tools/export_web.py). Kontejner Python nepotřebuje.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist /usr/share/nginx/html
