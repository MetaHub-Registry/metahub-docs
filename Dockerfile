# Stage 1: Build (also used as the CI `--target build` test image)
FROM python:3.12-alpine AS build

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY mkdocs.yml ./
COPY docs ./docs

# Version string for the footer. CI passes the resolved value (git tag or
# main:<sha>) via --build-arg; defaults to "dev" for plain local builds.
ARG DOCS_VERSION=dev
ENV MKDOCS_VERSION=${DOCS_VERSION}
ENV MKDOCS_COPYRIGHT="MetaHub Docs · ${DOCS_VERSION}"

# `mkdocs build --strict` runs here in CI (Test stage). Produces ./site.
RUN mkdocs build --strict

# Stage 2: Serve
FROM nginx:alpine

COPY --from=build /app/site /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
