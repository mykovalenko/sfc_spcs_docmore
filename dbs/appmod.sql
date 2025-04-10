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


---------------------------------------------------------------------------------
USE ROLE IDENTIFIER($DEPLOY_ROLE_OWNER);
USE DATABASE IDENTIFIER($TARGET_DATABASE);
USE SCHEMA IDENTIFIER($DEPLOY_SCHEMA);
USE WAREHOUSE IDENTIFIER($SERVICE_RUN_VWHS);

CREATE STAGE IF NOT EXISTS MODELS
    ENCRYPTION = (TYPE='SNOWFLAKE_SSE') 
    DIRECTORY = (ENABLE = TRUE);

CREATE OR REPLACE STAGE INBOX
    ENCRYPTION = (TYPE='SNOWFLAKE_SSE')
    DIRECTORY = (ENABLE = TRUE);

CREATE OR REPLACE STREAM INBOX_STREAM ON DIRECTORY(@INBOX);

CREATE OR REPLACE TEMPORARY TABLE STREAM_DUMP AS SELECT * FROM INBOX_STREAM;
INSERT INTO STREAM_DUMP SELECT * FROM INBOX_STREAM;
DROP TABLE STREAM_DUMP;
ALTER STAGE INBOX REFRESH;



CREATE OR REPLACE TABLE KBASE (
     RELATIVE_PATH VARCHAR
    ,FILE_SIZE NUMBER(38,0)
    ,FILE_URL VARCHAR
    ,SCOPED_URL VARCHAR
    ,LAST_MODIFIED TIMESTAMP_TZ(3)
    ,CHUNK_TEXT VARCHAR
    ,CHUNK_EN VARCHAR
    ,CHUNK_V768 VECTOR(FLOAT, 768)
    ,CHUNK_V1024 VECTOR(FLOAT, 1024)
    --,CREATED_BY VARCHAR
    --,FLAG_PRIVATE BOOLEAN
    --,SHARED_WITH ARRAY
);



CREATE OR REPLACE FUNCTION PDF_TO_PAGESET(file_path VARCHAR)
    RETURNS TABLE (pagenum INT, page VARCHAR)
    LANGUAGE PYTHON
    RUNTIME_VERSION = 3.11
    PACKAGES = ('pypdf2', 'snowflake-snowpark-python')
    HANDLER = 'Pdf2Txt'
AS $$
import io
from PyPDF2 import PdfReader
from snowflake.snowpark.files import SnowflakeFile

class Pdf2Txt:
    def process(self, file_path):
        with SnowflakeFile.open(file_path, 'rb') as file:
            f = io.BytesIO(file.readall())
            pdfreader = PdfReader(f)
            for page in range(len(pdfreader.pages)):
                #clean_text = pdfreader.getPage(page_num).extract_text().strip().replace('\n', ' ')
                yield((page, pdfreader.pages[page].extract_text()))
$$;



CREATE OR REPLACE FUNCTION TXT_TO_CHUNKS(text VARCHAR, separator VARCHAR, chunk_size INT, chunk_overlap INT)
    RETURNS TABLE (chunk VARCHAR)
    LANGUAGE PYTHON
    RUNTIME_VERSION = 3.11
    PACKAGES = ('pandas', 'langchain')
    HANDLER = 'Txt2Chunks'
AS $$
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter

class Txt2Chunks:
    def process(self, text, separator, chunk_size, chunk_overlap):        
        text_splitter = RecursiveCharacterTextSplitter(
            separators = [separator],
            chunk_size = chunk_size,
            chunk_overlap  = chunk_overlap,
            length_function = len,
            add_start_index = True
        )
        
        #chunks = text_splitter.create_documents([text])
        #df = pd.DataFrame(chunks, columns=['chunks','meta'])
        chunks = text_splitter.split_text(text)
        df = pd.DataFrame(chunks, columns=['chunks'])
        
        yield from df.itertuples(index=False, name=None)
$$;



CREATE OR REPLACE TASK KBASE_KEEPER
    WAREHOUSE = $SERVICE_RUN_VWHS
    SCHEDULE = '1 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA( 'INBOX_STREAM' )
AS
    INSERT INTO KBASE( RELATIVE_PATH, FILE_SIZE, FILE_URL, SCOPED_URL, LAST_MODIFIED, CHUNK_TEXT, CHUNK_EN, CHUNK_V768, CHUNK_V1024 )
    WITH RAW_TEXT AS (
        SELECT
             S.RELATIVE_PATH
            ,S.SIZE AS FILE_SIZE
            ,S.FILE_URL
            ,S.LAST_MODIFIED
            ,LISTAGG(p.page, '\n') WITHIN GROUP (ORDER BY pagenum) DOC_TEXT
            ,BUILD_SCOPED_FILE_URL( @INBOX, S.RELATIVE_PATH ) as SCOPED_URL
        FROM 
            INBOX_STREAM as S,
            TABLE( PDF_TO_PAGESET( BUILD_SCOPED_FILE_URL( @INBOX, S.RELATIVE_PATH ) ) ) AS P
        WHERE
            LOWER(S.RELATIVE_PATH) LIKE '%.pdf'
        GROUP BY
            S.RELATIVE_PATH, S.SIZE, S.FILE_URL, S.LAST_MODIFIED
    )
    SELECT
         R.RELATIVE_PATH
        ,R.FILE_SIZE
        ,R.FILE_URL
        ,R.SCOPED_URL
        ,R.LAST_MODIFIED
        ,C.CHUNK AS CHUNK_TEXT
        ,SNOWFLAKE.CORTEX.TRANSLATE(C.CHUNK, '', 'en') AS CHUNK_EN
        ,SNOWFLAKE.CORTEX.EMBED_TEXT_768( 'e5-base-v2', C.CHUNK ) AS CHUNK_V768
        ,SNOWFLAKE.CORTEX.EMBED_TEXT_1024( 'voyage-multilingual-2', C.CHUNK ) AS CHUNK_V1024
    FROM RAW_TEXT R
        ,TABLE( TXT_TO_CHUNKS( R.DOC_TEXT, '\n', 3000, 50 ) ) C
;



ALTER TASK IF EXISTS KBASE_KEEPER RESUME;
