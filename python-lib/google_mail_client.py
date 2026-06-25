import logging
import datetime
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dku_common import dss_to_gmail_date
from dku_constants import DKUConstants as constants


SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='google-calendar plugin %(levelname)s - %(message)s')


class GmailClientError(ValueError):
    pass


class GmailClient():
    def __init__(self, token):
        credentials = Credentials(token, SCOPES)
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                raise GmailClientError("Credential not valid or need to be refreshed")
        self.service = build('gmail', 'v1', credentials=credentials)
        logger.info("Connection to Gmail ok")
        self.batched_messages = []
        self.next_page_token = None
        self.number_retrieved_events = 0

    def search_emails(self, from_date=None, to_date=None):
        return

    def get_message_id(self,
                       user_id="me",
                       after_date=None,
                       before_date=None,
                       email_has=[],
                       search_query="",
                       from_user="",
                       to_user="",
                       records_limit=constants.RECORDS_NO_LIMIT):
        queries = []
        kwargs = {
            "userId": user_id
        }
        if records_limit and records_limit > 0:
            kwargs["maxResults"] = records_limit
        if after_date:
            queries.append("after:{}".format(dss_to_gmail_date(after_date)))
        if before_date:
            queries.append("before:{}".format(dss_to_gmail_date(before_date)))
        if search_query:
            queries.append(search_query)
        for item in email_has:
            queries.append("has:{}".format(item))
        if from_user:
            queries.append("from:{}".format(from_user))
        if to_user:
            queries.append("to:{}".format(to_user))
        if queries:
            kwargs["q"] = self.build_search_query(queries)
        print("ALX:kwargs={}".format(kwargs))
        response = self.service.users().messages().list(**kwargs).execute()
        print("ALX:results={}".format(response))
        self.update_next_page_token(response, records_limit)
        messages = response.get('messages', [])
        self.number_retrieved_events += len(messages)
        return messages

    def get_message(self, message_id, can_raise=True):
        if message_id:
            messageheader = self.service.users().messages().get(userId="me", id=message_id, format="full", metadataHeaders=None).execute()
            return messageheader
        else:
            return {"api_error": "Null ID"}

    def get_messages_callback(self, request_id, response, exception):
        print("ALX:got callback {}".format(request_id))
        if exception is not None:
            self.batched_messages.append({"api_error": "{}".format(exception)})
        else:
            self.batched_messages.append(response)

    def get_messages(self, message_ids=[], can_raise=True):
        self.batched_messages = []
        batch = self.service.new_batch_http_request()
        for message_id in message_ids:
            batch.add(self.service.users().messages().get(userId="me", id=message_id, format="full", metadataHeaders=None), callback=self.get_messages_callback)
        print("ALX:before")
        batch.execute()
        print("ALX:after")
        return self.batched_messages

    def get_events(self, from_date, to_date=None, calendar_id="primary", records_limit=-1, can_raise=True):
        if from_date is None:
            from_date = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        kwargs = {
            "calendarId": calendar_id,
            "timeMin": from_date,
            "singleEvents": True,
            "orderBy": "startTime"
        }
        if to_date:
            kwargs["timeMax"] = to_date
        if records_limit > 0:
            kwargs["maxResults"] = records_limit

        try:
            events_result = self.service.events().list(
                **kwargs
            ).execute()
        except Exception as err:
            logging.error("Google Calendar client error : {}".format(err))
            if can_raise:
                raise GmailClientError("Error: {}".format(err))
            else:
                return [{"api_error": "{}".format(err)}]
        events = events_result.get('items', [])
        return events

    @staticmethod
    def build_search_query(queries):
        return " ".join(queries)

    def update_next_page_token(self, events_result, records_limit=constants.RECORDS_NO_LIMIT):
        if records_limit == constants.RECORDS_NO_LIMIT or self.number_retrieved_events < records_limit:
            self.next_page_token = events_result.get("nextPageToken")
        else:
            self.next_page_token = None

        if self.next_page_token:
            logging.info("More events available")

    def has_more_events(self):
        return self.next_page_token is not None
