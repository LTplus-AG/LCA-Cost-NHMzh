import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test data paths
TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

# Check if in dev mode
dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'

# MinIO test configuration
MINIO_TEST_CONFIG = {
    'endpoint': 'localhost:9000' if dev_mode else f"{os.getenv('MINIO_ENDPOINT')}:{os.getenv('MINIO_PORT')}",
    'access_key': os.getenv('MINIO_ACCESS_KEY'),
    'secret_key': os.getenv('MINIO_SECRET_KEY'),
    'bucket': os.getenv('MINIO_LCA_COST_DATA_BUCKET')
}

# Ensure test directories exist
for dir_path in [DATA_DIR, INPUT_DIR, OUTPUT_DIR]:
    dir_path.mkdir(exist_ok=True) 