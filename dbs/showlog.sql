SET TARGET_DATABASE   = '<% dbsname %>';
SET DEPLOY_SCHEMA     = '<% depname %>';
SET DEPLOY_ROLE_OWNER = '<% depname %>_ROL';
SET APP_ROLE_TYPE_01  = '<% depname %>_R01';
SET APP_ROLE_TYPE_02  = '<% depname %>_R02';
SET SERVICE_NAME      = '<% depname %>_SVC';
SET SERVICE_RUN_USER  = '<% depname %>_USR';
SET SERVICE_RUN_POOL  = '<% depname %>_CPL';
SET SERVICE_RUN_VWHS  = '<% depname %>_VWH';
SET EXT_ACC_INT_NAME  = '<% depname %>_EAI';
SET EXT_ACC_NET_RULE  = '<% depname %>_NRL';
SET SERVICE_REF       = 'dep-<% depname %>';

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