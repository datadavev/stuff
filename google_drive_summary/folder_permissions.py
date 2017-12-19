'''
Script to generate Sphinx .rst documents providing a summary of a Google
Drive folder hierarchy.

The output is from the perspective of the account that is authenticated to
Google Drive, and so will not show any entries that are not in the user's path
or does not have permission to view.

Similarly, the output may show content that others do not have permission to 
view, and so care should be taken when presenting the results if sensitive 
content is in the folder hierarchy.

This script should be run from the top level folder of the Sphinx document
hierarchy (i.e. where the Makefile is located)
'''

from __future__ import print_function
import httplib2
import os
import sys
import logging 
import datetime
import codecs

from apiclient import discovery
from apiclient import errors
import oauth2client
from oauth2client import client
from oauth2client import tools

from operator import itemgetter

# ${HOME}/.dataone/gdrive
CLIENT_AUTH_CONFIG = os.path.join('.dataone', 'gdrive')
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive Permssions Summary'
MAXIMUM_DEPTH = 3

SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'

# Execute this script when in the top level folder of the Sphinx docment 
# hierarchy (i.e., where the Makefile is)
OUTPUT = "source/generated"

FOLDER_MIME = 'application/vnd.google-apps.folder'


def mimeToHuman(mimeType):
  ''' Get a friendly label for a mimeType.

  Given a Google Drive mimeType, try and return a friendly label. The mapping 
  list is not exhaustive.

  Returns:
    Label for mimeType
  '''
  mapping = {
  FOLDER_MIME: 'Folder',
  'application/vnd.google-apps.spreadsheet': 'Google Sheet',
  'application/vnd.google-apps.document': 'Google Doc',
  'application/vnd.openxmlformats-officedocument': 'Word',
  'application/vnd.google-apps.drawing': 'Google Drawing',
  'application/pdf':'PDF',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation':
    'Powerpoint',
  'application/vnd.google-apps.presentation':'Google Presentation',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 
    'Word',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'Excel',
  }
  try:
    return mapping[mimeType]
  except:
    pass
  return mimeType


def getCredentials():
  """Gets valid user credentials from storage.

  If nothing has been stored, or if the stored credentials are invalid,
  the OAuth2 flow is completed to obtain the new credentials.

  Returns:
      Credentials, the obtained credential.
  """
  home_dir = os.path.expanduser('~')
  credential_dir = os.path.join(home_dir, CLIENT_AUTH_CONFIG)
  if not os.path.exists(credential_dir):
    os.makedirs(credential_dir)
  credential_path = os.path.join(credential_dir,
                                 'drive-credentials.json')

  store = oauth2client.file.Storage(credential_path)
  credentials = store.get()
  if not credentials or credentials.invalid:
    sfile = os.path.join(home_dir, CLIENT_AUTH_CONFIG, CLIENT_SECRET_FILE)
    flow = client.flow_from_clientsecrets(sfile, SCOPES)
    flow.user_agent = APPLICATION_NAME
    if flags:
      credentials = tools.run_flow(flow, store, flags)
    else: # Needed only for compatability with Python 2.6
      credentials = tools.run(flow, store)
    print('Storing credentials to ' + credential_path)
  return credentials


def retrievePermissions(service, file_id):
  """Retrieve a list of permissions.

  Args:
    service: Drive API service instance.
    file_id: ID of the file or folder to retrieve permissions for.
  Returns:
    List of permissions.
  """
  try:
    permissions = service.permissions().list(fileId=file_id).execute()
    return permissions.get('items', [])
  except errors.HttpError as e:
    logging.exception(e)
  return None


