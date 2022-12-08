# Simple client-side python API for antAPI

1. Create a file (make sure you add it to .gitignore, so it doesn't get
   checked in) with client configuration:

```python
   antapi_client_conf.py:

   #(realm, email, password) should match those created for you
   #by the administrator
   AUTH = dict(
       email = 'me@example.com',
       password = 'xxxx',
       realm = 'trac',

       base_url = 'https://ant.isi.edu/antAPI',
   )
```

2. This is an example of how to create a trac ticket and add
   attachments to it

```python
   from antAPI.client.auth import AntAPIClientAuthenticator
   from antAPI.client.trac import (
       antapi_trac_ticket_new,
       antapi_trac_ticket_attach,
   )
   from antapi_client_conf import AUTH

   auth = AntAPIClientAuthenticator(**AUTH)

   ticket_fields = dict(
      description='description of the request',
      researcher='research first and last name',
      email='researcher email',
      affiliation='researcher affiliation',
      datasets='B-Root_Load-20170515 more space separated',
    )

   ticket_id = antapi_trac_ticket_new(auth, **ticket_fields)

   #add attachments
   antapi_trac_ticket_attach(auth, ticket_id, ['/path/to/file1', '/path/to/file2'])

   #...

   #if the token expires, it will be authomatically refreshed
   #but the refresh can be forced:
   auth.refresh()

   #continue creating tickets/adding attachments
```
