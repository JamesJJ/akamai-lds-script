# Bulk configure Akamai LDS

 - Supports different (S)FTP destination directories per CP-Code by using `${tag}` in your config file.

## Get started

1] Create a `.edgerc` file in your home directory:
   https://developer.akamai.com/legacy/introduction/Conf_Client.html

2] Run `./lds_script.py` and read the usage info.

Further details about the content of the config file can be found here:
https://developer.akamai.com/api/core_features/log_delivery_service/v3.html

(the config file is the request body to create/update Log Configuration APIs, templated)

## Known issues

1] Ensure your `edgegrid-python` is at least version 1.1.1 (previous versions had some bugs):

```
   pip install --upgrade edgegrid-python
```



