# encoding: utf-8
from time import time

start = time()
from mo_logs import Log
end = time()

print(f"import time = {str(round(end-start, 2))} seconds")

Log.note("this is a simple test")