import logging
import math
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GmailService:
    def __init__(self, access_token: str):
        # Create credentials with token; note: without refresh_token, this will fail after expiry
        # For production, you should also pass refresh_token, token_uri, client_id, client_secret
        self.creds = Credentials(
            token=access_token,
            refresh_token=None,  # TODO: Pass refresh token from session
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,  # TODO: Pass from config
            client_secret=None,  # TODO: Pass from config
        )
        self.service = build('gmail', 'v1', credentials=self.creds)

    def fetch_recent_emails(self, max_results=20):
        try:
            inbox_limit = math.ceil(max_results / 2)
            spam_limit = max_results - inbox_limit

            # 1. Fetch INBOX messages
            results_inbox = self.service.users().messages().list(
                userId='me', 
                maxResults=inbox_limit,
                labelIds=['INBOX']
            ).execute()
            
            # 2. Fetch SPAM messages
            results_spam = self.service.users().messages().list(
                userId='me', 
                maxResults=spam_limit,
                labelIds=['SPAM']
            ).execute()
            
            messages_inbox = results_inbox.get('messages', [])
            messages_spam = results_spam.get('messages', [])
            all_messages = messages_inbox + messages_spam
            
            if not all_messages:
                return []

            email_data = []

            # Callback for batch processing
            def callback(request_id, response, exception):
                if exception:
                    logger.error(f"Error fetching message {request_id}: {exception}", exc_info=exception)
                    return
                
                headers = response['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                snippet = response.get('snippet', '')
                
                # Determine folder based on labelIds in response
                labels = response.get('labelIds', [])
                folder = 'Spam' if 'SPAM' in labels else 'Inbox'

                email_data.append({
                    "id": response['id'],
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "snippet": snippet,
                    "status": "Unscanned", # Actual scanning not implemented yet
                    "threat": "Marked as Spam by Google" if folder == 'Spam' else None,
                    "folder": folder
                })

            # 3. Create Batch Request
            batch = self.service.new_batch_http_request(callback=callback)
            
            for msg in all_messages:
                batch.add(self.service.users().messages().get(
                    userId='me', 
                    id=msg['id'], 
                    format='full'
                ))
            
            batch.execute()
            return email_data
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}", exc_info=True)
            raise  # Re-raise to let caller handle API errors
        except Exception as e:
            logger.exception(f"Unexpected error fetching emails: {e}")
            raise
