# SITCON CAMP 點數系統 bot

## Commands
Build:
```bash
$ docker compose create
```

Run:
```bash
$ docker compose start
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

Remove all iamges, networks and containers:
```bash
$ docker compose down --rmi all -v
```
