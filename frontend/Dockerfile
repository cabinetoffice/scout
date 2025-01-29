FROM node:20.13.1-alpine@sha256:a7b980c958bfe4d84ee9263badd95a40c8bb50ad5afdb87902c187fefaef0e24 AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . ./
RUN npm run build

FROM builder AS  runner

WORKDIR /app

COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/public /app/public

EXPOSE 3000

CMD ["npm", "start"]