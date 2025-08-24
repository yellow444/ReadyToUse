py-spy record -o profile-new.svg --duration 80 --threads -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --http httptools --no-server-header --log-level warning --lifespan on &
Start-Sleep -Seconds 5
docker run --rm -v ./script.lua:/data/script.lua skandyla/wrk -c 64 -t 16 -d 60s -s ./script.lua http://192.168.50.100:8080/item-analytics > wrk-new.md
