# Stage 1 : build the app for production
FROM node:latest as build
WORKDIR /app
COPY ../../../../../../../Downloads .
RUN npm install --save --force
RUN npm run build --prod
# Stage 2 : deploy the app
FROM nginx:alpine
ENV PROJ_NAME zsoil-webapp
COPY --from=build /app/dist/$PROJ_NAME /usr/share/nginx/html
