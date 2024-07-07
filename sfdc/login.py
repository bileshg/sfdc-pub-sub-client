import logging

import requests
from pydantic import BaseModel, computed_field

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    client_id: str
    client_secret: str
    username: str
    password: str

    @computed_field
    @property
    def grant_type(self) -> str:
        return 'password'

    def get_data(self) -> dict:
        return {
            'grant_type': self.grant_type,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.username,
            'password': self.password
        }


class LoginResponse(BaseModel):
    access_token: str
    instance_url: str
    id: str
    token_type: str
    issued_at: str
    signature: str

    @computed_field
    @property
    def tenant_id(self) -> str:
        return self.id.split('/')[-2]

    def get_metadata(self) -> tuple:
        return (
            ('accesstoken', self.access_token),
            ('instanceurl', self.instance_url),
            ('tenantid', self.tenant_id)
        )


def login(url: str, **kwargs) -> LoginResponse:
    login_request = LoginRequest(**kwargs)

    logger.info(f'Logging in to {url}')
    response = requests.post(
        url,
        data=login_request.get_data()
    )
    response.raise_for_status()

    return LoginResponse(**response.json())
