# utils/google_ads.py
import pandas as pd
import os
from google.ads.googleads.client import GoogleAdsClient as AdsClient
from google.ads.googleads.errors import GoogleAdsException

def get_ad_groups_cost(client, customer_id, start_date, end_date):
    service = client.get_service("GoogleAdsService")
    
    # start_date y end_date ya vienen como string: 'YYYY-MM-DD'
    query = f"""
        SELECT
            ad_group.id,
            ad_group.name,
            metrics.cost_micros
        FROM ad_group
        WHERE segments.date >= '{start_date}'
          AND segments.date <= '{end_date}'
    """

    response = service.search_stream(customer_id=customer_id, query=query)
    rows = []

    for batch in response:
        for row in batch.results:
            rows.append({
                "Ad Group ID": str(row.ad_group.id),
                "Cost (in currency units)": row.metrics.cost_micros / 1_000_000
            })

    return pd.DataFrame(rows)

class GoogleAdsClient:
    @staticmethod
    def load_from_env(version="v18"):
        config = {
            "developer_token": os.getenv("GOOGLE_DEVELOPER_TOKEN"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            "login_customer_id": os.getenv("GOOGLE_LOGIN_CUSTOMER_ID"),
            "use_proto_plus": True
        }
        return AdsClient.load_from_dict(config, version=version)
