import threading
import time
import random


def printThing(s, count=10, delay=1):
    for i in range(0, count):
        print(f'{s}: {i}')
        time.sleep(1)

strings = ["James", "Aiden", "Mihai", "George"]
threads = []
print("begin multithreading!")
for s in strings:
    # args=(s, ) looks the way it does because it needs a comma to be considered a tuple, even if it only has a single value
    # args is for positional arguments, kw
    thread = threading.Thread(target=printThing, args=(s, ), kwargs={"count": random.randint(1, 10), "delay" : random.randint(1, 3)})
    threads.append(thread)
    thread.start()

for t in threads:
    thread.join()


