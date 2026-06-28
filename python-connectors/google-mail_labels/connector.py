from dataiku.connector import Connector
from google_mail_client import GmailClient
from dku_common import get_token_from_config
import base64
import json


class GmailConnector(Connector):
    BATCH_SIZE = 20

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        access_token = get_token_from_config(config)
        self.client = GmailClient(access_token)
        self.after_date = self.config.get("after_date")
        self.before_date = self.config.get("before_date", None)
        self.search_query = self.config.get("search_query", "")
        self.search_has = self.config.get("search_has", [])
        self.search_from = self.config.get("search_from", "")
        self.search_to = self.config.get("search_to", "")
        self.max_results = self.config.get("max_results", -1)

    def get_read_schema(self):
        # In this example, we don't specify a schema here, so DSS will infer the schema
        # from the columns actually returned by the generate_rows method
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        effective_limit = self._get_effective_limit(records_limit)
        first_call = True
        while first_call or self.client.has_more_events():
            first_call = False
            message_refs = self.client.get_message_id(
                search_query=self.search_query,
                after_date=self.after_date,
                before_date=self.before_date,
                email_has=self.search_has,
                from_user=self.search_from,
                to_user=self.search_to,
                records_limit=effective_limit
            )
            message_ids = [message.get("id") for message in message_refs if message.get("id")]
            for offset in range(0, len(message_ids), self.BATCH_SIZE):
                messages = self.client.get_messages(message_ids[offset:offset + self.BATCH_SIZE], can_raise=False)
                for message in messages:
                    message["body_text"] = ""
                    message["body_html"] = ""
                    payload = message.pop("payload", {})
                    parts = payload.get("parts", [])
                    for part in parts:
                        mime_type = part.get("mimeType")
                        if mime_type == "text/plain":
                            message["body_text"] = decode_padded(part.get("body", {}).get("data", ""))
                        if mime_type == "text/html":
                            message["body_html"] = decode_padded(part.get("body", {}).get("data", ""))
                    yield message

    def _get_effective_limit(self, records_limit):
        dataset_limit = records_limit if records_limit and records_limit > 0 else -1
        config_limit = self.max_results if self.max_results and self.max_results > 0 else -1

        if dataset_limit > 0 and config_limit > 0:
            return min(dataset_limit, config_limit)
        if dataset_limit > 0:
            return dataset_limit
        return config_limit

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        """
        Returns a writer object to write in the dataset (or in a partition).

        The dataset_schema given here will match the the rows given to the writer below.

        Note: the writer is responsible for clearing the partition, if relevant.
        """
        raise NotImplementedError

    def get_partitioning(self):
        """
        Return the partitioning schema that the connector defines.
        """
        raise NotImplementedError

    def list_partitions(self, partitioning):
        """Return the list of partitions for the partitioning scheme
        passed as parameter"""
        return []

    def partition_exists(self, partitioning, partition_id):
        """Return whether the partition passed as parameter exists

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        """
        Returns the count of records for the dataset (or a partition).

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError


def decode_padded(payload):
    padded_payload = payload + "=" * (-len(payload) % 4)
    ret = ""
    try:
        decoded_payload = base64.urlsafe_b64decode(padded_payload.encode('utf-8'))
    except Exception:
        return ""
    if isinstance(decoded_payload, bytes):
        decoded_payload = decoded_payload.decode('utf-8')
    return decoded_payload
