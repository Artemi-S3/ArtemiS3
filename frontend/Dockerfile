FROM node:25-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

EXPOSE 5173

# dev command
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]