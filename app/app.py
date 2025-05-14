import time
import datetime
import pandas as pd
import streamlit as st
import snowflake.connector
from snowflake.cortex import Complete, Translate
from snowflake.snowpark import Session, FileOperation
from snowflake.snowpark import functions as f
import ollama as ol
import helpers




# Get User from SPCS Headers
try:
    user = st.context.headers["Sf-Context-Current-User"] or 'Visitor'
except KeyError:
    user = 'Visitor'

st.set_page_config(page_title = f'DocMore [{user}]', page_icon = ':green_book:', layout = 'wide')
#https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/
#https://ollama.com/blog/python-javascript-libraries




# Make connection to Snowflake and cache it
@st.cache_resource
def connect_to_snowflake():
    return helpers.session()



session = connect_to_snowflake()




@st.cache_data
def create_prompt( myquestion, rag ):
    if rag == 1:
        qry = f"""
            SELECT
                 RELATIVE_PATH
                ,VECTOR_COSINE_DISTANCE(CHUNK_V768, SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2','{myquestion}')) AS DISTANCE
                ,CHUNK_TEXT
            FROM KBASE
            ORDER BY DISTANCE ASC
            LIMIT 1
        """
        df_context = session.sql(qry).to_pandas()
        prompt_context = df_context._get_value(0,'CHUNK_TEXT').replace("'", "")
        relative_path =  df_context._get_value(0,'RELATIVE_PATH')
    
        prompt = f"""{myquestion}? Build the answer using the following context: {prompt_context}"""
        qry = f"SELECT GET_PRESIGNED_URL(@INBOX, '{relative_path}', 360) as URL_LINK FROM DIRECTORY(@INBOX)"
        url_link = session.sql(qry).to_pandas()._get_value(0,'URL_LINK')

    else:
        prompt = myquestion
        url_link = "None"
        relative_path = "None"
        
    return prompt, url_link, relative_path




def make_complete(question, model, placeholder, rag, esp_in, esp_out):
    if question != '':
        my_question = question
        if esp_in == 1:
            my_question = Translate(
                text = question,
                from_language = '',
                to_language = 'es',
                session = session
            )
        
        prompt, url_link, relative_path = create_prompt( my_question, rag )

        full_response = ''
        if model_serving == "Ollama":
            full_response = complete_ollama( prompt, model, placeholder )
        else:
            full_response = complete_cortex( prompt, model, placeholder ) 

        if rag == 1:
            display_url = f"Link to [{relative_path}]({url_link}) that may be useful"
            c2.markdown(display_url)

        if esp_out == 1:
            full_response = Translate(
                text = full_response,
                from_language = '',
                to_language = 'es',
                session = session
            )
            placeholder.markdown(full_response)




def complete_cortex(prompt, model, placeholder):
    stream = Complete(
        model = model,
        prompt = prompt,
        session = session,
        stream = True
    )

    ctx_response = ''
    for update in stream:
        ctx_response += update
        placeholder.markdown(ctx_response)

    return ctx_response




def complete_ollama(prompt, model, placeholder):
    stream = ol.chat(
        model = model,
        messages = [{
            'role': 'user',
            'content': prompt,
        }],
        stream = True
    )
    
    ol_response = ''
    for update in stream:
        ol_response += update['message']['content']
        placeholder.markdown(ol_response)

    return ol_response




