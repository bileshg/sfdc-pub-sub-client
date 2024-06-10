import os
import io
import uuid
import grpc
import requests
import threading
import certifi
import avro.io
import avro.schema
import pubsub_api_pb2 as pb2
import pubsub_api_pb2_grpc as pb2_grpc
from dotenv import load_dotenv
from pprint import pprint
from datetime import datetime

# Load the environment variables
load_dotenv()

# Get the environment variables
LOGIN_URL = os.getenv('LOGIN_URL')
PUBSUB_API_ENDPOINT = os.getenv('PUBSUB_API_ENDPOINT')
CLIENT_ID = os.getenv('SFDC_CONSUMER_KEY')
CLIENT_SECRET = os.getenv('SFDC_CONSUMER_SECRET')
USERNAME = os.getenv('SFDC_USERNAME')
PASSWORD = os.getenv('SFDC_PASSWORD')
INTEGRATION_USER_ID = os.getenv('SFDC_INTEGRAION_USER_ID')

# Create a semaphore to control the flow of events
semaphore = threading.Semaphore(1)

# Define the pub and sub topics
sub_topic = "/data/AccountChangeEvent"
pub_topic = "/event/Account_Processed_Platform_Event__e"


def login(url, client_id, client_secret, username, password):
    """
    Function to log in to Salesforce using OAuth2.

    Parameters:
    url (str): The login URL for the Salesforce app.
    client_id (str): The client ID for the Salesforce app.
    client_secret (str): The client secret for the Salesforce app.
    username (str): The username for the Salesforce account.
    password (str): The password for the Salesforce account.

    Returns:
    dict: A dictionary containing the response from the Salesforce login API.
    """
    data = {
        'grant_type': 'password',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password
    }
    response = requests.post(
        url,
        data=data
    )
    response.raise_for_status()
    return response.json()


def create_auth_metadata(login_response):
    """
    Function to create authentication metadata from the login response.

    Parameters:
    login_response (dict): The response from the Salesforce login API.

    Returns:
    tuple: A tuple containing the authentication metadata.
    """
    session_id = login_response['access_token']
    instance_url = login_response['instance_url']
    tenant_id = login_response['id'].split('/')[-2]
    return ('accesstoken', session_id), ('instanceurl', instance_url), ('tenantid', tenant_id)


def fetch_req_stream(topic):
    """
    Generator function to yield FetchRequest objects for a given topic.

    Parameters:
    topic (str): The topic to fetch events from.

    Yields:
    FetchRequest: A FetchRequest object for the given topic.
    """
    while True:
        semaphore.acquire()
        yield pb2.FetchRequest(
            topic_name=topic,
            replay_preset=pb2.ReplayPreset.LATEST,
            num_requested=1
        )


# Encode the payload
def encode(schema, payload):
    """
    Function to encode a payload using a given Avro schema.

    Parameters:
    schema (str): The Avro schema to use for encoding.
    payload (dict): The payload to encode.

    Returns:
    bytes: The encoded payload.
    """
    schema = avro.schema.parse(schema)
    buf = io.BytesIO()
    encoder = avro.io.BinaryEncoder(buf)
    writer = avro.io.DatumWriter(schema)
    writer.write(payload, encoder)
    return buf.getvalue()


def decode(schema, payload):
    """
    Function to decode a payload using a given Avro schema.

    Parameters:
    schema (str): The Avro schema to use for decoding.
    payload (bytes): The payload to decode.

    Returns:
    dict: The decoded payload.
    """
    avro_schema = avro.schema.parse(schema)
    buf = io.BytesIO(payload)
    decoder = avro.io.BinaryDecoder(buf)
    reader = avro.io.DatumReader(avro_schema)
    return reader.read(decoder)


def process_event(stub, auth_metadata, event):
    """
    Function to process an event.

    Parameters:
    stub (PubSubStub): The PubSubStub object to use for API calls.
    auth_metadata (tuple): The authentication metadata.
    event (Event): The event to process.

    Returns:
    dict: The decoded payload of the event.
    """
    payload_bytes = event.event.payload
    schema_id = event.event.schema_id
    schema = stub.GetSchema(
        pb2.SchemaRequest(schema_id=schema_id),
        metadata=auth_metadata
    ).schema_json
    return decode(schema, payload_bytes)


def make_publish_request(schema_id, schema, data):
    """
    Function to create a PublishRequest object.

    Parameters:
    schema_id (str): The ID of the Avro schema to use for encoding.
    schema (str): The Avro schema to use for encoding.
    data (dict): The data to include in the payload.

    Returns:
    list: A list containing a dictionary with the schema ID and the encoded payload.
    """
    payload = {
        "CreatedDate": int(datetime.now().timestamp()),
        "CreatedById": INTEGRATION_USER_ID,
        **data
    }
    req = {
        "schema_id": schema_id,
        "payload": encode(schema, payload)
    }

    return [req]


def publish_event(stub, auth_metadata, input_payload):
    """
    Function to publish an event.

    Parameters:
    stub (PubSubStub): The PubSubStub object to use for API calls.
    auth_metadata (tuple): The authentication metadata.
    input_payload (dict): The payload to publish.

    Returns:
    PublishResponse: The response from the Publish API call.
    """
    schema_id = stub.GetTopic(
        pb2.TopicRequest(topic_name=pub_topic),
        metadata=auth_metadata
    ).schema_id
    schema = stub.GetSchema(
        pb2.SchemaRequest(schema_id=schema_id),
        metadata=auth_metadata
    ).schema_json

    data = {
        "ProcessId__c": str(uuid.uuid4()),
        "isSuccessful__c": True
    }

    return stub.Publish(
        pb2.PublishRequest(
            topic_name=pub_topic,
            events=make_publish_request(schema_id, schema, data),
        ),
        metadata=auth_metadata,
    )


def main():
    """
    The main function of the script.
    It sets up the gRPC channel, logs in to Salesforce, subscribes to a topic, and processes and publishes events.
    """
    # Read the certificate
    with open(certifi.where(), 'rb') as f:
        creds = grpc.ssl_channel_credentials(f.read())

        # Create a gRPC channel
        with grpc.secure_channel(PUBSUB_API_ENDPOINT, creds) as channel:

            auth_metadata = create_auth_metadata(
                login(LOGIN_URL, CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD)
            )
            stub = pb2_grpc.PubSubStub(channel)

            print(f'Subscribing to {sub_topic}')
            substream = stub.Subscribe(
                fetch_req_stream(sub_topic),
                metadata=auth_metadata
            )

            for event in substream:
                if event.events:
                    semaphore.release()
                    print(f"# of events received: {len(event.events)}")
                    for e in event.events:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing event: {e.event.id}")
                        decoded = process_event(stub, auth_metadata, e)
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Decoded Payload:")
                        pprint(decoded)
                        response = publish_event(stub, auth_metadata, decoded)
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Published event:")
                        pprint(response)
                else:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] The subscription is active.")


if __name__ == '__main__':
    main()
