# SITCON CAMP 點數系統 bot

## Setup

## Commands
Build:
```bash
$ docker compose create
```

Run:
```bash
$ docker compose start
```

Stop:
```bash
$ docker compose stop
```

Build and Run:
```bash
$ docker compose up
```
Or in detach mode:
```bash
$ docker compose up -d
```

Remove image `camp2017`, networks and containers:
```bash
$ docker compose down --rmi local -v
```

Usually, it takes long to pull `mongo` image.  
Remove all images, networks and containers:
```bash
$ docker compose down --rmi all -v
```
