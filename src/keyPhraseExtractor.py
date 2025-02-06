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
    
    try:
        doc = getTheFirstSection(references,legislation_folder_path)
        if doc is None:
            doc = get_relevantSection_from_vectore_store(query,ref_list)
    except:
        doc = get_relevantSection_from_vectore_store(query,ref_list)
    return doc
def getTheFirstSection(ref_list,legislation_folder_path):
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
                return doc
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
                                    #section_id = f"{legislation_id}_{section}"
                                    # Get section text using get_relevantSection
                                    relevant_doc = get_the_relevant_section(paragraph, [legislation_id],references,legislation_dir)
                                    if relevant_doc:
                                        section_id = relevant_doc.metadata.get("id", "unknown")
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

def getTheInterpretationDf(dataframe):
    # Filter rows where 'triples_result' is not NaN
    filtered_df = dataframe[dataframe['triples_result'].notna()]

    # Initialize a list to store the extracted data
    extracted_data = []

    # Iterate over each row in the filtered DataFrame
    for _, row in filtered_df.iterrows():
        # Parse the 'triples_result' JSON string into a list of dictionaries
        triples = ast.literal_eval(row['triples_result'])

        # Extract relevant fields from each triple
        for triple in triples:
            try:
                legislation_phrases =triple['key_phrases/concepts']
            except:
                legislation_phrases = triple['key_phrases']
                

            case_term = triple.get('case_law_term', '')
            legislation_term = triple.get('legislation_term', '')
            confidence = triple.get('confidence', '')
            reasoning = triple.get('reasoning', '')
            #legislation_phrases = triple.get('key_phrases/concepts', [])
            

            # Append the extracted data along with additional information to the list
            extracted_data.append({
                'url': row.get('case_uri', ''),
                'para_id': row.get('para_id', ''),
                'paragraphs': row.get('paragraphs', ''),
                'case_term_phrases': row.get('interpretation_phrases', ''),
                'legislation_id': row.get('section_id', ''),
                'section_text':row.get('section_text', ''),
                'case_term': case_term,
                'legislation_term': legislation_term,
                'confidence': confidence,
                'reasoning': reasoning,
                'key_phrases': legislation_phrases
            })

    # Create a new DataFrame from the extracted data
    new_dataframe = pd.DataFrame(extracted_data)

    # Return the new DataFrame
    return new_dataframe
def getTheLegitPhrases(case_input_file_path,case_output_file_path):
    def checkIfPhraseInText(phrase,text):
        try:
            if phrase in text:
                return True
            else:
                return False
        except:
            return False
    print("=====================================")
    print(f"processing to extract phrases from file {case_input_file_path}")
    print("=====================================")
    data = pd.read_csv(case_input_file_path,index_col=False)
    data = getTheInterpretationDf(data)

    data_expanded = data.explode('key_phrases')
    data_expanded = data_expanded.dropna(subset='key_phrases')
    data_expanded['section_text'] = data_expanded['section_text'].astype(str)
    data_expanded['key_phrases'] = data_expanded['key_phrases'].astype(str)
    data_expanded['in_section_text'] = data_expanded.apply(
        lambda row: checkIfPhraseInText(row['key_phrases'], row['section_text']),axis=1)
    data_expanded = data_expanded[data_expanded['in_section_text']==True]
    data_expanded.drop(columns=['in_section_text'], inplace=True)
    data_expanded.to_csv(case_output_file_path,index=False)

def get_the_final_files(input_folder, output_folder):
    """
    Process CSV files in the input folder and separate rows based on specific conditions.

    Args:
        input_folder (str): Path to the folder containing input CSV files.
        output_folder (str): Path to the folder where output CSV files will be saved.
    """
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # List all CSV files in the input folder
    csv_files = [file for file in os.listdir(input_folder) if file.endswith('.csv')]

    # Initialize lists to store rows
    rows_with_phrases = []
    rows_without_phrases = []

    # Process each CSV file
    for csv_file in csv_files:
        file_path = os.path.join(input_folder, csv_file)

        # Read the CSV file
        df = pd.read_csv(file_path)

        # Ensure "if_interpretation" column is treated as string
        df["if_interpretation"] = df["if_interpretation"].astype(str)

        # Filter rows where "if_interpretation" equals '1'
        filtered_rows = df[df["if_interpretation"] == '1']

        # Separate rows based on "triples_result" column
        for _, row in filtered_rows.iterrows():
            # Convert "triples_result" to a Python object if it's a string representation of a list
            try:
                triples_result = ast.literal_eval(row["triples_result"])
            except (ValueError, SyntaxError):
                triples_result = None

            # Check if "triples_result" is a non-empty list
            if isinstance(triples_result, list) and len(triples_result) > 0:
                rows_with_phrases.append(row)
            else:
                rows_without_phrases.append(row)

    # Convert lists to DataFrames
    df_with_phrases = pd.DataFrame(rows_with_phrases)
    df_without_phrases = pd.DataFrame(rows_without_phrases)

    # Save the DataFrames to output folder
    with_phrases_path = os.path.join(output_folder, 'rows_with_phrases.csv')
    without_phrases_path = os.path.join(output_folder, 'rows_without_keyPhrases.csv')

    df_with_phrases.to_csv(with_phrases_path, index=False)
    df_without_phrases.to_csv(without_phrases_path, index=False)

    print(f"Saved rows with phrases to: {with_phrases_path}")
    print(f"Saved rows without key phrases to: {without_phrases_path}")

    return with_phrases_path,without_phrases_path


def extractThePhrases(case_act_pickle_file,input_dir,output_dir,legislation_dir,output_folder_path_for_aggregated_result):
    print("Key Phrase Extractor is running...")
    with open(case_act_pickle_file, 'rb') as f:
        case_legislation_dic = pickle.load(f)
    acts = list(set(util.flatten_list_of_lists(case_legislation_dic.values())))
    global vectore_store
    vectore_store = openAIHandler.BuildVectorDB(legislation_dir,acts)
    case_list = list(case_legislation_dic.keys()) 
    sections_dir = f"{output_dir}/csv_with_legislation"
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
        time.sleep(10) # Sleep for 10 seconds to avoid rate limiting
    

        
   
    with_phrases_path,without_phrases_path = get_the_final_files(sections_dir, output_folder_path_for_aggregated_result)
    interpreted_file_with_phrases= f"{output_folder_path_for_aggregated_result}/ExplodedPhrases.csv" 
    getTheLegitPhrases(with_phrases_path,interpreted_file_with_phrases)

        
  
    

if __name__ == "__main__":
    pass
