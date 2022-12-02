## Contents

This directory contains uploaded trac tickets. Its location
may be changed by modifying `TRAC_ATTACHMENT_DIR` in 
`app/flask_conf.py`

Each filename is constructed as:

```
   <ticket_id-formfield>
```

Thus, if the submission was:

```
   curl -X POST http://localhost:5000/trac/ticket/1234/attach \
        -H 'x-access-token: ey...'
        -F user_dua=@/tmp/DUA.txt -Fssh_key=@/tmp/my_ssh_key.pub
```

and it succeeds, there will be 2 files created:

```
  1234-DUA.txt
  1234-my_ssh_key.pub
```

Previously created files with same name are allowed to be 
overwritten.
