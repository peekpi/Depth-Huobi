from multiprocessing.dummy import Pool
import time

def tr(n):
    time.sleep(n)


l = [1 for i in range(22)]
pool = Pool(len(l))
pool.map(tr, l)
pool.close()
pool.join()
