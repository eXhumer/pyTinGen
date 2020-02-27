# py_tinfoil_gdrive_generator
Script that will allow you to easily generate a JSON file (with encrypted if needed) for use with Tinfoil.
This project is a based on [this project](https://github.com/BigBrainAFK/tinfoil_gdrive_generator/) by [BigBrainAFK](https://github.com/BigBrainAFK/). This script uses the crypto section for encrypting the resulting file from the previously mentioned project.

## Requirements

- Python 3
- Modules from `requirements.txt` found in the root of project directory.
- `credentials.json` (or any file name if using `--credentials` flag to pass custom location for the required credential file). It can be obtained from [here](https://developers.google.com/drive/api/v3/quickstart/python)  by clicking the `Enable Drive API` button in there while being signed in with the user account you want to generate credentials for or from Google's Developer Console.
- Google Drive Folder IDs to scan and index.

Execute the following command in a terminal to install all the required modules.
`pip3 install -r requirements.txt`

## Usage
```
usage: py_tinfoil_gdrive_generator.py [-h] [--share-files [{update,all}]]
                                      [--credentials CREDENTIALS_FILE_NAME] [--token TOKEN_FILE_PATH]
                                      [--index-file INDEX_FILE_PATH] [--encrypt [ENC_INDEX_FILE_PATH]]
                                      [--public-key PUBLIC_KEY_FILE_PATH] [--disable-recursion]
                                      [--success SUCCESS_MESSAGE]
                                      [FOLDER_ID_TO_SCAN [FOLDER_ID_TO_SCAN ...]]

Script that will allow you to easily generate a JSON file with Google Drive file links for use with
Tinfoil.

positional arguments:
  FOLDER_ID_TO_SCAN     Folder ID of Google Drive folders to scan. Can use more than 1 folder IDs at a
                        time.

optional arguments:
  -h, --help            show this help message and exit
  --share-files [{update,all}]
                        Use this flag if you want to share files that gets newly added to your index
                        file. If you want to share files that was already added to your old index file,
                        use "--share-files all"
  --credentials CREDENTIALS_FILE_NAME
                        Obtainable from https://developers.google.com/drive/api/v3/quickstart/python.
                        Make sure to select the correct account before downloading the credentails file.
  --token TOKEN_FILE_PATH
                        File Path of a Google Token file.
  --index-file INDEX_FILE_PATH
                        File Path for unencrypted index file to update.
  --encrypt [ENC_INDEX_FILE_PATH]
                        Use this flag is you want to encrypt the resulting index file.
  --public-key PUBLIC_KEY_FILE_PATH
                        File Path for Public Key to encrypt with.
  --disable-recursion   Use this flag to stop folder IDs entered from being recusively scanned. (It
                        basically means if you use this flag, the script will only add the files at the
                        root of each folder ID passed, without going through the sub-folders in it.
  --success SUCCESS_MESSAGE
                        Success Message to add to index.
```

## Credits
[BigBrainAFK](https://github.com/BigBrainAFK/) for Crypto Stuff.