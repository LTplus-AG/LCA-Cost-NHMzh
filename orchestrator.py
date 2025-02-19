import json
import logging
import os
import time
from confluent_kafka import Consumer, Producer
from typing import Optional, Dict, Any

from modules.ifc_processing_service import IFCExtractBuildingElementsService
from modules.cost_processor import CostProcessor
from modules.lca_processor import LCAProcessor
from modules.storage.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Orchestrator:
    def __init__(self):
        # Kafka configuration
        self.kafka_broker = os.getenv('KAFKA_BROKER', 'broker:29092')
        self.input_topic = os.getenv('KAFKA_INPUT_TOPIC', 'ifc-files')
        self.output_topic = os.getenv('KAFKA_OUTPUT_TOPIC', 'ifc_processed')
        self.group_id = os.getenv('KAFKA_GROUP_ID', 'ifc_processor_group')
        
        # Service configuration
        self.ifc_api_endpoint = os.getenv('IFC_API_ENDPOINT', 
            'https://openbim-service-production.up.railway.app/api/ifc/extract-building-elements')
        self.db_path = os.getenv('DB_PATH', '/app/data/nhmzh_data.duckdb')
        
        # Initialize Kafka consumer and producer
        self.consumer = Consumer({
            'bootstrap.servers': self.kafka_broker,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest'
        })
        
        self.producer = Producer({
            'bootstrap.servers': self.kafka_broker
        })
        
        # Initialize database
        self.db = DatabaseManager(self.db_path)
        
        # Subscribe to input topic
        self.consumer.subscribe([self.input_topic])
        logging.info(f"Subscribed to topic: {self.input_topic}")

    def process_ifc(self, ifc_url: str, project_name: Optional[str] = None) -> str:
        """Process an IFC file and run LCA and Cost calculations."""
        try:
            # Step 1: Extract IFC data
            ifc_service = IFCExtractBuildingElementsService(
                ifc_url=ifc_url,
                api_endpoint=self.ifc_api_endpoint,
                db=self.db,
                project_name=project_name
            )
            ifc_service.run()
            project_id = ifc_service.project_id
            
            # Step 2: Run LCA Processing
            lca_processor = LCAProcessor(
                input_file_path=None,  # Data loaded from DB
                material_mappings_file=None,  # Mappings in DB
                db=self.db,
                project_id=project_id
            )
            lca_processor.run()
            
            # Step 3: Run Cost Processing
            cost_processor = CostProcessor(
                input_file_path=None,  # Data loaded from DB
                data_file_path=None,  # Cost data in DB
                output_file=None,  # Results stored in DB
                db=self.db,
                project_id=project_id
            )
            cost_processor.run()
            
            return project_id
            
        except Exception as e:
            logging.exception("Error processing IFC file")
            raise

    def handle_message(self, message: Any) -> None:
        """Handle incoming Kafka message."""
        try:
            raw_value = message.value()
            if not raw_value:
                logging.error("Received an empty message payload.")
                return

            # Decode and strip whitespace from the raw value.
            ifc_url = raw_value.decode('utf-8').strip()
            if not ifc_url:
                logging.error("Message value is empty after decoding and stripping.")
                return

            # Process the IFC file with the URL directly
            project_id = self.process_ifc(ifc_url)

            # Send success response
            response = {
                'status': 'completed',
                'project_id': project_id,
                'message': f"LCA and Cost processing completed for project {project_id}"
            }

            self.producer.produce(
                self.output_topic,
                value=json.dumps(response).encode('utf-8')
            )
            self.producer.flush()

            logging.info(f"Processing completed for project {project_id}")

        except Exception as e:
            logging.exception("Error handling message")

    def run(self):
        """Main processing loop."""
        try:
            logging.info("Starting orchestrator service...")
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    logging.error(f"Consumer error: {msg.error()}")
                    continue
                    
                self.handle_message(msg)
                
        except KeyboardInterrupt:
            logging.info("Shutting down...")
        finally:
            self.consumer.close()
            self.db.close()

if __name__ == '__main__':
    orchestrator = Orchestrator()
    orchestrator.run() 