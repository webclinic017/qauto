import asyncio
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


def thr(i):
    # we need to create a new loop for the thread, and set it as the 'default'
    # loop that will be returned by calls to asyncio.get_event_loop() from this
    # thread.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ret = loop.run_until_complete(do_stuff(i))
    loop.close()
    return ret


async def do_stuff(i):
    ran = random.uniform(0.1, 0.5)
    await asyncio.sleep(ran)  # NOTE if we hadn't called
    # asyncio.set_event_loop() earlier, we would have to pass an event
    # loop to this function explicitly.
    print(i, ran)
    return ran


def main():
    num_threads = 10
    with ThreadPoolExecutor(num_threads) as executor:
        futures = {}
        for i in range(num_threads):
            future = executor.submit(thr, i)
            futures[future] = i
        for future in as_completed(futures):
            ret = future.result()
            print(ret, futures[future])


if __name__ == "__main__":
    main()
