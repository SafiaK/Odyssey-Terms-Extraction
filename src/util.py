
def getTheFirstSection(ref_list,legislation_folder_path):
    for ref in ref_list:
        act,section = ref['legislation_section']
        if section:
            section_u = section.split('/')[0]
            with open(f'{legislation_folder_path}/{act}/section-{section_u}.txt', 'r') as file:
                content = file.read()
                return content
    return ''

def flatten_list_of_lists(list_of_lists):
    """
    Flattens a list of lists into a single list containing all the values.

    Args:
        list_of_lists (list): A list where each element is a list.

    Returns:
        list: A single list containing all the values from the input lists.
    """
    return [item for sublist in list_of_lists for item in sublist]
from spacy.lang.en.stop_words import STOP_WORDS
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
def is_all_stopwords(phrase, custom_stopwords_file):
    """
    Check if all words in a phrase are stopwords (either in custom list or English stopwords).
    
   Args:
        phrase (str): The phrase to check.
        custom_stopwords_file (str): Path to file containing custom stopwords.
    
    Returns:
        bool: True if all words are stopwords, False otherwise
    """
    # Convert custom stopwords to a lowercase set for efficient lookup
    # Read custom stopwords from file
    with open(custom_stopwords_file, 'r') as f:
        custom_stopwords = set(word.strip().lower() for word in f.readlines())
    #print(custom_stopwords)
    # Initialize stemmer and lemmatizer
    stemmer = PorterStemmer()
    lemmatizer = WordNetLemmatizer()
    
    # Split phrase into words and convert to lowercase
    phrase_words = phrase.lower().split()
    #print(f"Phrase words: {phrase_words}")
    
    # Check if all words in the phrase are stopwords
    for word in phrase_words:
        # Get all variations of the word
        variations = {
            word,  # Original lowercase
            stemmer.stem(word),  # Stemmed
            lemmatizer.lemmatize(word)  # Lemmatized
        }
        #print(f"Variations for '{word}': {variations}")
        
        # Check if any variation is in custom or NLTK stopwords
        if not any(var in custom_stopwords or var in STOP_WORDS for var in variations):
            return False
            
    return True


