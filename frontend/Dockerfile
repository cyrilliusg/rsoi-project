# syntax=docker/dockerfile:1.7
# Stage 1: deps
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
# Install with npm: with no lockfile we fall back to `npm install` which
# resolves and locks transitive deps inside the image. Acceptable for a
# learning project; production would commit package-lock.json.
RUN --mount=type=cache,target=/root/.npm \
    npm install --no-audit --no-fund

# Stage 2: builder
FROM node:20-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_IDP_ISSUER=http://localhost:8090
ARG NEXT_PUBLIC_GATEWAY_URL=http://localhost:8080
ARG NEXT_PUBLIC_OAUTH_CLIENT_ID=spa
ARG NEXT_PUBLIC_OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback
ENV NEXT_PUBLIC_IDP_ISSUER=$NEXT_PUBLIC_IDP_ISSUER \
    NEXT_PUBLIC_GATEWAY_URL=$NEXT_PUBLIC_GATEWAY_URL \
    NEXT_PUBLIC_OAUTH_CLIENT_ID=$NEXT_PUBLIC_OAUTH_CLIENT_ID \
    NEXT_PUBLIC_OAUTH_REDIRECT_URI=$NEXT_PUBLIC_OAUTH_REDIRECT_URI

RUN npm run build

# Stage 3: runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
