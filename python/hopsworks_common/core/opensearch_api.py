#
#   Copyright 2023 Logical Clocks AB
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from __future__ import annotations

from typing import Any, Dict

from furl import furl
from hopsworks_common import client, usage
from hopsworks_common.client.exceptions import FeatureStoreException
from hopsworks_common.core.variable_api import VariableApi


class OPENSEARCH_CONFIG:
    ELASTIC_ENDPOINT_ENV_VAR = "ELASTIC_ENDPOINT"
    SSL_CONFIG = "es.net.ssl"
    NODES_WAN_ONLY = "es.nodes.wan.only"
    NODES = "es.nodes"
    SSL_KEYSTORE_LOCATION = "es.net.ssl.keystore.location"
    SSL_KEYSTORE_PASSWORD = "es.net.ssl.keystore.pass"
    SSL_TRUSTSTORE_LOCATION = "es.net.ssl.truststore.location"
    SSL_TRUSTSTORE_PASSWORD = "es.net.ssl.truststore.pass"
    HTTP_AUTHORIZATION = "es.net.http.header.Authorization"
    INDEX = "es.resource"
    HOSTS = "hosts"
    HTTP_COMPRESS = "http_compress"
    HEADERS = "headers"
    USE_SSL = "use_ssl"
    VERIFY_CERTS = "verify_certs"
    SSL_ASSERT_HOSTNAME = "ssl_assert_hostname"
    CA_CERTS = "ca_certs"


class OpenSearchApi:
    def __init__(self) -> None:
        self._variable_api: VariableApi = VariableApi()

    def _get_opensearch_url(self) -> str:
        if client._is_external():
            external_domain = self._variable_api.get_loadbalancer_external_domain(
                "opensearch"
            )
            return f"https://{external_domain}:9200"
        else:
            service_discovery_domain = self._variable_api.get_service_discovery_domain()
            if service_discovery_domain == "":
                raise FeatureStoreException(
                    "Client could not locate service_discovery_domain "
                    "in Hopsworks cluster configuration or variable is empty."
                )
            return f"https://rest.elastic.service.{service_discovery_domain}:9200"

    @usage.method_logger
    def get_project_index(self, index: str) -> str:
        """
        This helper method prefixes the supplied index name with the project name to avoid index name clashes.

        # Arguments
            index: the opensearch index to interact with.

        # Returns
            `str`: A valid opensearch index name.
        """
        _client = client.get_instance()
        return (_client._project_name + "_" + index).lower()

    @usage.method_logger
    def get_default_py_config(self) -> Dict[str, Any]:
        """
        Get the required opensearch configuration to setup a connection using the *opensearch-py* library.

        ```python

        import hopsworks
        from opensearchpy import OpenSearch

        project = hopsworks.login()

        opensearch_api = project.get_opensearch_api()

        client = OpenSearch(**opensearch_api.get_default_py_config())

        ```

        # Returns
            `dict`: A dictionary with required configuration.
        """
        url = furl(self._get_opensearch_url())
        return {
            OPENSEARCH_CONFIG.HOSTS: [{"host": url.host, "port": url.port}],
            OPENSEARCH_CONFIG.HTTP_COMPRESS: False,
            OPENSEARCH_CONFIG.HEADERS: {
                "Authorization": self._get_authorization_token()
            },
            OPENSEARCH_CONFIG.USE_SSL: True,
            OPENSEARCH_CONFIG.VERIFY_CERTS: True,
            OPENSEARCH_CONFIG.SSL_ASSERT_HOSTNAME: False,
            OPENSEARCH_CONFIG.CA_CERTS: client.get_instance()._get_ca_chain_path(),
        }

    def _get_authorization_token(self) -> str:
        """Get opensearch jwt token.

        # Returns
            `str`: OpenSearch jwt token
        # Raises
            `hopsworks.client.exceptions.RestAPIError`: If the backend encounters an error when handling the request
        """

        _client = client.get_instance()
        path_params = ["elastic", "jwt", _client._project_id]

        headers = {"content-type": "application/json"}
        return _client._send_request("GET", path_params, headers=headers)["token"]
