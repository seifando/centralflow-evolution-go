# Build on GitHub-hosted runners. Do not compile on the production VPS.
FROM golang:1.26.11-alpine AS build
RUN apk add --no-cache git build-base libjpeg-turbo-dev libwebp-dev python3 ca-certificates
WORKDIR /build
RUN git init -q . && git remote add origin https://github.com/evolution-foundation/evolution-go.git \
 && git fetch --depth=1 origin 9337afc47e10b86cc896a6f432240e40fee95dd1 \
 && git checkout --detach FETCH_HEAD \
 && test "$(git rev-parse HEAD)" = "9337afc47e10b86cc896a6f432240e40fee95dd1"
ENV GOMAXPROCS=2
ENV GOMEMLIMIT=1536MiB
RUN go mod download && go mod vendor
COPY evolution-centralflow-go /centralflow
RUN python3 /centralflow/apply.py /build \
 && gofmt -w pkg/sendMessage/service/centralflow.go pkg/sendMessage/handler/centralflow.go vendor/go.mau.fi/whatsmeow/centralflow.go \
 && CGO_ENABLED=1 go build -p 2 -mod=vendor -ldflags "-X main.version=0.7.2-centralflow-0.6.1" -o server ./cmd/evolution-go
FROM alpine:3.19.1 AS final
RUN apk add --no-cache tzdata ffmpeg libjpeg-turbo libwebp poppler-utils ca-certificates
WORKDIR /app
COPY --from=build /build/server .
COPY --from=build /build/manager/dist ./manager/dist
COPY --from=build /build/VERSION ./VERSION
COPY evolution-centralflow-go /opt/centralflow-source
COPY LICENSES /usr/share/licenses/centralflow
COPY LICENSE NOTICE /usr/share/licenses/centralflow/
ENV TZ=America/Sao_Paulo
ENV SERVER_PORT=8080
ARG SOURCE_URL=https://github.com/seifando/centralflow-evolution-go
ARG REVISION=local-unpublished
LABEL org.opencontainers.image.source=$SOURCE_URL org.opencontainers.image.revision=$REVISION \
 io.centralflow.protocol="centralflow-publishing/1" io.centralflow.upstream="evolution-go:0.7.2" io.centralflow.version="0.6.1"
EXPOSE 8080
ENTRYPOINT ["/app/server"]
