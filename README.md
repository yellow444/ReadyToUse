# ReadyToUse

## Overview

ReadyToUse — учебно‑практический проект по оптимизации трёх микросервисов на FastAPI: выдача токенов, поиск идентификатора пользователя и вычисление аналитики. На основе исходных сервисов ведётся переписывание с опорой на CPU‑ускорения, включая AVX/AVX2/AVX512 и многопоточность.

Векторизация и параллельное исполнение считаются обязательными требованиями, а объединение нескольких сервисов в один — лишь возможным направлением дальнейшей оптимизации.

## System Requirements

- Поддерживаемые ОС: Windows 10/11 и Linux/WSL2.
- CPU с поддержкой AVX/AVX2; предпочтительно AVX512.
- Рекомендуется не менее 8 ГБ оперативной памяти.

## Running

### Windows

1. Откройте PowerShell и перейдите в директорию проекта.
2. Создайте и активируйте виртуальное окружение:
   ```powershell
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   ```
3. Установите зависимости:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Запустите приложение:
   ```powershell
   uvicorn app:app --host 0.0.0.0 --port 8080
   ```
   Требуется CPU с поддержкой AVX2.

### Linux/WSL2

1. Перейдите в директорию проекта.
2. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Установите зависимости:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Запустите приложение:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8080
   ```
   Требуется CPU с поддержкой AVX2.

### Docker

```bash
docker run --rm -it -p 8080:8080 -v ${PWD}:/app -w /app python:3.12-slim \
  bash -c "pip install -r requirements.txt && uvicorn app:app --host 0.0.0.0 --port 8080"
```

Требуется CPU хоста с поддержкой AVX2.

### Объединённый микросервис (опционально)

Если в проекте реализован объединённый микросервис, его можно запустить командой:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Tests and Benchmarks

### Unit tests

```bash
pytest
```

### Load testing

Для оценки пропускной способности `POST /item-analytics` используйте `wrk` с подготовленным Lua-скриптом:

```cmd
docker run --rm -v ./script.lua:/data/script.lua skandyla/wrk -c 64 -t 16 -d 60s -s ./script.lua http://localhost:8080/item-analytics
```

Команда нагружает сервис в течение минуты, выводя латентность и число запросов в секунду, например:

```
Running 1m test @ http://localhost:8080/item-analytics
  16 threads and 64 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     4.29ms    0.88ms  21.46ms   79.48%
    Req/Sec     0.94k    65.93     2.18k    79.21%
  896977 requests in 1.00m, 124.04MB read
Requests/sec:  14925.92
```

### Profiling scripts

В репозитории есть PowerShell-скрипты, объединяющие `py-spy` и `wrk`. Каждый запускает сервис, собирает SVG-flamegraph и сохраняет результаты нагрузки.

- `test-old.ps1` — профиль и бенчмарк исходного сервиса `main:app`; выводит `profile-new.svg` и `wrk-old.md`. Используйте для базового сравнения.
- `test-new.ps1` — проверка текущего сервиса `app.main:app` с настройками по умолчанию; выводит `profile-new.svg` и `wrk-new.md`.
- `test-new-faster.ps1` — тот же сервис, но с `--workers 10` для оценки масштабирования; выводит `profile-new-faster.svg` и `wrk-new-faster.md`.

После выполнения открывайте соответствующий файл `profile-*.svg` в браузере, чтобы изучить горячие участки кода.
