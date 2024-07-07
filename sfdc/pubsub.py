import uuid
import logging
import threading
import pubsub_api_pb2 as pb2
from datetime import datetime
from pubsub_api_pb2_grpc import PubSubStub
from sfdc.login import LoginResponse
from utils.avro_utils import encode, decode


logger = logging.getLogger(__name__)


class Subscriber:

    def __init__(self, auth: LoginResponse, stub: PubSubStub, topic: str) -> None:
        self.auth = auth
        self.stub = stub
        self.topic = topic

        # Create a semaphore to control the flow of events
        self.semaphore = threading.Semaphore(1)

    def subscribe(self, replay_type: str, replay_id: bytes, num_requested: int = 1):
        logger.info(f"Subscribing to {self.topic}")
        return self.stub.Subscribe(
            self.fetch_req_stream(replay_type, replay_id, num_requested),
            metadata=self.auth.get_metadata()
        )

    def make_fetch_request(self, replay_type: str, replay_id: bytes, num_requested: int = 1) -> pb2.FetchRequest:
        replay_preset = None
        match replay_type.upper():
            case "LATEST":
                replay_preset = pb2.ReplayPreset.LATEST
            case "EARLIEST":
                replay_preset = pb2.ReplayPreset.EARLIEST
            case "CUSTOM":
                replay_preset = pb2.ReplayPreset.CUSTOM

        return pb2.FetchRequest(
            topic_name=self.topic,
            replay_preset=replay_preset,
            replay_id=replay_id,
            num_requested=num_requested
        )

    def fetch_req_stream(self, replay_type: str, replay_id: bytes, num_requested: int = 1):
        """
        Returns a FetchRequest stream for the Subscribe RPC.
        """
        while True:
            # Only send FetchRequest when needed. Semaphore release indicates need for new FetchRequest
            self.semaphore.acquire()
            yield self.make_fetch_request(replay_type, replay_id, num_requested)

    def release_semaphore(self):
        self.semaphore.release()


class Publisher:

    def __init__(self, auth: LoginResponse, stub: PubSubStub, topic: str, integration_user_id: str) -> None:
        self.auth = auth
        self.stub = stub
        self.topic = topic
        self.integration_user_id = integration_user_id

    def make_request(self, schema_id, schema, data):
        payload = {
            "CreatedDate": int(datetime.now().timestamp()),
            "CreatedById": self.integration_user_id,
            **data
        }
        req = {
            "schema_id": schema_id,
            "payload": encode(schema, payload)
        }

        return [req]

    def publish(self, data: dict) -> pb2.PublishResponse:
        schema_id = self.stub.GetTopic(
            pb2.TopicRequest(topic_name=self.topic),
            metadata=self.auth.get_metadata()
        ).schema_id

        schema = self.stub.GetSchema(
            pb2.SchemaRequest(schema_id=schema_id),
            metadata=self.auth.get_metadata()
        ).schema_json

        data = {
            "ProcessId__c": str(uuid.uuid4()),
            "isSuccessful__c": True
        }

        logger.info(f"Publishing event to {self.topic}")
        return self.stub.Publish(
            pb2.PublishRequest(
                topic_name=self.topic,
                events=self.make_request(schema_id, schema, data),
            ),
            metadata=self.auth.get_metadata(),
        )


class EventProcessor:

    def __init__(self, auth: LoginResponse, stub: PubSubStub) -> None:
        self.auth = auth
        self.stub = stub

    def process(self, event) -> dict:
        payload_bytes = event.event.payload
        schema_id = event.event.schema_id
        schema = self.stub.GetSchema(
            pb2.SchemaRequest(schema_id=schema_id),
            metadata=self.auth.get_metadata()
        ).schema_json
        return decode(schema, payload_bytes)
