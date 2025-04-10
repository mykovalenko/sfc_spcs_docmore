import os
import snowflake.connector
from snowflake.snowpark import Session
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import serialization

def read_file(file: str):
  with open(file, 'r') as f:
    return f.read()

def base_conf():
    return {
        'protocol': "https",
        'host': os.getenv('SNOWFLAKE_HOST'),
        'account': os.getenv('SNOWFLAKE_ACCOUNT'),
        'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
        'database': os.getenv('SNOWFLAKE_DATABASE'),
        'schema': os.getenv('SNOWFLAKE_SCHEMA'),
        'role':  os.getenv('SNOWFLAKE_ROLE'),
        'client_session_keep_alive': True,
        'session_parameters': {'QUERY_TAG': 'APP:Cortexan',}
    }

def get_environ_creds():
    if 'SNOWFLAKE_USER' in os.environ:
        creds = base_conf()
        creds['user'] = os.getenv('SNOWFLAKE_USER')
        creds['password'] = os.getenv('SNOWFLAKE_PASSWORD')
        return creds

def get_keypair_creds():
    if os.path.isfile("./cfg/rsa_key.p8"):
        passphrase = os.getenv('SNOWFLAKE_ACCOUNT')
        private_key = read_file('./cfg/rsa_key.p8')

        p_key = serialization.load_pem_private_key(
            private_key.encode(),
            password=passphrase.encode(),
            backend=default_backend()
        )

        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        creds = base_conf()
        creds['user'] = os.getenv('SNOWFLAKE_USER')
        creds['private_key'] = pkb
        return creds

def get_oauth_creds():
    if os.path.isfile("/snowflake/session/token"):
        creds = base_conf()
        creds['authenticator'] = "oauth"
        creds['token'] = read_file('/snowflake/session/token')
        return creds

def get_snowcli_creds():
    if 'SNOWCLI_CONNECTION_NAME' in os.environ and os.path.isfile(f"{os.getenv('HOME')}/.snowflake/config.toml"):
        creds = {
            'connection_name': os.getenv('SNOWCLI_CONNECTION_NAME'),
            'client_session_keep_alive': True,
            'session_parameters': {'QUERY_TAG': 'APP:Cortexan',}
        }

        return creds

def connection() -> snowflake.connector.SnowflakeConnection:
    if os.path.isfile("/snowflake/session/token"):
        creds = get_oauth_creds()
    
    elif os.path.isfile("./cfg/rsa_key.p8"):
        creds = get_keypair_creds()

    elif 'SNOWCLI_CONNECTION_NAME' in os.environ:
        creds = get_snowcli_creds()

    else:
        creds = get_environ_creds()

    connection = snowflake.connector.connect(**creds)
    return connection

def session() -> Session:
    return Session.builder.configs({"connection": connection()}).create()