def showFolderPermissions(service, fid, fdest=sys.stdout):
  """Print a list-table fragment with permissions for a file or folder.

  Args:
    service: Drive API service instance.
    fid: ID of the file or folder to retrieve permissions for.
    fdest: File object open for writing that will receive the output.
  """
  perms = retrievePermissions(service, fid)
  for perm in perms:
    try:
      n = perm['name']
    except KeyError:
      perm['name'] = "n/a"
    try:
      n = perm['emailAddress']
    except KeyError:
      perm['emailAddress'] = "n/a"
  #sort on Name
  sperms = sorted(perms, key=itemgetter('name'))
  for perm in sperms:
    role = perm['role']
    name = perm['name']
    if perm['type'] == 'group':
      name = "{0} (Group)".format(name)
    elif perm['type'] == 'domain':
      name = "{0} (Domain)".format(name)
    elif perm['type'] == 'Anyone':
      name = "Anyone (public)"

    email = perm['emailAddress']
    fdest.write(u"   * - {0}\n".format(role))
    try:
      fdest.write(u"     - .. image:: {0}\n".format(perm['photoLink']))
    except KeyError:
      fdest.write(u"     - \n")
    fdest.write(u"     - {0}\n".format(name))
    fdest.write(u"     - {0}\n".format(email))
  return


def getFileMetadata(service, file_id):
  """Return metadata for a Drive file or folder.

  Args:
    service: Drive API service instance.
    file_id: ID of the file to print metadata for.
  """
  try:
    meta = service.files().get(fileId=file_id).execute()
    return meta
  except errors.HttpError as e:
    logging.exception(e)
  return None


def printFolderInformation(service, folder_id, parents=[], fdest=sys.stdout):
  '''Output restructured text section describing a folder.

  Outputs a restructured text section for Sphinx that describes a folder,
  the permissions associated with it (i.e. shares), and its contents. 

  Args:
    service: Drive API service instance.
    folder_id: The folder to report on.
    parents: List of folder names that are the parents of folder_id.
    fdest: File object open for writing that will receive the output.
  '''
  # underline chars for heading. The heading level depends on the number of 
  # entries in parents[]
  ul = ["-", "~", "+", ".", ","]
  meta = getFileMetadata(service, folder_id)
  title = u" / ".join(parents + [meta['title']])
  uline = len(title)*ul[len(parents)]

  print(title)
  
  fdest.write("{0}\n{1}\n\n".format(title, uline))
  
  label = meta['title']
  if len(parents) > 0:
    label = " / ".join(parents + [meta['title']] )
  fdest.write(u":Path: `{0} <{1}>`_\n\n".format(label, meta['alternateLink']))
  fdest.write("""

**Permissions**

.. list-table::
   :header-rows: 1
   :widths: 10 10 40 50

   * - Permission
     - 
     - Name
     - Email
""")
  showFolderPermissions(service, folder_id, fdest=fdest)
  fdest.write("""
**Folder Contents**

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Kind
     - Name
""")
  return meta['title']


def printFilesInFolder(service, 
                       folder_id, 
                       depth=2, 
                       parents=[], 
                       fdest=sys.stdout, 
                       is_root=False):
  """Print files belonging to a folder.

  Args:
    service: Drive API service instance.
    folder_id: ID of the folder to print files from.
  """
  fname = printFolderInformation(service, folder_id, parents, fdest=fdest)
  if not is_root:
    parents.append(fname)
  else:
    parents.append(".")
  page_token = None
  content_meta = []
  folder_meta = []
  while True:
    try:
      param = {}
      if page_token:
        param['pageToken'] = page_token
      children = service.children().list(
        folderId=folder_id, **param).execute()

      for child in children.get('items', []):
        meta = getFileMetadata(service, child['id'])
        if meta['mimeType'] == FOLDER_MIME:
          folder_meta.append(meta)
        else:
          content_meta.append(meta)
      page_token = children.get('nextPageToken')
      if not page_token:
        break
    except errors.HttpError as error:
      print('An error occurred: %s' % error)
      break
  #`Link text <http://example.com/>`_ 
  for meta in content_meta:
    fdest.write(u"   * - .. image:: {0}\n".format(meta['iconLink']))
    fdest.write(u"          :target: {0}\n".format(meta['alternateLink'] ))
    fdest.write(u"          :alt: {0}\n".format(mimeToHuman(meta['mimeType'])))
    fdest.write(u"     - :index:`{0}`\n".format(meta['title'].strip()))
  for meta in folder_meta:
    fdest.write(u"   * - .. image:: {0}\n".format(meta['iconLink']))
    fdest.write(u"          :target: {0}\n".format(meta['alternateLink'] ))
    fdest.write(u"          :alt: {0}\n".format(mimeToHuman(meta['mimeType'])))
    fdest.write(u"     - :index:`{0}`\n".format(meta['title'].strip()))
  if len(content_meta) == 0 and len(folder_meta) == 0:
    fdest.write("   * - No files.\n     - .")
  fdest.write("\n\n")
  fdest.write("----\n\n")
  for meta in folder_meta:
    if depth > 0:
      # Recurse into subfolder if maximum depth not reached
      printFilesInFolder(service, meta['id'], 
                         depth=depth-1,
                         parents=parents,
                         fdest=fdest)
  if len(parents) > 0:
    parents.pop()


