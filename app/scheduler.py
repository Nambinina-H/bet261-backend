from apscheduler.schedulers.background import BackgroundScheduler

# Scheduler global : heberge le job de collecte (voir collector/cron).
scheduler = BackgroundScheduler()
