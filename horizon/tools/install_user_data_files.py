#!/usr/bin/env python

import os
from horizon.utils import userdata

def main():
    base_dir = userdata.UserDataScriptHelper.base_dir
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    for filename, context in userdata.user_data_file_context_dicts.items():
        file_path = '/'.join((base_dir, filename)) 
        try:
            with open(file_path, 'wb') as file:
                file.write(context)
        except Exception:
            pass

if __name__ == '__main__':
    main()