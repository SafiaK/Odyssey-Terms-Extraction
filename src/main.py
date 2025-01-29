import os
from LegislationHandler import LegislationParser
from JudgementHandler import JudgmentParser
import pandas as pd
from classifier import process_csv_with_openai
import time
import ast
import pickle
import keyPhraseExtractor


#This is the main class for the pipeline
# Each step is listed and commented for clarity
# Step#1
##Convert_CSVs_xml_to_Csv
## The pipline starts with parsing the caselaw XML and converting it to Json format
# Step#2
## Extract_Judgment_Body_Paragraphs_Text
## Extracts the judgment body paragraphs and their corresponding text and references
# Step#3
### Extract_Legislation_Text
## Downlod the legislation act section by section



def Convert_CSVs_xml_to_Csv(caselaw_xml_path,caselaw_csv_path):

    def create_and_save_dataframe_with_data(file_path, data1, data2,data3,data4):
        # Set default column names if none are provided
        
        col_names = ["case_uri","para_id","paragraphs","references"]
        
        # Extract the file name without extension from the path
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Create a DataFrame with the provided data
        data = pd.DataFrame({col_names[0]: data1, col_names[1]: data2,col_names[2]:data3,col_names[3]:data4})
        
        # Save the DataFrame as a CSV file with the extracted name
        csv_filename = f"{base_name}.csv"
        data.to_csv(caselaw_csv_path, index=False)
        
        return csv_filename
    parser = JudgmentParser(caselaw_xml_path)
    #Only those cases are reffered which have type=legislation as a reference
    if parser.has_legislation_reference():
        judgment_body_paragraphs_text = parser.get_judgment_body_paragraphs_text()
        #print(judgment_body_paragraphs_text)
        para_contents = []
        para_ids = [] 
        para_references = []
        case_uris = []
        for para in judgment_body_paragraphs_text: 
            caseuri,para_id,content,references = para
            para_contents.append(content)
            para_ids.append(para_id)
            para_references.append(references)
            case_uris.append(caseuri)
        create_and_save_dataframe_with_data(caselaw_csv_path,case_uris,para_ids,para_contents,para_references)

def downloadThelegislationIfNotExist(legislation_urls,legislation_dir):

    for url in legislation_urls:
        try:
            # Extract legislation ID from URL
            # Extract legislation path after ukpga
            # Split URL to get legislation path after ukpga
            legislation_parts = url.split('/ukpga/')[-1].split('/')
            
            # Create directory path preserving the full structure (e.g. Eliz2/8-9/65)
            directory_path = os.path.join(legislation_dir, *legislation_parts)
            
            # Check if the directory already exists and contains files
            if not os.path.exists(directory_path) or not os.listdir(directory_path):
                parser = LegislationParser(url, True)
                
                # Create directory if it does not exist
                os.makedirs(directory_path, exist_ok=True)
                
                parser.save_all_sections_to_files(directory_path)
                
        except Exception as e:
            print(f"Error processing legislation URL {url}: {str(e)}")
            continue

def extract_legislation_references(unprocessed_cases, folder_path):
        # Dictionary to store case number -> legislation URLs mapping
        case_legislation_map = {}
        
        for case in unprocessed_cases:
            legislation_urls = set()
            csv_path = f'{folder_path}/{case}.csv'
            print("------checking legislation for csv --------")
            print(csv_path)
            print(f"------------------------------------------")
            try:
                df = pd.read_csv(csv_path)
                # Extract legislation references from the references column
                for _, row in df.iterrows():
                    if not pd.isna(row['references']):
                        refs = ast.literal_eval(row['references'])
                        for ref in refs:
                            if 'href' in ref:
                                # Extract the legislation URI without section
                                uri = ref['href']
                                # Get just the legislation part before any section
                                bas_uri = uri.split('/section')[0]
                                legislation_urls.add(bas_uri)
                
                # Add non-empty legislation URL lists to the map
                if legislation_urls:
                    case_legislation_map[case] = sorted(list(legislation_urls))
                    
            except Exception as e:
                print(f"Error processing case {case}: {e}")
                
        print(f"Found legislation references in {len(case_legislation_map)} cases")
        return case_legislation_map
if __name__ == "__main__":
    
    input_folder_path = 'data/sample'
    output_folder_path = f"{input_folder_path}/output"
    os.makedirs(output_folder_path, exist_ok=True)
    xml_to_csv = f"{output_folder_path}/xml_to_csv"
    os.makedirs(xml_to_csv, exist_ok=True)
    legislation_dir = f"{input_folder_path}/legislation"
    os.makedirs(legislation_dir, exist_ok=True)
    
    ##########################STEP 1 PROCESSING###############################
    
    # Process only the cases in the issues list
    for filename in os.listdir(input_folder_path):
        if filename.endswith('.xml'):
            # Extract case number from filename
            filename_case = filename.split('.')[0]
            case_number = filename_case.split('_')[-1]
            
            
            test_case_path = os.path.join(input_folder_path, filename)
            caselaw_csv_path = f'{xml_to_csv}/{case_number}.csv'
            print("================================")
            print(f"processing {caselaw_csv_path}")
            Convert_CSVs_xml_to_Csv(test_case_path, caselaw_csv_path)
    
    ##########################STEP 2 Classifier###############################
    
    # Lists of case numbers - issues contains cases that had processing problems,
    
    
    folder_path = xml_to_csv
    # Iterate over each file in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            # Extract case number from filename
            case_number = filename.split('.')[0]
            csv_path = os.path.join(folder_path, filename)
            print(csv_path)
            print(f"===========processing {case_number} =============================")
            process_csv_with_openai('src/examples.json', csv_path)

    
    #######STEP 3 Attaching the sections with the paragraphs which are legally interpreted###############################
    #####part-1 step 3----download the legislation mentioned in the case laws########### 
    # Read all case CSVs and collect unique legislation references
    
    folder_path = xml_to_csv
    csv_files = [f.replace('.csv', '') for f in os.listdir(folder_path) if f.endswith('.csv')]
    case_legislation_map = extract_legislation_references(csv_files, folder_path)
    #print(case_legislation_map)
    legislationlist = [item for sublist in case_legislation_map.values() for item in sublist]
    downloadThelegislationIfNotExist(legislationlist,legislation_dir)
    # Remove URL prefix from legislation references
    cleaned_case_legislation_map = {}
    for case, legislation_list in case_legislation_map.items():
        cleaned_legislation = []
        for legislation in legislation_list:
            # Remove the base URL prefix if present
            if 'legislation.gov.uk/id/ukpga/' in legislation:
                cleaned_url = legislation.split('legislation.gov.uk/id/ukpga/')[-1]
                cleaned_legislation.append(cleaned_url)
            else:
                cleaned_legislation.append(legislation)
        cleaned_case_legislation_map[case] = cleaned_legislation
    
    print("Cleaned legislation references by case:")
    print(cleaned_case_legislation_map)
     # Save the cleaned legislation map to a pickle file
    with open(f'{input_folder_path}/cleaned_case_legislation_map.pkl', 'wb') as f:
         pickle.dump(cleaned_case_legislation_map, f)
    print("Saved cleaned legislation map to data/cleaned_case_legislation_map.pkl")
    
    
     #####part-2 step 3----make the Triples########### 
    pickle_file_path = f'{input_folder_path}/cleaned_case_legislation_map.pkl'
    keyPhraseExtractor.extractThePhrases(pickle_file_path,xml_to_csv,xml_to_csv,legislation_dir,output_folder_path)
   