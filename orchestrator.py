import json
import logging
import os
import time
from confluent_kafka import Consumer, Producer
from typing import Optional, Dict, Any
from flask import Flask, jsonify, request
from flask_cors import CORS

from modules.ifc_processing_service import IFCExtractBuildingElementsService
from modules.cost_processor import CostProcessor
from modules.lca_processor import LCAProcessor
from modules.storage.db_manager import DatabaseManager, DEFAULT_PROJECT_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://172.22.0.5:5173"  # Docker network URL
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

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
        
        # Initialize database
        self.db = DatabaseManager(self.db_path)
        
        # Initialize Kafka consumer and producer
        self.consumer = Consumer({
            'bootstrap.servers': self.kafka_broker,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest'
        })
        
        self.producer = Producer({
            'bootstrap.servers': self.kafka_broker
        })
        
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
                project_name=project_name,
                project_id=DEFAULT_PROJECT_ID
            )
            ifc_service.run()
            
            # Step 2: Run LCA Processing
            lca_processor = LCAProcessor(
                input_file_path=None,  # Data loaded from DB
                material_mappings_file=None,  # Mappings in DB
                db=self.db,
                project_id=DEFAULT_PROJECT_ID
            )
            lca_processor.run()
            
            # Step 3: Run Cost Processing
            cost_processor = CostProcessor(
                input_file_path=None,  # Data loaded from DB
                data_file_path=None,  # Cost data in DB
                output_file=None,  # Results stored in DB
                db=self.db,
                project_id=DEFAULT_PROJECT_ID
            )
            cost_processor.run()
            
            # Prepare results JSON combining IFC extraction, LCA and Cost results
            results_json = {
                'ifcData': getattr(ifc_service, 'result', {}),
                'lcaResults': getattr(lca_processor, 'results', {}),
                'costResults': getattr(cost_processor, 'results', {}),
                'materialMappings': getattr(lca_processor, 'material_mappings', {})
            }
            
            return DEFAULT_PROJECT_ID
            
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

# Create orchestrator instance
orchestrator = Orchestrator()

@app.route('/api/ifc-results/<project_id>', methods=['GET'])
def get_ifc_results(project_id):
    """Get IFC results including materials and mappings for a project."""
    try:
        logging.info(f"Received request for IFC results for project: {project_id}")
        logging.info(f"Database path: {orchestrator.db.db_path}")
        logging.info(f"Database connection status: {orchestrator.db.conn is not None}")
        
        # Check if project exists
        project_info = orchestrator.db.get_project_info(project_id)
        logging.info(f"Project info: {json.dumps(project_info, indent=2) if project_info else 'Not found'}")
        
        results = orchestrator.db.get_ifc_results(project_id)
        logging.info(f"Retrieved results from database: {json.dumps(results, indent=2)}")
        
        if not results.get('ifcData', {}).get('materials'):
            logging.warning(f"No materials found for project {project_id}")
            
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error getting IFC results: {str(e)}", exc_info=True)
        default_response = {
            'projectId': project_id,
            'ifcData': { 'materials': [] },
            'materialMappings': {}
        }
        logging.info(f"Returning default response: {json.dumps(default_response, indent=2)}")
        return jsonify(default_response)

@app.route('/api/update-material-mappings', methods=['POST'])
def update_material_mappings():
    """Update material mappings for a project."""
    try:
        data = request.json
        logging.info(f"Received material mappings update request: {json.dumps(data, indent=2)}")
        project_id = data.get('projectId')
        material_mappings = data.get('materialMappings', {})
        
        orchestrator.db.update_material_mappings(
            project_id=project_id,
            material_mappings=material_mappings
        )
        
        response = {'message': 'Material mappings updated successfully'}
        logging.info("Material mappings updated successfully")
        return jsonify(response)
    except Exception as e:
        error_msg = f"Error updating material mappings: {str(e)}"
        logging.error(error_msg)
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    # Enable debug mode but disable auto-reloader to prevent database lock conflicts
    app.debug = True
    app.config['DEBUG'] = True
    app.config['USE_RELOADER'] = False
    # Run Flask app on all interfaces
    app.run(host='0.0.0.0', port=5000, use_reloader=False, threaded=True) 