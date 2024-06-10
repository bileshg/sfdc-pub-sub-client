# Salesforce PUB/SUB Client

This project is a Python application that uses the Salesforce PubSub API to subscribe to a topic, process the events received, and publish new events. It uses OAuth2 for authentication and Avro for encoding and decoding the event payloads.

## Prerequisites

- Python 3.10 or higher
- Salesforce account with access to the PubSub API

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/sfdc-pub-sub-client.git
    ```
2. Navigate to the project directory:
    ```bash
    cd sfdc-pub-sub-client
    ```
3. Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
4. Get the proto file `pubsub_api.proto` from the [GitHub repository for Pub/Sub API](https://github.com/forcedotcom/pub-sub-api).
5. Save the file in your project directory.
6. Generate the stubs for the Pub/Sub API by running the following command:
    ```bash
    python3 -m grpc_tools.protoc --proto_path=. pubsub_api.proto --python_out=. --grpc_python_out=.
    ```
The last command generates two files in your project directory:
1. `pubsub_api_pb2.py`
2. `pubsub_api_pb2_grpc.py`

It also generates client and server code and protocol buffer code for populating, serializing, and retrieving message types.

## Configuration

1. Create an environment file `.env` in your project directory.
2. Fill in your Salesforce credentials and other configuration details in the `.env` file. Example:
    ```dotenv
    LOGIN_URL='https://login.salesforce.com/services/oauth2/token'
    PUBSUB_API_ENDPOINT='api.pubsub.salesforce.com:7443'
    SFDC_CONSUMER_KEY="<your_consumer_key>"
    SFDC_CONSUMER_SECRET="<your_consumer_secret>"
    SFDC_USERNAME="<your_username>"
    SFDC_PASSWORD="<your_password>+<your_security_token>"
    SFDC_INTEGRAION_USER_ID="<your_integration_user_id>"
    ```

## Usage

Run the main script:
```bash
python main.py
```