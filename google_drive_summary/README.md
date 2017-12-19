# Google Drive Summary

Generates a static summary of Google Drive content and permissions.

## Installation

```
pip install -U google-api-python-client
pip install -U sphinx
```

## Running

Edit `folder_permissions.py`, setting the variable `fid` in the `__main__` section near the end of the file. `fid` should be set to the part of the Gogle Drive URL after the last slash in the URL. For example, given the folder URL:

```
https://drive.google.com/drive/u/0/folders/0By3ryhJR2IgZWmQtZE88DSVZRN2c
```

`fid` should be set to `0By3ryhJR2IgZWmQtZE88DSVZRN2c`

Also need to create a folder in $HOME called `.dataone/gdrive`

Also need to enable API access to your Google goodies, instructions are available from Google: 

  https://developers.google.com/api-client-library/python/start/get_started

Then run:

```
python folder_permissions.py
```

And after it is done (can take quite a while for a large folder structure):

```
make html
open build/html/index.html
```


