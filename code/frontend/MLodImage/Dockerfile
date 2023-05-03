# Stage 1 : build the app for production
FROM node:latest as build
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build --omit=dev
# Stage 2 : deploy the app
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
