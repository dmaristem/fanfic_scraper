from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from typing import List

#Download web pages to get the raw HTML, with the help of the requests package
def simple_get(url:str):
    """
    Attempts to get the content at 'url' by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the text content (a string?), otherwise return None.

    # >>> from fanfic_scraper import simple_get
    >>> raw_html = simple_get('https://www.fanfiction.net/s/8559914/1/Fledgling')
    >>> len(raw_html)
    276646
    >>> no_html = simple_get('https://www.fanfiction.net/s/8559914/19/Fledgling')
    >>> no_html is None
    True
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
        # options = html.find_all('option value')
        option_tags = html.select("option")
        # option_tags = html.select("span select option:nth-of-type()")
        # option_tags = html.select("span > select > option['value']")
        values = [o.get('value') for o in option_tags]

        # one-chapter situation
        if not values:
            print(1)
            return 1
        # multi-chapter situation
        else:
            print(int(values[-1]))
            # print(o)
            # print(options)
            # print(values[-1])
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
    id = second_slice[0]
    title = first_slice[1]
    chap = '/{}/'
    link = id + chap + title
    # print(id, title)
    # print(url)
    # print(first_slice, second_slice)
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
            # lst.append(f'https://www.fanfiction.net/s/8559914/{n}/Fledgling')  #f-string option; works for Python 3.6+
        # print(lst)
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
            #     "ResultSet object has no attribute '%s'. You're probably treating a list of items like a single item. Did you call find_all() when you meant to call find()?" % key
            # AttributeError: ResultSet object has no attribute 'get_text'. You're probably treating a list of items like a single item. Did you call find_all() when you meant to call find()?
            # p = html.find_all('p').get_text()
            # print(p)

            for paragraph in html.select('p'): #select all <p> tags from the HTML document
                f.write(paragraph.get_text() + '\r\n')
                # f.write(paragraph.get_text())


                # print(paragraph.get_text()) #print out the text in all the <p> tags
        else:
            #Raise an exception if we failed to get any data from the url
            raise Exception('Error retrieving contents at {}'.format(url))
    f.close()


if __name__ == '__main__':
    # get_text('https://www.fanfiction.net/s/8559914/1/Fledgling')
    # get_num_of_chapters('https://www.fanfiction.net/s/8559914/1/Fledgling')
    # slice_link('https://www.fanfiction.net/s/8559914/1/Fledgling')
    # generate_links('https://www.fanfiction.net/s/8559914/1/Fledgling')
    # get_title("https://www.fanfiction.net/s/5782108/1/Harry-Potter-and-the-Methods-of-Rationality")
    # get_text("https://m.fanfiction.net/s/5182916/1/a-fish") # ISSUES with finding num of chapters. FIGURED IT OUT: because it's the mobile page. "m.fanfiction.."
    # get_text("https://www.fanfiction.net/s/4656343/1/Personally-I-d-Rather-Lick-Sand")
    # get_text("https://www.fanfiction.net/s/4844985/1/brave-soldier-girl-comes-marching-home")
    # get_num_of_chapters("https://www.fanfiction.net/s/4844985/1/brave-soldier-girl-comes-marching-home")
    # get_num_of_chapters("https://www.fanfiction.net/s/4656343/1/Personally-I-d-Rather-Lick-Sand")

    # stopped at the end of chapter 5
    get_text("https://www.fanfiction.net/s/7880959/1/Ad-Infinitum") # ISSUE UnicodeEncodeError: 'charmap' codec can't encode character '\u2015' in position 0: character maps to <undefined>

    # get_text("https://www.fanfiction.net/s/7552826/1/An-Unfound-Door")

"""
from fanfic_scraper import simple_get, get_text, get_num_of_chapters
get_num_of_chapters('https://www.fanfiction.net/s/8559914/1/Fledgling')
get_num_of_chapters("https://www.fanfiction.net/s/5782108/1/Harry-Potter-and-the-Methods-of-Rationality")
get_text('https://www.fanfiction.net/s/8559914/19/Fledgling')
get_text('https://www.theglobeandmail.com/life/travel/article-from-edmonton-to-ecuador-10-places-to-visit-in-2019/')
"""

#TODO: convert .txt to .docx or .pdf, never take in mobile version of fanfiction.net, UnicodeEncodeError, include Chapter number and title in the .txt file
