from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from typing import List

#Download web pages to get the raw HTML, with the help of the requests package
def simple_get(url:str):
    """
    Attempts to get the content at 'url' by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the text content, otherwise return None.
    """
    try:
        #The closing() function ensures that any network resources are freed when they go out of scope in the with block.
        #Using closing() is a good practice to help prevent fatal errors and network timeouts
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                print("HTTP Error: {0}".format(resp.raise_for_status()))
                print(resp.headers)
                #the content is the HTML document
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None

def is_good_response(resp)-> bool:
    """
     Return True if the response seems to be HTML, otherwise return False.
    """
    content_type = resp.headers['Content-Type'].lower()
    print("HTTP Status Code: {0}".format(resp.status_code))
    return (resp.status_code == 200 and content_type is not None and content_type.find('html') > -1)

def log_error(e):
    """
    This function prints the errors.
    """
    print(e)


def get_num_of_chapters(url: str) -> int:
    """
    Return the total number of chapters in the fanfic.

    :param url: The URL of a fanfic at any chapter.
    :return: The total number of chapters in the fanfic.
    """

    response = simple_get(url)

    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        option_tags = html.select("option")
        values = [o.get('value') for o in option_tags]
        # one-chapter situation
        if not values:
            return 1
        # multi-chapter situation
        else:
            return int(values[-1])

    else:
        #Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))

def slice_link(url: str) -> str:
    """
    Return a modified link of the fanfic to be scraped. Modified to insert chapter values into the fanfic link.
    :param url: The URL of a fanfic at any chapter.
    """
    first_slice = url.rsplit('/', 1)  # first would print something like ['https://www.fanfiction.net/s/8559914/1', 'Fledgling']
    second_slice = first_slice[0].rsplit('/', 1) # second would print something like ['https://www.fanfiction.net/s/8559914', '1']
    id_ = second_slice[0]
    title = first_slice[1]
    chap = '/{}/'
    link = id_ + chap + title
    return link

def generate_links(url: str) -> List:
    """
    Return a list of links to all chapters of a fanfic, in chronological order.
    :param url: The URL of a fanfic at any chapter.
    """
    num_chaps = get_num_of_chapters(url)
    if num_chaps == 1:
        return [url]
    else:
        link = slice_link(url)
        lst = []
        for n in range(1, num_chaps + 1):
            lst.append(link.format(n)) #string format method
        return lst


def get_title(url: str) -> str:
    """
    Get the title of the fanfiction, without any non-alphnumeric characters between words.
    """
    first_slice = url.rsplit('/', 1)
    title = first_slice[1]
    normal_title = title.replace('-', ' ')
    # print(normal_title)
    return normal_title

#Select and extract from the raw HTML using BeautifulSoup, to get text
# The BeautifulSoup constructor parses raw HTML strings and produces an object that mirrors the HTML document's structure
# The object includes a lot of methods to select, view, and manipulatethe DOM nodes and text content
#Extract the textual content of a chapter:
def get_text(url: str)-> None:
    """
    Downloads the fanfiction page(s) and returns a string of the entire text of the chapter(s).
    """
    lst_links = generate_links(url)
    title = get_title(url)
    f = open(title + ".txt", 'w+')
    for link in lst_links:
        response = simple_get(link)
        if response is not None:
            html = BeautifulSoup(response, 'html.parser')
            for paragraph in html.select('p'): 
                f.write(paragraph.get_text() + '\r\n')
        else:
            #Raise an exception if we failed to get any data from the url
            raise Exception('Error retrieving contents at {}'.format(url))
    f.close()


if __name__ == '__main__':
    # get_text("https://m.fanfiction.net/s/5182916/1/a-fish") # ISSUES with finding num of chapter because it's the mobile page. "m.fanfiction.."
   
    # stopped at the end of chapter 5
    get_text("https://www.fanfiction.net/s/7880959/1/Ad-Infinitum") # ISSUE UnicodeEncodeError: 'charmap' codec can't encode character '\u2015' in position 0: character maps to <undefined>




#TODO: convert .txt to .docx or .pdf, never take in mobile version of fanfiction.net, UnicodeEncodeError, include Chapter number and title in the .txt file
