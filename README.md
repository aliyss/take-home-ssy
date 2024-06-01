# take-home-ssy


## Overview
Create a simple API service that takes any python script as input and returns the result of the script execution as output. The service should be a simple docker image exposing port 8080. The service should execute the python script and return the result of the function main(). If the file does not contain a function main() and does not return a JSON, an error must be thrown.


## Usage

### Setup (Docker)
```bash
docker build -t take-home .
```

### Run (Docker)
```bash
docker run --priveleged -p 8080:8080 take-home
```

### Open Browser
Don't forget to add the `https` prefix.
[https://127.0.0.1:8080/](https://127.0.0.1:8080/)


## Other

### Test unallowed imports
Uncomment `scipy` in `requirements-nsjail.txt` and rebuild the image
