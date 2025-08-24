# cython: boundscheck=False, wraparound=False, cdivision=True, language_level=3
import numpy as np
cimport numpy as np
from cython.parallel import prange, parallel
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def assign_abc_cy(np.ndarray[np.float64_t, ndim=1] sales):
    cdef Py_ssize_t n = sales.shape[0]
    cdef np.ndarray[np.intp_t, ndim=1] order = np.argsort(sales)[::-1]
    cdef np.ndarray[np.float64_t, ndim=1] sorted_sales = sales[order]
    cdef np.ndarray[np.float64_t, ndim=1] cumulative = np.empty(n, dtype=np.float64)
    cdef Py_ssize_t i
    cumulative[0] = sorted_sales[0]
    for i in range(1, n):
        cumulative[i] = cumulative[i-1] + sorted_sales[i]
    cdef double total = cumulative[n-1]
    cdef np.ndarray[np.uint8_t, ndim=1] abc = np.empty(n, dtype=np.uint8)
    cdef double share
    with nogil, parallel():
        for i in prange(n, schedule="static"):
            if total > 0.0:
                share = cumulative[i] / total * 100.0
            else:
                share = 0.0
            if share <= 80.0:
                abc[i] = 65
            elif share <= 95.0:
                abc[i] = 66
            else:
                abc[i] = 67
    return order, abc
