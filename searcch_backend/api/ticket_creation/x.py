from antAPI.client.auth import AntAPIClientAuthenticator
from antAPI.client.trac import (
   antapi_trac_ticket_status,
)
from antapi_client_conf import AUTH

auth = AntAPIClientAuthenticator(**AUTH)

ticket_id = '10000'
# check the status:
ticket_status = antapi_trac_ticket_status(auth, ticket_id)
print(ticket_status)
if ticket_status != 'released':
   print("Your dataset request is under consideration")
else:
   print("Your dataset request has been approved and released (check your mailbox)")
