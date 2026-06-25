# -*- coding: utf-8 -*-
import dataiku
import pandas
import logging

from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
from google_mail_client import GmailClient
from dku_common import get_token_from_config


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='google-calendar plugin %(levelname)s - %(message)s')


logger.info("Google Calendar Plugin events recipe")
input_A_names = get_input_names_for_role('input_A_role')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

email_id_column = config.get("email_id_column", None)
if email_id_column is None:
    raise ValueError("The recipe needs a list of email IDs to retrieve. Please refer to the documentation.")
access_token = get_token_from_config(config)
logger.info("Retrieving Gmails using columns id '{}'".format(email_id_column))
client = GmailClient(access_token)
logger.info("Gmail client authenticated")

input_parameters_dataset = dataiku.Dataset(input_A_names[0])
print("ALX:1")
input_parameters_dataframe = input_parameters_dataset.get_dataframe(infer_with_pandas=False)
print("ALX:2")
lines_to_process = len(input_parameters_dataframe)
logger.info("{} line(s) to process".format(lines_to_process))

messages = []
batch = []
batch_size = 0
for index, input_parameters_row in input_parameters_dataframe.iterrows():
    print("ALX:index={}".format(index))
    email_id = input_parameters_row.get(email_id_column)
    batch.append(email_id)
    batch_size += 1
    if batch_size == 20 or index == lines_to_process - 1:
        print("ALX:batching")
        messages.extend(
            client.get_messages(batch, can_raise=False)
        )
        print("ALX:back from batch index={}, {}".format(index, lines_to_process))
        batch = []
        batch_size = 0

    # first_call = True
    # while first_call or client.has_more_events():
    #     first_call = False
    #     messages.append(
    #         client.get_message(email_id, can_raise=False)
    #     )

odf = pandas.DataFrame(messages)

if odf.size > 0:
    output_names_stats = get_output_names_for_role('api_output')
    api_output = dataiku.Dataset(output_names_stats[0])
    api_output.write_with_schema(odf)
