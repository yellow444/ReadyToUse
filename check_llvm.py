# check_llvm_fixed.py
import numba as nb
import numpy as np
import subprocess
import os

def check_llvm_installation():
    print("=== LLVM Installation Check ===")
    
    # Проверка системного LLVM
    try:
        result = subprocess.run(['llvm-config', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ System LLVM found:", result.stdout.strip())
        else:
            print("✗ System LLVM not found")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("✗ llvm-config command not available")
    
    # Проверка переменных окружения
    llvm_config = os.environ.get('LLVM_CONFIG', '')
    print("LLVM_CONFIG env variable:", llvm_config if llvm_config else 'Not set')
    
    # Проверка PATH
    path_has_llvm = any('llvm' in path.lower() for path in os.environ.get('PATH', '').split(';'))
    print("PATH contains LLVM:", path_has_llvm)

def check_numba_capabilities():
    print("\n=== Numba Capabilities Check ===")
    
    print("Numba version:", nb.__version__)
    
    # Проверка основных возможностей
    print("AVX support:", nb.config.ENABLE_AVX)
    print("Parallel diagnostics:", nb.config.PARALLEL_DIAGNOSTICS)
    
    # Тест параллельной компиляции
    try:
        from numba import prange
        
        @nb.njit(parallel=True, fastmath=True)
        def simple_parallel_test(arr):
            total = 0.0
            for i in prange(arr.shape[0]):
                total += arr[i] * arr[i]
            return total
        
        test_arr = np.ones(10, dtype=np.float64)
        result = simple_parallel_test(test_arr)
        print("✓ Parallel compilation test: SUCCESS")
        print(f"  Test result: {result}")
        
    except Exception as e:
        print("✗ Parallel compilation test: FAILED")
        print(f"  Error: {e}")

if __name__ == "__main__":
    check_llvm_installation()
    check_numba_capabilities()