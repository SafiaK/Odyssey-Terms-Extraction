import pandas as pd
from openAIHandler import getLegalClassifierChain
import ast
import json
import time
def getExamples(file_path):
    

    def getTheParaId(case_uri, para_id):
        try:
            # Ensure para_id is converted to a string for consistent processing
            para = str(para_id)
            
            # Extract case number from case_uri
            case_number = case_uri.split("/")[-1]
            
            # Split para_id on "_" and get the second part (index 1), if it exists
            para_parts = para.split("_")
            
            # Ensure there are at least two parts to avoid IndexError
            if len(para_parts) > 1:
                para_number = para_parts[1]
            else:
                raise ValueError("Invalid para_id format, expecting an underscore.")

            # Return the formatted result
            return f"{case_number}_{para_number}"
        
        except Exception as e:
            print(f"Error processing case_uri: {case_uri}, para_id: {para_id}. Error: {e}")
            return None  # Return None or another placeholder if there's an error
    def getTheExampleTuple(row):
        try:
            pharses = []
            #print(type(row['label']))
            if not pd.isna(row['label']):
                labels = ast.literal_eval(row['label'])
                for label in labels:
                    pharses.append(label['text'])
            exampleDic = {'id':row['id'],
            'para_content' : row['ProcessedParagraphs'],
            'if_interpretation' : row['classifier_label'],
            'interpreted_phrases' :pharses}
            return exampleDic
        except Exception as e:
            print("+++++++=======================================")
            print(e)
            print(row)
            print("+++++++=======================================")

    data = pd.read_csv(file_path)
    data['id'] = data.apply(
    lambda x: getTheParaId(str(x['case_uri']), str(x['para_id'])), axis=1
    )
    examples =[]
    examples_dic = {}
    case_uris = data["case_uri"].unique()
    for test_case in case_uris:
        train_data = data[data["case_uri"]!= test_case]
        test_data = data[data["case_uri"] == test_case]
        #check how many positive exaple in each traing set
        #pick up the same number of negative
        #if total picked negatice examples are less than positive examples -- drop the positive-- keep the number equal
        # Separate positive and negative examples in the training data
        positive_examples = train_data[train_data['classifier_label'] == 1]
        negative_examples = train_data[train_data['classifier_label'] == 0]
        
        # Determine the minimum count between positive and negative examples
        min_count = min(len(positive_examples), len(negative_examples))
        
        # Balance the examples by picking 'min_count' from both positive and negative examples
        positive_examples = positive_examples.sample(n=min_count, random_state=42)
        negative_examples = negative_examples.sample(n=min_count, random_state=42)
        
        for i,row in positive_examples.iterrows():
            examples.append(getTheExampleTuple(row))
        for i,row in negative_examples.iterrows():
            examples.append(getTheExampleTuple(row))
        
        examples_dic[test_case]=examples
        examples = []
    return examples_dic



def process_csv_with_openai(example_json_file,caselaw_csv_to_process):
    def extract_phrases_or_error(x,column_name):
        try:
            return x[column_name]
        except KeyError:
            return "Error"
    def process_in_batches(data,parser,chain, batch_size=20,delay=30):
        responses = []
        # Split the DataFrame into batches
        print("batch size is",batch_size)
        
        for start in range(0, len(data), batch_size):
            print("starting again...")
            end = start + batch_size
            batch = data.iloc[start:end]
            
            # Prepare the input dictionary list for batch processing
            input_batch = [
                {
                    "para_id": row['para_id'],
                    "para_content": row['paragraphs'],
                    "format_instructions": parser.get_format_instructions()
                }
                for _, row in batch.iterrows()
            ]
            
            # Call chain.batch on the batch of inputs
            batch_responses = chain.batch(input_batch)
            responses.extend(batch_responses)
            time.sleep(delay) # to make sure it does not exceed the processing limit
            
        
        # Add responses to a new column in the original DataFrame
        return responses

    """
    Process a CSV file containing legal text using OpenAI handlers.
    
    Args:
        csv_path (str): Path to the CSV file
        
    Returns:
        pd.DataFrame: Processed results with interpretations
    """
    # Read the CSV file
    with open(example_json_file, 'r') as file:
        examples = json.load(file)
    
    # Initialize the chains
    parser,classifier_chain = getLegalClassifierChain(examples)  # Empty examples list for now
    
    df = pd.read_csv(caselaw_csv_to_process,index_col=False)
    Processeddata = process_in_batches(df,parser,classifier_chain)
    dataProcess = pd.DataFrame()
    dataProcess['gpt-40'] = Processeddata
    dataProcess['para_id'] = dataProcess['gpt-40'].apply(lambda x: x.get('para_id') if isinstance(x, dict) else None)
    dataProcess['if_interpretation'] = dataProcess['gpt-40'].apply(lambda x: x.get('if_interpretation') if isinstance(x, dict) else None)
    dataProcess['interpretation_phrases'] = dataProcess['gpt-40'].apply(lambda x: x.get('interpretation_phrases') if isinstance(x, dict) else None)
    dataProcess['reason_of_interpretation'] = dataProcess['gpt-40'].apply(lambda x: x.get('reason') if isinstance(x, dict) else None)
    dataProcess = dataProcess.drop_duplicates(subset='para_id')
    df = df.merge(dataProcess,on="para_id")
    df['if_interpretation'] = df['if_interpretation'].apply(lambda x: '1' if x == True else ('0' if pd.notna(x) else '0'))
    if 'gpt-40' in df.columns:
        df.drop(columns=['gpt-40'], inplace=True)
    df.to_csv(caselaw_csv_to_process,index=False)
    

if __name__ == "__main__":
    csv_path = "data/dataP.csv"  # replace with your actual CSV file path
    examples_dic = getExamples(csv_path)
    first_value = next(iter(examples_dic.values()))
    print(len(first_value))
    with open('data/examples.json', 'w') as json_file:
        json.dump(first_value, json_file, indent=4)
    
    #print(getExamples(csv_path))

