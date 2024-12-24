bind = "unix:/home/ec2-user/logwatcher/logwatcher.sock"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 65
timeout = 120
