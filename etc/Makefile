DEP_NAME=&{ depname }
DBS_NAME=&{ dbsname }
CNX_NAME=&{ cnxname }
ACC_NAME=&{ accname }
TMS_EXEC=$(shell /bin/date "+%Y%m%d_%H%M%S")

all: img_push svc_deploy

snow_reset:
	snow sql -c $(CNX_NAME) -f dbs/reset.sql -D "depname=$(DEP_NAME)" -D "dbsname=$(DBS_NAME)" > log/reset_$(TMS_EXEC).log 2>&1

snow_setup: snow_reset
	snow sql -c $(CNX_NAME) -f dbs/setup.sql -D "depname=$(DEP_NAME)" -D "dbsname=$(DBS_NAME)" > log/setup_$(TMS_EXEC).log 2>&1

snow_add01: snow_setup
	snow sql -c $(CNX_NAME) -f dbs/setkey.sql -D "appname=$(APP_NAME)" -D "dbsname=$(DBS_NAME)" > log/setkey_$(TMS_EXEC).log 2>&1

snow_add02: snow_add01
	snow sql -c $(CNX_NAME) -f dbs/appmod.sql -D "depname=$(DEP_NAME)" -D "dbsname=$(DBS_NAME)" > log/appmod$(TMS_EXEC).log 2>&1

snow_login: snow_add02
	snow spcs image-registry token --connection $(CNX_NAME) --format=JSON | sudo docker login $(ACC_NAME).registry.snowflakecomputing.com --username 0sessiontoken --password-stdin

img_build:
	sudo docker build --platform=linux/amd64 -t app-$(DEP_NAME):latest ./img

img_push: img_build snow_login
	sudo docker tag app-$(DEP_NAME):latest $(ACC_NAME).registry.snowflakecomputing.com/$(DBS_NAME)/$(DEP_NAME)/images/app-$(DEP_NAME):latest
	sudo docker push $(ACC_NAME).registry.snowflakecomputing.com/$(DBS_NAME)/$(DEP_NAME)/images/app-$(DEP_NAME):latest

svc_deploy:
	rm -f app.tar.gz
	rm -rf "./app/helpers/__pycache__"
	tar -zcvf app.tar.gz app
	snow sql -c $(CNX_NAME) -f dbs/deploy.sql -D "depname=$(DEP_NAME)" -D "dbsname=$(DBS_NAME)" > log/deploy_$(TMS_EXEC).log 2>&1

svc_suspend:
	snow sql -c $(CNX_NAME) -f dbs/suspend.sql -D "depname=$(DEP_NAME)" -D "dbsname=$(DBS_NAME)" > log/suspend_$(TMS_EXEC).log 2>&1

svc_resume:
	snow sql -c $(CNX_NAME) -f dbs/resume.sql -D "depname=$(DEP_NAME)" -D "dbsname=$(DBS_NAME)" > log/resume_$(TMS_EXEC).log 2>&1

svc_logs:
	snow sql -c $(CNX_NAME) -f dbs/showlog.sql -D "depname=$(DEP_NAME)" -D "dbsname=$(DBS_NAME)" > log/showlog_$(TMS_EXEC).log 2>&1
	cat log/showlog_$(TMS_EXEC).log
