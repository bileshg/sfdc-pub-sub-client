# Salesforce PUB/SUB Client

This project is a simple Python application that uses the Salesforce PubSub API to subscribe to a topic, process the events received, and publish new events. It uses OAuth2 for authentication and Avro for encoding and decoding the event payloads.

## Prerequisites

- Python 3.10 or higher
- Salesforce account with access to the PubSub API

## Salesforce Configuration

Before running the application, you need to configure your Salesforce account:

1. Create a new Connected App in Salesforce. This will provide you with the `Consumer Key` and `Consumer Secret` needed for OAuth2 authentication.
2. Make sure that the Connected App has the required application permissions.
3. Enable Change Data Capture for the `Account` object in Salesforce.
4. Create the `Account_Processed_Platform_Event__e` Platform Event with the following custom fields in Salesforce.
   - `isSuccessful__c`: Checkbox
   - `ProcessId__c`: Text(255)

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

1. Update the `config.ini` file with the configuration details.
2. Create an environment file (say) `.env` in your project directory based on what you have in the `config.ini` file. The environment file should contain the Salesforce credentials and other configuration details. The application will read these values from the environment
3. Following is an example of the `.env` file:
    ```dotenv
    SFDC_CONSUMER_KEY="<your_consumer_key>"
    SFDC_CONSUMER_SECRET="<your_consumer_secret>"
    SFDC_USERNAME="<your_username>"
    SFDC_PASSWORD="<your_password>+<your_security_token>"
    SFDC_INTEGRAION_USER_ID="<your_integration_user_id>"
    ```

Please replace `<your_consumer_key>`, `<your_consumer_secret>`, `<your_username>`, and `<your_password>+<your_security_token>` with your actual Salesforce credentials. The password should be your Salesforce password concatenated with your security token. `<your_integration_user_id>` should be the ID of the integration user in Salesforce that will be used to publish events.

## Usage

Run the main script:
```bash
python main.py
```