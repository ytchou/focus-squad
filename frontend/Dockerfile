FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code (will be overridden by volume mount in dev)
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
