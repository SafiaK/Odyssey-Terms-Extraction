import pandas as pd
import openAIHandler
import pickle
import util
import json 
import re
import time
import os
import ast
from langchain.docstore.document import Document
from langchain.vectorstores import FAISS

# Initialize the FAISS vector store
global vectore_store


def get_the_relevant_section(query, ref_list,references,legislation_folder_path):
    print("Called the function get_the_relevant_section")
    doc = getTheFirstSection(references,legislation_folder_path)
    try:
        
        print("Got the doc from referene",doc.page_content)
    except:
        doc = get_relevantSection_from_vectore_store(query,ref_list)
    print("Got the doc",doc)
    return doc
def getTheFirstSection(ref_list,legislation_folder_path):
    print("Called the function getTheFirstSection")
    for ref in ref_list:
        act,section = ref['legislation_section']
        if section:
            
            section_u = section.split('/')[0]
            #print(f"the section is {section_u}")
            
            with open(f'{legislation_folder_path}/{act}/section-{section_u}.txt', 'r') as file:
                content = file.read()
                doc = Document(content)
                doc.metadata['id'] = f'{act}_section_{section_u}'
                doc.metadata['legislation_id'] = '{act}'
                print("returning from  the function getTheFirstSection")
                return doc
    print("returning None  the function getTheFirstSection")
    return None
def get_relevantSection_from_vectore_store(query, legislation_filter_list):
    relevant_doc = None
    global vectore_store
    try:
        score = 1
        for legislation in legislation_filter_list:

            results = vectore_store.similarity_search_with_score(
                query=query,
                k=1,
                filter={"legislation_id": legislation}
            )
            #print(results)

            #print(legislation)
            #print(results)
            if len(results)>0:
                doc,score_r = results[0]

                if score_r < score:
                    score = score_r
                    relevant_doc = doc

                
    except Exception as e:
        print(f"Error in get_relevantSection: {e}")
        relevant_doc = None  # Return None if error occurred in search
            
    return relevant_doc
def process_case_annotations(case_number, input_file_path, output_file_path, case_legislation_dic,legislation_dir):
        test_case = input_file_path
        print(f"processing {test_case}")
        annotations_df_gpt=pd.read_csv(test_case)
        annotations_df_gpt['section_id'] = '0'
        annotations_df_gpt['section_text'] = ''
        legislation_list = case_legislation_dic[case_number]
        annotations_df_gpt['if_interpretation'] = annotations_df_gpt['if_interpretation'].astype(str)
        for i,row in annotations_df_gpt.iterrows():
            if (row['if_interpretation'] == '1'):
                try:
                    paragraph = row['paragraphs']
                    references = row.get('references',[])
                    references = ast.literal_eval(references)
                    
                    if len(references)>0:
                        # Extract legislation sections from references if available
                        for ref in references:
                            if isinstance(ref, dict) and 'legislation_section' in ref:
                                legislation_id, section = ref['legislation_section']
                                if legislation_id:
                                    section_id = f"{legislation_id}_{section}"
                                    # Get section text using get_relevantSection
                                    relevant_doc = get_the_relevant_section(paragraph, [legislation_id],references,legislation_dir)
                                    if relevant_doc:
                                        section_text = relevant_doc.page_content
                                        annotations_df_gpt.at[i, 'section_id'] = section_id
                                        annotations_df_gpt.at[i, 'section_text'] = section_text
                                    break
                    else:
                        # Fall back to original behavior if no references
                        relevant_doc = get_the_relevant_section(paragraph,legislation_list,references,legislation_dir)
                        if relevant_doc:
                            section_id = relevant_doc.metadata.get("id", "unknown")
                            section_text = relevant_doc.page_content
                            annotations_df_gpt.at[i, 'section_id'] = section_id
                            annotations_df_gpt.at[i, 'section_text'] = section_text
                except:
                    pass
                    
        output_file = output_file_path
        annotations_df_gpt.to_csv(output_file, index=False)
def getJsonList(results_str):
    try:
        results = json.loads(results_str)
        return results
    except:
        match = re.search(r'```json\n(.*?)\n```', results_str, re.S)
        if match:
            json_string = match.group(1)
        try:
            # Parse the extracted JSON string
            json_data = json.loads(json_string)
            print("Successfully extracted JSON list:")
            return json_data

           
        except json.JSONDecodeError as e:
            print("Error parsing JSON:", e)
            return []
def processToGetTriples(llm_chain_extraction,input_file_path, output_file_path):
    print(f"processing to extract phrases from file {input_file_path}")
    annotations_df_gpt = pd.read_csv(input_file_path,index_col=False)
    annotations_df_gpt['triples_result'] = ''
    for i ,row in annotations_df_gpt.iterrows():
        para_id =row['para_id']
        case_text = row['paragraphs']
        legislation_text = row['section_text']
        section_id = row['section_id']
        
        if section_id != '0':
        #print(text)
        #print(section_text)
            try:
                RESULTS = openAIHandler.getInterPretations(legislation_text,case_text,llm_chain_extraction)
                print(para_id)
                print(section_id)
                print("===========================")

                results = getJsonList(RESULTS)
                #RESULTS_legit = getIflegit(results,case_text,legislation_text)
                #print(RESULTS_legit)
                annotations_df_gpt.at[i, 'triples_result'] = results
            except Exception as e:
                print(f"Error occurred: {e}")
                continue
    annotations_df_gpt.to_csv(output_file_path,index=False)

def getTheLegitPhrases(case_file_path):
    data = pd.read_csv(case_file_path, index_col=False)
    data_expanded = data['key_phrases'].explode()
    data_expanded['in_section_text'] = data_expanded.apply(
        lambda row: row['phrases'] in row['section_text'], axis=1)
    
    # Keep rows with in_section_text=True
    data_expanded = data_expanded[data_expanded['in_section_text'] == True]
    
    # Drop the in_section_text column
    data_expanded = data_expanded.drop(columns=['in_section_text'])
    
    data_expanded.to_csv(case_file_path, index=False)

def extractThePhrases(case_act_pickle_file,input_dir,output_dir,legislation_dir):
    print("Key Phrase Extractor is running...")
    with open(case_act_pickle_file, 'rb') as f:
        case_legislation_dic = pickle.load(f)
    acts = list(set(util.flatten_list_of_lists(case_legislation_dic.values())))
    global vectore_store
    vectore_store = openAIHandler.BuildVectorDB(legislation_dir,acts)
    case_list = list(case_legislation_dic.keys()) 
    sections_dir = f"{output_dir}/sections"
    os.makedirs(sections_dir, exist_ok=True)
    llm_chain_extraction = openAIHandler.getPhraseExtractionChain()
    for case_number in case_list:
        interpreted_file = f"{input_dir}/{case_number}.csv"
        interpreted_file_with_sections = f"{sections_dir}/{case_number}.csv"
        process_case_annotations(case_number, interpreted_file, interpreted_file_with_sections, case_legislation_dic,legislation_dir)
    for case_number in case_list:
        interpreted_file = f"{input_dir}/{case_number}.csv"
        interpreted_file_with_sections = f"{sections_dir}/{case_number}.csv"
        processToGetTriples(llm_chain_extraction, interpreted_file_with_sections, interpreted_file_with_sections)
        getTheLegitPhrases(interpreted_file_with_sections)
        time.sleep(10) # Sleep for 10 seconds to avoid rate limiting
    

    


if __name__ == "__main__":
    extractThePhrases()
