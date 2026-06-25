from dataiku.connector import Connector
from google_mail_client import GmailClient
from dku_common import get_token_from_config
import datetime


class GmailConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)
        access_token = get_token_from_config(config)
        self.client = GmailClient(access_token)
        self.after_date = self.config.get("after_date")
        self.before_date = self.config.get("before_date", None)
        self.search_query = self.config.get("search_query", "")
        self.raw_results = self.config.get("raw_results", False)
        self.search_has = self.config.get("search_has", [])
        self.search_from = self.config.get("search_from", "")
        self.search_to = self.config.get("search_to", "")
        print("ALX:search_has={}".format(self.search_has))

    def get_read_schema(self):
        # In this example, we don't specify a schema here, so DSS will infer the schema
        # from the columns actually returned by the generate_rows method
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        first_call = True
        while first_call or self.client.has_more_events():
            first_call = False
            messages = self.client.get_message_id(
                search_query=self.search_query,
                after_date=self.after_date,
                before_date=self.before_date,
                email_has=self.search_has,
                from_user=self.search_from,
                to_user=self.search_to,
                records_limit=records_limit
            )
            if self.raw_results:
                for message in messages:
                    yield {"api_output": message}
            else:
                for message in messages:
                    yield message

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
