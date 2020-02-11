# py_tinfoil_gdrive_generator
Script that will allow you to easily generate a JSON file (with encrypted if needed) for use with Tinfoil.
This project is a based on [this project](https://github.com/BigBrainAFK/tinfoil_gdrive_generator/) by [BigBrainAFK](https://github.com/BigBrainAFK/). This script uses the crypto section for encrypting the resulting file from the previously mentioned project.

## Requirements

- Python 3
- Modules from `requirments.txt` found in the root of project directory.
- `credentials.json` (or any file name if using `--credentials` flag to pass custom location for the required credential file). It can be obtained from [here](https://developers.google.com/drive/api/v3/quickstart/python)  by clicking the `Enable Drive API` button in there while being signed in with the user account you want to generate credentials for or from Google's Developer Console.
- Google Drive Folder IDs to scan and index.

Execute the following command in a terminal to install all the required modules.
`pip3 install -r requirments.txt`

## Simple Usage

- `python3 py_tinfoil_gdrive_generator.py FOLDER_ID_TO_SCAN [...]`
Use the following command to update a `index.json` file (will make file from scratch if not found) to use for tinfoil with its new `gdrive:/` protocol with all the files in the folders of all the folder IDs passed.

## Advanced Usage

- `--share-files {update/all}`
Use this flag if you want to share the files that you are going to add to the index file.
Use `update` if you want to share files that will be newly added to the index file.
Use `all` if you want to share all the files in the folder IDs that will be passed.
By default, the script ***does not*** share files. If this flag is not passed or is passed without `update`/`all`, the files will not be shared.
- `--credentials /path/to/credentials.json`
Use this flag if you want to specify a custom location for the credentials to use.
By default, the script will look for a file named `credentials.json` in the working directory.
- `--token /path/to/token.json`
Use this flag if you want to specify a custom location for the token to use.  
By default, the script will look for a file named `token.json` in the working directory.
- `--output-json /path/to/index.json`
Use this flag if you want to specify a custom location for the output index file.  
By default, the script will look for a file named `index.json` in the working directory.
- `--encrypt-file /path/to/encrypted_index.json`
Use this flag if you want to encrypt the resulting index file to `/path/to/encrypted_index.json`.
By default, the script ***will not*** encrypt the resulting index file.
- `--public-key /path/to/public.key`
Use this flag if you want to specify a custom public key to encrypt with.  
By default, the script will look for a file named `public.json` in the working directory if `--encrypt-file` is used.
- `--disable-recursion`
Use this flag if you do not want the folder IDs passed to be recursively scanned.
- `--use-old-url-format`
Use this flag if you want to generate links using the old URL method.
## Credits
[BigBrainAFK](https://github.com/BigBrainAFK/) for Crypto Stuff.