with st.sidebar:
    inbox_stage='INBOX'

    st.sidebar.title(f"DocMore v1.0")
    st.header(f"", divider='rainbow')

    st.subheader("Knowledge Base")
    st.data_editor(
        session.sql("SELECT RELATIVE_PATH, FILE_SIZE, LAST_MODIFIED FROM KBASE GROUP BY ALL").collect(),
        column_config={
            "RELATIVE_PATH": "Name",
            "FILE_SIZE": "Size",
            "LAST_MODIFIED": "Timestamp"
        },
        hide_index=True
    )

    st.subheader("Knowledge Drop")
    with st.expander("Processing queue"):
        #st.header("Processing queue")
        st.data_editor(
            session.sql("SELECT RELATIVE_PATH, SIZE FROM INBOX_STREAM ORDER BY LAST_MODIFIED DESC").collect(),
            column_config={
                "relative_path": "Name",
                "size": "Size"
            },
            hide_index=True
        )
    
    file_to_upload = st.file_uploader("Add PDFs")
    if file_to_upload is not None:
        FileOperation(session).put_stream(
            input_stream=file_to_upload, 
            #add per user location so that we can retrieve the owner when making chunks
            stage_location='@'+inbox_stage+'/'+file_to_upload.name,
            auto_compress=False,
            overwrite=True
        )

        qry = f"""
            ALTER STAGE {inbox_stage} REFRESH;
        """
        
        session.sql(qry).collect()

    private_doc = st.toggle('Keep private', True)
    #st.caption(f" Connected as [{user}]")
    current_role = session.create_dataframe([1]).select(snowflake.snowpark.functions.current_role()).collect()[0]['CURRENT_ROLE()']
    st.markdown(f"<div style='text-align: center; color: grey;'> Role [{current_role}]</div>", unsafe_allow_html=True)




left_co,gap,right_co = st.columns([1,0.15,2])

with left_co:
    c1 = st.container()
with right_co:
    c2 = st.container()

model_serving = c1.radio(
    "Model Serving",
    key="model_serving",
    options=["Cortex", "Ollama"],
)

if model_serving != "None" and model_serving == "Cortex":
    model_list = {
        'models': ['mistral-7b','mixtral-8x7b','mistral-large2','claude-3-5-sonnet','gemma-7b','jamba-1.5-mini','jamba-instruct','reka-flash','reka-core','snowflake-arctic','llama3.1-405b','llama3.1-70b','llama3.1-8b'],
        'command': ['mistral-7b','mixtral-8x7b','mistral-large2','claude-3-5-sonnet','gemma-7b','jamba-1.5-mini','jamba-instruct','reka-flash','reka-core','snowflake-arctic','llama3.1-405b','llama3.1-70b','llama3.1-8b']
    }
elif model_serving != "None" and model_serving == "Ollama":
    model_list = {
        'models': ['deepseek-r1:7b', 'deepseek-r1:70b', 'deepseek-v3', 'gemma3:27b', 'llama3.3:70b', 'llama3.1:405b', 'phi4:latest'],
        'command': ['deepseek-r1:7b', 'deepseek-r1:70b', 'deepseek-v3', 'gemma3:27b', 'llama3.3:70b', 'llama3.1:405b', 'phi4:latest']
    }

models_pd = pd.DataFrame(data=model_list)

model = c1.selectbox('Model:', models_pd['command'])

if model_serving == "Ollama":
    ol_avail_list = ol.list()
    ol_avail_names = []
    for m in ol_avail_list['models'] :
        ol_avail_names.append(m['model'])

    if len(ol_avail_names) == 0 or model not in ol_avail_names:
        c1.write("No preloaded model/s found")

        if c1.button("Download"):
            with st.spinner(f"Pulling Ollama[ {model} ]"):
                ol.pull(model)

    else :
        c1.caption(f'Found preloaded models ({", ".join(ol_avail_names)})')




rag = c1.checkbox('Use Knowledge Base for context', False)
es_in = c1.checkbox('Pregunta en Español', False)
es_out = c1.checkbox('Inferencia en Español', False)

question_in = c2.text_input("Prompt", placeholder="Pregunta aqui" if es_in else "Ask your question here", label_visibility="collapsed")

c2_c1,c2_c2 = c2.columns([2,4])

infer_out = c2.empty()

with c2_c1:
    st.button("Ask", on_click=make_complete(question_in, model, infer_out, 1 if rag else 0, 1 if es_in else 0, 1 if es_out else 0))
    #st.button("Clear", on_click=infer_out.markdown(''))

with c2_c2:
    his = st.checkbox('Cargar el historico de la conversación' if es_in else 'Load my previous conversations', False)