def listAllContent(service, 
                   folder_id, 
                   depth=2, 
                   parents=[], 
                   fdest=sys.stdout, 
                   is_root=False):
  '''
  '''
  page_token = None
  content_meta = []
  folder_meta = []
  folder_path = " / ".join(parents)
  while True:
    try:
      param = {}
      if page_token:
        param['pageToken'] = page_token
      children = service.children().list(
        folderId=folder_id, **param).execute()

      for child in children.get('items', []):
        meta = getFileMetadata(service, child['id'])
        fdest.write(u"   * - .. image:: {0}\n".format(meta['iconLink']))
        fdest.write(u"          :target: {0}\n".format(meta['alternateLink'] ))
        fdest.write(u"          :alt: {0}\n".format(mimeToHuman(meta['mimeType'])))
        if meta['mimeType'] == FOLDER_MIME:
          fdest.write(u"     - {1} / {0}\n".format(meta['title'].strip(), folder_path))
        else:
          fdest.write(u"     - {1} / **{0}**\n".format(meta['title'].strip(), folder_path))
        if meta['mimeType'] == FOLDER_MIME:
          if depth > 0:
            # Recurse into subfolder if maximum depth not reached
            parents.append(meta['title'])
            listAllContent(service, meta['id'], 
                           depth=depth-1,
                           parents=parents,
                           fdest=fdest)
            parents.pop()
      page_token = children.get('nextPageToken')
      if not page_token:
        break
    except errors.HttpError as error:
      print('An error occurred: %s' % error)
      break


def generateContentIndex(service, folder_id, depth=2, fname=None):
  fdest = None
  if fname is None:
    fdest = sys.stdout
  else:
    fdest = codecs.open(fname, "w", "utf-8")
  tstamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00")
  fdest.write("""
.. Content is autogenerated. Edits will be lost!

List of Everything
==================

:Generated: {0}
:Max Depth: {1}

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Kind
     - Path
""".format(tstamp, depth+1))
  listAllContent(service, folder_id, depth=depth, fdest=fdest, is_root=True)
  fdest.write("\n\n")
  if fname is not None:
    fdest.close()


def generateFolderSumaries(service, fid, depth=2, fname=None):
  fdest = None
  if fname is None:
    fdest = sys.stdout
  else:
    fdest = codecs.open(fname, "w", "utf-8")
  tstamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00")
  fdest.write(""".. Generated file. Edits will be lost!

Google Drive Folder Contents - DataONE Phase2
=============================================

:Generated: {0}
:Max Depth: {1}

.. contents::


""".format(tstamp, max_depth))
  printFilesInFolder(service, fid, depth=depth-1, fdest=fdest, is_root=True)
  fdest.write(".")
  if fname is not None:
    fdest.close()


# ==============================================================================
if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
  except ImportError:
    flags = None

  credentials = getCredentials()
  http = credentials.authorize(httplib2.Http())

  service = discovery.build('drive', 'v2', http=http)
  # The folder ID for the starting point of content traversal.
  fid = "0BztxcZtKztA5MkhCOW1vOXpqU1k"

  max_depth = MAXIMUM_DEPTH
  fname = os.path.join(OUTPUT, "index.rst")
  generateFolderSumaries(service, fid, depth=max_depth, fname=fname)

  fname = os.path.join(OUTPUT, "all_files.rst")
  generateContentIndex(service, fid, depth=max_depth+2, fname=fname)
