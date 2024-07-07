import os
import grpc
import logging
import certifi
import pubsub_api_pb2_grpc as pb2_grpc
from pprint import pformat
from binascii import hexlify
from sfdc.login import login, LoginResponse
from sfdc.pubsub import Subscriber, Publisher, EventProcessor
from utils.config_utils import Config
from utils.replay_utils import load_replay_id, save_replay_id

# read the environment variable
env = os.getenv('ENV', 'DEFAULT').upper()
config: Config = Config.from_file('config.ini', env)

# instantiate logger
logger = logging.getLogger()
logger.setLevel(getattr(logging, config.run.log_level.upper()))

# define handler and formatter
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# add formatter to handler
handler.setFormatter(formatter)

# add handler to logger
logger.addHandler(handler)


def main():
    """
    The main function of the script.
    It sets up the gRPC channel, logs in to Salesforce, subscribes to a topic, and processes and publishes events.
    """
    # Read the certificate
    with open(certifi.where(), 'rb') as f:
        creds = grpc.ssl_channel_credentials(f.read())

        # Create a gRPC channel
        with grpc.secure_channel(config.sfdc.pubsub_api_endpoint, creds) as channel:

            auth: LoginResponse = login(
                config.sfdc.login_url,
                **config.sfdc.get_credentials()
            )
            stub = pb2_grpc.PubSubStub(channel)

            subscriber = Subscriber(auth, stub, config.sfdc.sub_topic)
            event_processor = EventProcessor(auth, stub)
            publisher = Publisher(auth, stub, config.sfdc.pub_topic, config.sfdc.integration_user_id)

            if replay_id := load_replay_id(config.sfdc.replay_id_file):
                logger.info(f"Replaying from: {hexlify(replay_id)}")
                substream = subscriber.subscribe("CUSTOM", replay_id, 1)
            else:
                substream = subscriber.subscribe("LATEST", b"", 1)

            no_event_count = 0
            for event in substream:
                if event.events:
                    subscriber.release_semaphore()
                    logger.info(f"# of events received: {len(event.events)}")
                    for e in event.events:
                        logger.info(f"Processing event: {e.event.id}")
                        decoded = event_processor.process(e)
                        logger.debug(pformat(decoded))
                        response = publisher.publish(decoded)
                        logger.debug(pformat(response))

                    save_replay_id(config.sfdc.replay_id_file, event.latest_replay_id)
                    no_event_count = 0
                else:
                    no_event_count += 1
                    logger.info("Subscription is active")

                # Log the latest replay ID
                logger.info(f"Latest Replay ID: {hexlify(event.latest_replay_id)}")

                # Check if we need to stop
                if config.run.stop_switch and no_event_count >= config.run.stop_after:
                    break

            logger.info("Subscription has ended")


if __name__ == '__main__':
    logger.info(f"Environment: {env}")
    main()
