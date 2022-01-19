# encoding: utf-8
from time import time

start = time()
from mo_logs import logger
end = time()

print(f"import time = {str(round(end-start, 2))} seconds")

logger.info("this is a simple test")