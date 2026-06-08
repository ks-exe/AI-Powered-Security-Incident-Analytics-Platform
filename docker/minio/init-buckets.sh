#!/bin/sh
set -e

echo "Waiting for MinIO to be ready..."
sleep 5

mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER:-minioadmin} ${MINIO_ROOT_PASSWORD:-minioadmin123}

echo "Creating buckets..."
mc mb --ignore-existing myminio/bronze-layer
mc mb --ignore-existing myminio/silver-layer
mc mb --ignore-existing myminio/gold-layer
mc mb --ignore-existing myminio/raw-data

echo "Buckets created successfully:"
mc ls myminio/
