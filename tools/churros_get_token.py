from getpass import getpass
from pprint import pprint

import pydantic
import requests

LOGIN_QUERY = """
mutation LoginUser($email: String!, $password: String!) {
  login(email: $email, password: $password) {
      __typename
    ... on Error {
      message
    }
    ... on MutationLoginSuccess {
      data {
        active
        createdAt
        expiresAt
        id
        token
      }
    }
  }
}
"""

ENDPOINT = 'https://churros.inpt.fr/graphql'


class MutationLoginSuccess(pydantic.BaseModel):
    active: bool
    createdAt: str
    expiresAt: str
    id: str
    token: str


class LoginData(pydantic.BaseModel):
    data: MutationLoginSuccess


class _LoginResponse(pydantic.BaseModel):
    login: LoginData


class LoginResponse(pydantic.BaseModel):
    data: _LoginResponse


def main():
    email = input('Email: ')
    password = getpass()

    variables = {'email': email, 'password': password}

    req_data = {'query': LOGIN_QUERY, 'variables': variables}

    resp = requests.post(ENDPOINT, json=req_data)
    resp.raise_for_status()
    resp_data = resp.json()
    pprint(resp_data)

    resp_obj = LoginResponse.model_validate(resp.json())
    token_data = resp_obj.data.login.data

    print(token_data)
    print(token_data.token)


if __name__ == '__main__':
    main()
