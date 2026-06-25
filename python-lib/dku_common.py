import pandas
import datetime


def get_token_from_config(config):
    oauth_credentials = config.get("oauth_credentials")
    if not oauth_credentials:
        raise ValueError("OAuth credential not present. Please refer to the plugin's documentation.")
    access_token = oauth_credentials.get("access_token")
    if not access_token:
        raise ValueError("No access token. Please validate the Google Calendar preset in your profile's credentials list. ")
    if isinstance(access_token, dict):
        raise ValueError("The 'Manually defined' option cannot be used for Single Sign On authentication. Please create a preset in the plugin's settings, then validate it in your profile's credentials list.")
    return access_token


def get_iso_format(panda_date):
    if pandas.isnull(panda_date):
        return None
    return panda_date.isoformat() + "Z"


def dss_to_gmail_date(date):
    return datetime.datetime.strftime(datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ"), "%Y/%m/%d")