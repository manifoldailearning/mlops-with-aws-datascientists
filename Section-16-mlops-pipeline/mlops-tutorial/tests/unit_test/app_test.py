import json
from urllib import request

base_url='http://localhost:8080'
headers={"Content-type": "text/csv"}

# Toy request payload: `str()`
payload = "6.550000000000000266e-01,5.200000000000000178e-01,1.900000000000000022e-01,\
1.454499999999999904e+00,5.999999999999999778e-01,3.865000000000000102e-01,\
3.829999999999999516e-01,1.000000000000000000e+00,0.000000000000000000e+00,0.000000000000000000e+00"

# Encode payload to Bytes for `request()
payload = payload.encode('utf-8')


def predict(payload, headers):
    """
    Description:
    -----------
    Prediction request to the local API.
    
    :payload: (Bytes) Bytes encoded string of `abalone` features for a single observation.
    :headers: (dict) Dictionary specifying the request content type.
    """
    req = request.Request("%s/invocations" % base_url, data=payload, headers=headers)
    resp = request.urlopen(req)
    print("API Response code: %d \nPrediction Response: %s" % (resp.getcode(), resp.read().decode('utf-8')))


def main():
    for x in range(1, 4):
        print("\nStarting Test {} ...".format(x))
        resp = request.urlopen("%s/ping" % base_url)
        print("\nPING Response code: %d" % resp.getcode())
        predict(payload, headers)


if __name__ == "__main__":
    main()