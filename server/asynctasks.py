import asyncio
from threading import Thread
from collections import deque
import random
import time


class AsyncTasks:

    def __init__(self, func=None, tasks=[], *args, **kw):
        self.func = func
        self.tasks = deque()
        self.args = args
        self.kw = kw
        if tasks:
            for task in tasks:
                self.tasks.appendleft(task)
        self.new_loop = asyncio.new_event_loop()
        loop_thread = Thread(target=self.start_thread_loop,
                             args=(self.new_loop,))
        # loop_thread.setDaemon(True)
        loop_thread.start()

        consumer_thread = Thread(target=self.consumer)
        consumer_thread.setDaemon(True)
        consumer_thread.start()

    def start_thread_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def consumer(self):
        while True:
            if not self.tasks:
                continue
            task = self.tasks.pop()
            print(task)
            if not task:
                continue
            print(self.func, self.args, self.kw)
            asyncio.run_coroutine_threadsafe(
                self.func(task, *self.args, **self.kw),
                self.new_loop
            )


async def hello(task, name):
    print('正在执行name:', task, name)
    await asyncio.sleep(2)
    return '返回结果：' + task + name

if __name__ == "__main__":
    name = 'august'
    t = AsyncTasks(func=hello, tasks=range(20, 30), name=name)
    # i = random.randint(1, 10)
    # t.tasks.appendleft(str(i))
    # time.sleep(0.25)
