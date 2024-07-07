import configparser

from dotenv import dotenv_values
from pydantic.v1 import BaseSettings


class SfdcCredentials(BaseSettings):
    client_id: str
    client_secret: str
    username: str
    password: str


class SfdcConfig(BaseSettings):
    credentials: SfdcCredentials
    login_url: str
    pubsub_api_endpoint: str
    sub_topic: str
    pub_topic: str
    integration_user_id: str
    replay_id_file: str

    def get_credentials(self):
        return self.credentials.dict()


class RunConfig(BaseSettings):
    log_level: str
    stop_switch: bool
    stop_after: int


class Config(BaseSettings):
    env: str
    sfdc: SfdcConfig
    run: RunConfig

    @classmethod
    def from_file(cls, file_path: str, environment: str) -> 'Config':
        env = environment.upper()
        config = configparser.ConfigParser()
        config.read(file_path)

        secrets = dotenv_values(config[env]['secrets_file'])

        def get_value(key: str, default: str = None) -> str:
            return config[env].get(key, config['DEFAULT'].get(key, default))

        sfdc_creds = SfdcCredentials(
            client_id=secrets['SFDC_CONSUMER_KEY'],
            client_secret=secrets['SFDC_CONSUMER_SECRET'],
            username=secrets['SFDC_USERNAME'],
            password=secrets['SFDC_PASSWORD'],
        )

        sfdc = SfdcConfig(
            credentials=sfdc_creds,
            login_url=get_value('login_url'),
            pubsub_api_endpoint=get_value('pubsub_api_endpoint'),
            sub_topic=get_value('sub_topic'),
            pub_topic=get_value('pub_topic'),
            integration_user_id=secrets['SFDC_INTEGRAION_USER_ID'],
            replay_id_file=get_value('replay_id_file')
        )

        run = RunConfig(
            log_level=get_value('log_level', 'INFO'),
            stop_switch=get_value('stop_switch', 'off').lower() == 'on',
            stop_after=int(get_value('stop_after', '10'))
        )

        return cls(
            env=env,
            sfdc=sfdc,
            run=run
        )
