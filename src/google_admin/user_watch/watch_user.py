from google.oauth2 import service_account
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1
from googleapiclient.discovery import build
from dotenv import load_dotenv
from src.google_admin.auth import GoogleAdmin
from uuid import uuid4
import os,json, base64

load_dotenv()

class PubSub:

    '''
        links 
            --> https://developers.google.com/admin-sdk/reports/v1/guides/push#creating-notification-channels
            --> https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/watch
    '''

    def __init__(self):
        project_id = os.getenv('project_id')
        subscription_id = os.getenv('subscription_id')
        service_account_file_path = os.getenv('creds')

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file_path)
        self.service = build('pubsub', 'v1', credentials=credentials)
        self.timeout = 5.0
        self.subscriber = pubsub_v1.SubscriberClient()

        # The `subscription_path` method creates a fully qualified identifier
        # in the form `projects/{project_id}/subscriptions/{subscription_id}`
        self.subscription_path = self.subscriber.subscription_path(project_id, subscription_id)



    def callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        print(f"Received {message}.")
        message.ack()

# using python api client
    def pullMessage(self):
        service = self.service
        body = {"maxMessages" : '10',}
       
        try :
            # TODO do not retain acked messages
            subscriber = service.projects().subscriptions()

            pull_message = subscriber.pull(subscription = self.subscription_path, body=body).execute()
            print(f"Listening for messages on {self.subscription_path}..\n")


            for rcvd_msg in pull_message["receivedMessages"]:
                message = rcvd_msg['message']['data']
                print(f"Received message: {base64.b64decode(message).decode('utf-8')}")

                # ack the received messages 
                subscriber.acknowledge(subscription = self.subscription_path, body  = {"ackIds": [rcvd_msg['ackId']]}).execute()
        except Exception as err:
            print(err)

    def pullCloud(self):
        subscriber = self.subscriber
        subscription_path = self.subscription_path
        response = subscriber.pull({"subscription":  subscription_path, "max_messages":5})  # Adjust max_messages as needed

        for received_message in response.received_messages:
            # Process the received message
            message_data = received_message.message.data.decode('utf-8')
            print(f"Received message: {message_data}")

            # Acknowledge the message to mark it as processed
            # subscriber.acknowledge(subscription_path, [received_message.ack_id])

    def pullFuture(self):
        subscriber = self.subscriber
        subscription_path = self.subscription_path
        streaming_pull_future = subscriber.subscribe(subscription_path, callback=self.callback)

        print(f"Listening for messages on {self.subscription_path}..\n")
        # Block until the user interrupts the program
        with subscriber:

            try:
                streaming_pull_future.result(timeout= self.timeout)
            except TimeoutError:
                streaming_pull_future.cancel()
                streaming_pull_future.result()
            except KeyboardInterrupt:
                streaming_pull_future.cancel()
            except Exception:
                streaming_pull_future.cancel()
        


class UserWatch:

    def __init__(self):
        service_account_file_path = os.getenv('creds')
        self.topic = os.getenv('topic')
        self.customer = os.getenv('customerId')
        self.delegate = os.getenv('delegated_admin')
        self.watchPath = os.getenv('watchPath')

        self.SCOPES = [
            'https://www.googleapis.com/auth/admin.reports.audit.readonly']
        
        # TODO don't use delegated admin, enable the API in the project and give the credential account access
        # to the api and permission needed to carry out the tasks

        self.credentials = service_account.Credentials.from_service_account_file(
            service_account_file_path, scopes=self.SCOPES,subject=self.delegate)
        self.service = build('admin', 'reports_v1', credentials=self.credentials)

        # gadmin = GoogleAdmin(service_account_file_path,customer)
        # return gadmin

    '''
    Should onl be called once
    '''
    def register_watch(self):
        uuid = str(uuid4())
        # gadmin = GoogleAdmin()

        #watching through reports API instead of directory.users.watch

        try:
            address = "https://pubsub.googleapis.com/v1/{}:publish".format(self.topic)
            response = self.service.activities().watch(
                userKey = "all",
                applicationName = "admin",
                eventName = 'CREATE_USER',
                customerId = self.customer,
                startTime = "2024-03-08T23:32:35Z", #change to current time minus 5 mins
                body = {
                    "id": uuid,
                    "type": "web_hook",
                    "address": address
                }
            ).execute()

            try:
                with open(self.watchPath,'w') as watch:
                    watch.write(json.dumps(response))
            except Exception as error:
                print (error)
                print(response)

            # print(json.dumps(response))
            print(response)
                  
        except Exception as err:
            print(err)
            raise err
        
    def remove_watch(self):
        
        try:
            with open(self.watchPath,'r') as watch:
                info = json.load(watch)
            
            response = self.service.channels().stop(
                body= {
                    "id":info['id'],
                    "resourceId": info['resourceId'],
                    "kind": "api#channel"
                }
            ).execute()

            #clear the file
            open(self.watchPath, 'w').close()

            print(response)
        except Exception as err:
            print (err)
            raise err


if __name__ == '__main__':
    service_account_file_path = os.getenv('creds')
    # Wrap subscriber in a 'with' block to automatically call close() when done.
    subclient = PubSub()
    # subclient.pullMessage()
    # subclient.pullCloud()
    subclient.pullFuture()

    # reg = UserWatch()
    # reg.register_watch()
    # reg.remove_watch()



    