# Introduction

antAPI is a simple REST api for RPC to ANT systems.
It can be deployed standalone or using apache and
protected by JSON Web Tokens (JWT).

# Deployment

To deploy the application at `/some/location`:

```
   mkdir /some/location
   rsync -av thisdir/ /some/location/
   cd /some/location
```

First, create a virtual environment:

```
   python3 -m venv venv
```

Next fetch all required packages:

```
   venv/bin/pip install -r requirements.txt
```

At this point, you should be able to run the package:

```
   venv/bin/python run.py
```

This step integrates it with apache using wsgi module (install separately): edit
the `wsgi.py` file and update current install path. Also edit apache config `antAPI.conf`
to update paths and place it under `/etc/httpd/conf.d`.  Restart httpd/apache.

Create and initialize the database and add an admin-realm user (who can create other users):

```
  ./dbinit.py
```

Answer prompts and hit return.

Finally, change `SECRET_KEY` in `app/flask_conf.py` to something random with enough entropy.
 

Throught the rest of this document, we assume that the application is started in the debug mode
by running:

```
   venv/bin/python run.py
```

and therefore is accessible at `http://localhost:5000`.  In production the application will be
deployed over HTTPS and the URL will be `https://hostname/path/to/app` and all our example URLs
will be relative to that.  E.g. example debug URL `http://localhost:5000/user/auth` will be
accessible as `https://hostname/path/to/app/user/auth`.


# Authentication of users and submitting requests

All requests are done in two steps:

1. Authenticate to the system using email, realm, and a password.  If authenticated, the system
   replies with a token that can be used in step 2.

2. Use the token from the previous step to submit a request.  The token can be used for one hour
   and can submit as many requests as you like but only to the realm you authenticated to.

Authentication is done by submitting a POST request to /user/auth with form
fields email, realm, and pword required:

```
   curl -X POST http://localhost:5000/user/auth -F email=xxx@isi.edu -F realm=xxx -F pword=xxx
```

returns with status 201 and JSON:

```
   {"message":"OK","token":"eyJh"}
```

The JSON response, if successful (201), contains "token" field which can be used for a 
certain time period (currently set to 1 hour) to make requests for the given realm.

# TRAC endpoints

With this api you can create new tickets and add attachments to them.
To access any endpoint, authenticate first using email and password as described above
and obtain the JSON token.

## Creating new tickets

Use the access token (by default, valid for 1 hour) to create tickets:

```
   curl -X POST http://localhost:5000/trac/ticket/new \
        -H 'x-access-token: eyJh...'
        -F description='this request is covering
   several lines of text.  Can be as long as needed.
   ...' \
        -F researcher='firstname lastname' \
        -F email=xxx@isi.edu \
        -F affiliation='USC/ISI'
        -F datasets='Anycast_Enumeration_from_Netalyzr_to_Roots-20111130 Anycast_Enumeration_from_PlanetLab_to_TLDns-20120402'
```

returns with status 201 and JSON:

```
   {"message":"OK","ticket_id":"1234"}
```

where "1234" is the id of the newly created ticket in the trac system.


## Adding attachments to existing tickets

Similarly, you can use the access token to add attachments:

```
   curl -X POST http://localhost:5000/trac/ticket/1234/attach \
        -H 'x-access-token: eyJh...'
        -F dua_file.pdf=@/path/to/dua_file.pdf
        -F ssh_key.pub=@/path/to/ssh_key.pub

   { "message": "OK" }
```
 
## Getting status of existing tickets

Use the access token to inquire about the status of the `ticket_id` you've created:

```
    curl -X GET http://localhost:5000/trac/ticket/1234/status \
        -H 'x-access-token: eyJh...'
```

Successful query returns with status 201 and JSON containing "status" field:
```
    { "message": "OK", "status": "released" } or
    { "message": "OK", "status": "new" }
```

On error, 401 is returned with an error message:
```
    {
        "message": "ERROR cannot obtain ticket status: exception -  Ticket 13099 does not exist."
    }
```


# Administration

Administration is done by users who have access to `admin` realm.  At present it's limited to
just user control (adding, deleting, or listing current users).
First, the admin must authenticate:

```
   curl -X POST http://localhost:5000/user/auth -F realm=admin -F email=... -F pword=...
   {"message":"OK","token":"eyJhb..."}
```

and then, use the provided token to add/delete users:

Adding:

```
   curl -X POST http://localhost:5000/user/add -F uname='test user' -F email=xxx@yyy.zzz -F realm=test -F pword=xxx \
        -H 'x-access-token: eyJhb...'
```

Deleting:

```
   curl -X POST http://localhost:5000/user/del -F uname='test user' -F email=xxx@yyy.zzz -F realm=test -F pword=xxx \
        -H 'x-access-token: eyJhb...'
```

Listing:

```
   curl -X POST http://localhost:5000/user/list \
        -H 'x-access-token: eyJhb...'
   => {"message":"OK","users":[{"email":"xxx@isi.edu","realm":"admin"},{"email":"yyy@ant.isi.edu","realm":"trac"},{"email":"zzz@ant.isi.edu","realm":"trac"}]}
```

