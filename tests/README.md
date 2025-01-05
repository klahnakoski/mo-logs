# mo-logs - Testing


## Running Tests

```
python -m pip install -r tests/requirements.txt
python -m pip install -r requirements.txt
python -m unittest discover .
```


## Coverage

```
python -m pip install coverage
python -m coverage run -m unittest discover .
python -m coverage html --omit="tests/"
```