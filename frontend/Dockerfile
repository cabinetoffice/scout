FROM public.ecr.aws/docker/library/node:20-bookworm AS builder

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