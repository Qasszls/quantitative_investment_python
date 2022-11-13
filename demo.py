import hashlib
from multiprocessing import Pool
from timeit import default_timer as timer
from events.engine import EventEngine, Event


def js_hash(e: EventEngine):
    print(e)
    count = 0
    while count <= 99991929:
        count += 1
    event = Event('event', '完事了')
    e.put(event)


def listen(event):
    print(event.data)


if __name__ == '__main__':
    p = Pool(5)  # 创建一个进程池，最大进程数5
    start_time = timer()
    for i in range(0, 2):
        # apply_async(要调用的目标,args=(传递的参数,))
        p.apply_async(js_hash, args=(i,))
    p.close()  # 关闭进程池，关闭后进程池不再接受新的请求
    p.join()  # 等待所有子进程执行完毕，必须放在close语句后
    end_time = timer()
    print(end_time-start_time)
