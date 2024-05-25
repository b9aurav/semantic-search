## Deploy it locally

1. Clone repo
```
git clone https://github.com/b9aurav/semantic-search.git
```

2. Update .env file (Rename .env.example to .env)
```
ELASTIC_USERNAME=  <--- Your elasticsearch username
ELASTIC_PASSWORD=  <--- Your elasticsearch password
```

2. Build docker compose services
```
docker-compose build
```

3. Start docker compose services
```
docker-compose up
```

Wait for services to be ready, and then test APIs from http://localhost:80/docs