
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

