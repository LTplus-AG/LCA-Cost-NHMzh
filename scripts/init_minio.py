#!/usr/bin/env python3
"""
Script to initialize MinIO bucket for testing.
This script creates the necessary buckets and uploads sample files.
"""

import os
from minio import Minio
from minio.error import S3Error
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_minio():
    """Initialize MinIO bucket and upload sample files"""
    try:
        # MinIO client setup
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio1:9000")
        minio_access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
        minio_secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        
        print(f"Connecting to MinIO at {minio_endpoint}")
        client = Minio(
            minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=False  # Set to True if using HTTPS
        )
        
        # Create buckets if they don't exist
        buckets = ["ifc-files", "lca-results", "cost-results"]
        for bucket in buckets:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"Created bucket: {bucket}")
            else:
                print(f"Bucket already exists: {bucket}")
        
        # Upload sample IFC file (using a JSON file as a placeholder)
        sample_ifc_path = "tests/data/input/sample_ifc_result.json"
        if os.path.exists(sample_ifc_path):
            client.fput_object(
                "ifc-files",
                "sample.ifc",
                sample_ifc_path,
                content_type="application/json"
            )
            print(f"Uploaded sample IFC file: {sample_ifc_path}")
        
        # Create a sample Kafka message file
        sample_message = {
            "fileUrl": "http://minio1:9000/ifc-files/sample.ifc",
            "projectId": "TEST-001"
        }
        
        with open("tests/data/input/sample_kafka_message.json", "w") as f:
            json.dump(sample_message, f, indent=2)
        
        # Upload the sample Kafka message
        client.fput_object(
            "ifc-files",
            "sample_kafka_message.json",
            "tests/data/input/sample_kafka_message.json",
            content_type="application/json"
        )
        print("Uploaded sample Kafka message")
        
        print("MinIO initialization completed successfully")
        
    except S3Error as e:
        print(f"Error initializing MinIO: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    init_minio() 