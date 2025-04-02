import time
import datetime
import pandas as pd
import streamlit as st
import snowflake.connector
from snowflake.cortex
from snowflake.snowpark import Session, FileOperation
from snowflake.snowpark import functions as f
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManagerForLLMRun
import ollama as ol
import helpers

# Get User from SPCS Headers
try:
    user = st.context.headers["Sf-Context-Current-User"] or Visitor
except KeyError:
    user = "Visitor"

# Make connection to Snowflake and cache it
@st.cache_resource
def connect_to_snowflake():
    return helpers.session()

#https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/
st.set_page_config(page_title = f'DocMore [{user}]', page_icon = ':green_book:', layout = 'wide')



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
    
        prompt = f"""
            'Answer the question based on the context.
            Context: {prompt_context}
            Question: {myquestion}'
        """
        qry = f"SELECT GET_PRESIGNED_URL(@INBOX, '{relative_path}', 360) as URL_LINK FROM DIRECTORY(@INBOX)"
        url_link = session.sql(qry).to_pandas()._get_value(0,'URL_LINK')

    else:
        prompt = f"""
            'Question: {myquestion} 
            Answer: '
        """
        url_link = "None"
        relative_path = "None"
        
    return prompt, url_link, relative_path



def complete(question, model, placeholder, rag, esp_in, esp_out):
    my_question = question
    if esp_in == 1:
        my_question = snowflake.cortex.translate(
            text = question,
            from_language = '',
            to_language = 'es',
            session = session
        )
    
    my_prompt, url_link, relative_path = create_prompt(my_question, rag)
    stream = snowflake.cortex.complete(
        model = model,
        prompt = my_prompt,
        session = session,
        stream = True
    )

    ctx_response = ''
    for update in stream:
        ctx_response += update
        placeholder.markdown(ctx_response)

    if rag == 1:
        display_url = f"Link to [{relative_path}]({url_link}) that may be useful"
        c2.markdown(display_url)

    if esp_out == 1:
        ctx_response = snowflake.cortex.translate(
            text = ctx_response,
            from_language = '',
            to_language = 'es',
            session = session
        )
        placeholder.markdown(ctx_response)



def complete_ol(question, placeholder, rag, esp_in, esp_out):
    my_question = question
    if esp_in == 1:
        my_question = snowflake.cortex.translate(
            text = question,
            from_language = '',
            to_language = 'es',
            session = session
        )
    
    my_prompt, url_link, relative_path = create_prompt(my_question, rag)
    
    run_manager = CallbackManagerForLLMRun()
    stream = ollama._stream(my_prompt, run_manager=run_manager)
    
    ol_response = ''
    for update in stream:
        ol_response += update
        placeholder.markdown(ol_response)

    if rag == 1:
        display_url = f"Link to [{relative_path}]({url_link}) that may be useful"
        c2.markdown(display_url)

    if esp_out == 1:
        ol_response = snowflake.cortex.translate(
            text = ol_response,
            from_language = '',
            to_language = 'es',
            session = session
        )
        placeholder.markdown(ol_response)



def display_response (response, url_link, relative_path):
    full_response = ''
    placeholder = c2.empty()
    for char in response:
        full_response += char
        placeholder.markdown(full_response)
        time.sleep(0.01)

    if rag == 1:
        display_url = f"Link to [{relative_path}]({url_link}) that may be useful"
        c2.markdown(display_url)



def display_response_ol (question, rag):
    response, url_link, relative_path = complete_ol(question, rag)

    c2.markdown( response[0].RESPONSE_ES if esp == 1 else response[0].RESPONSE )
    
    if rag == 1:
        display_url = f"Link to [{relative_path}]({url_link}) that may be useful"
        c2.markdown(display_url)



def change_label_style(label, font_size='12px', font_color='black', font_family='sans-serif'):
    html = f"""
    <script>
        var elems = window.parent.document.querySelectorAll('p');
        var elem = Array.from(elems).find(x => x.innerText == '{label}');
        elem.style.fontSize = '{font_size}';
        elem.style.color = '{font_color}';
        elem.style.fontFamily = '{font_family}';
    </script>
    """
    st.components.v1.html(html)



session = connect_to_snowflake()

inbox_stage='INBOX'

with st.sidebar:
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
        'models': ['claude-3-5-sonnet','gemma-7b','jamba-1.5-mini','jamba-instruct','mistral-7b','mixtral-8x7b','mistral-large2','reka-flash','reka-core','snowflake-arctic','llama3.1-405b','llama3.1-70b','llama3.1-8b'],
        'command': ['claude-3-5-sonnet','gemma-7b','jamba-1.5-mini','jamba-instruct','mistral-7b','mixtral-8x7b','mistral-large2','reka-flash','reka-core','snowflake-arctic','llama3.1-405b','llama3.1-70b','llama3.1-8b']
    }
elif model_serving != "None" and model_serving == "Ollama":
    model_list = {
        'models': ['deepseek-r1:7b', 'deepseek-r1:70b', 'deepseek-v3', 'gemma3:27b', 'llama3.3:70b', 'phi4'],
        'command': ['deepseek-r1:7b', 'deepseek-r1:70b', 'deepseek-v3', 'gemma3:27b', 'llama3.3:70b', 'phi4']
    }

models_pd = pd.DataFrame(data=model_list)

model = c1.selectbox('Model:', models_pd['command'])

if model_serving == "Ollama":
    ol_avail_list = ol.list()
    ol_avail_names = []
    for m in ol_avail_list['models'] :
        st.print(m['model'])
        ol_avail_names.append(m['model'])

    if len(ol_avail_names) == 0 or model not in ol_avail_names:
        c1.write("No preloaded model/s found")

        if c1.button("Download"):
            # Initialize Ollama
            with st.spinner(f"Pulling Ollama[ {model} ]"):
                ol.pull(model)

    else :
        #st.markdown(f'Found preloaded models (:blue[{", ".join(ol_avail_names)}])')
        c1.caption(f'Found preloaded models ({", ".join(ol_avail_names)})')

    ollama = Ollama(model=model)


def clear_output(e):
    e.markdown('')

rag = c1.checkbox('Use Knowledge Base for context', False)
es_in = c1.checkbox('Pregunta en Español', False)
es_out = c1.checkbox('Inferencia en Español', False)

question = c2.text_input("Prompt", placeholder="Pregunta aqui" if es_in else "Ask your question here", label_visibility="collapsed")

c2_c1,c2_c2 = c2.columns([1,5])

inf_out = c2.empty()

with c2_c1:
    st.button("Clear", on_click=clear_output(inf_out))

with c2_c2:
    his = st.checkbox('Cargar el historico de la conversación' if es_in else 'Load my previous conversations', False)

if question:
    if model_serving == "Ollama":
        complete_ol( question, inf_out, 1 if rag else 0, 1 if es_in else 0, 1 if es_out else 0 )
    else:
        complete( question, model, inf_out, 1 if rag else 0, 1 if es_in else 0, 1 if es_out else 0 ) 
