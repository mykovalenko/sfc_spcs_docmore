SET TARGET_DATABASE   = '<% dbsname %>';
SET DEPLOY_SCHEMA     = '<% depname %>';
SET DEPLOY_ROLE_OWNER = 'APP_<% depname %>_OWNER';
SET APP_ROLE_TYPE_01  = 'APP_<% depname %>_ROL01';
SET APP_ROLE_TYPE_02  = 'APP_<% depname %>_ROL02';
SET APP_NB_CONTROL    = 'APP_<% depname %>_CONTROL';
SET SERVICE_NAME      = 'APP_<% depname %>_SVC';
SET SERVICE_RUN_USER  = 'APP_<% depname %>_USER';
SET SERVICE_RUN_POOL  = 'APP_<% depname %>_POOL';
SET SERVICE_RUN_VWHS  = 'APP_<% depname %>_WH';
SET EXT_ACC_INT_NAME  = 'APP_<% depname %>_EXASINT';
SET EXT_ACC_NET_RULE  = 'APP_<% depname %>_NETRULE';
SET SERVICE_REF       = 'app-<% depname %>';

---------------------------------------------------------------------------------
USE ROLE IDENTIFIER($DEPLOY_ROLE_OWNER);

USE DATABASE IDENTIFIER($TARGET_DATABASE);
USE SCHEMA IDENTIFIER($DEPLOY_SCHEMA);
USE WAREHOUSE IDENTIFIER($SERVICE_RUN_VWHS);

SELECT $1 from @SPECS/service.yaml; 

SHOW SERVICES;

-- check the status of service
CALL SYSTEM$GET_SERVICE_STATUS($SERVICE_NAME);

-- check the logs in the docker containers
CALL SYSTEM$GET_SERVICE_LOGS($SERVICE_NAME, '0', $SERVICE_REF, 1000);

SHOW SERVICE CONTAINERS IN SERVICE IDENTIFIER($SERVICE_NAME);
SHOW ENDPOINTS IN SERVICE IDENTIFIER($SERVICE_NAME);